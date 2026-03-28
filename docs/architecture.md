# Harbor — Architecture

## Overview

Harbor is an agent platform management system that brings API Management (APIM) principles to AI agent ecosystems running on AWS Bedrock AgentCore. It provides a centralized registry, discovery, lifecycle governance, and runtime policy enforcement — built entirely on AWS serverless primitives and designed to deploy into existing Control Tower landing zones.

## Design Principles

1. **Serverless-first** — Lambda + API Gateway for compute. No ECS, Fargate, or EC2. Management-plane traffic is low and bursty; serverless is cost-optimal.
2. **Single-table DynamoDB** — All entities in one table with composite PK/SK keys. Multi-tenant by construction, not by convention.
3. **Tenant = AWS Account** — Tenant identity derived from the caller's AWS account ID. No tenant parameter in the API — it's extracted from the auth token.
4. **Policy enforcement at the platform layer** — Agents don't enforce their own governance. Harbor evaluates capability boundaries, communication ACLs, and schedule windows centrally.
5. **A2A Agent Card alignment** — Agent metadata schema follows the A2A protocol spec, extended with APIM and governance fields.
6. **Control Tower native** — Harbor is a consumer of CT landing zones, not a replacement. It deploys into Shared Services OU and integrates with SCPs, StackSets, and IAM Identity Center.

## System Architecture

```
┌─ Management Account (Control Tower) ─────────────────────────┐
│  Landing Zone │ SCPs │ Account Factory │ Config Rules         │
└──────────────────────────────────────────────────────────────┘
         │ governs
         ▼
┌─ Shared Services OU ─────────────────────────────────────────┐
│  Harbor Central Account                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ CloudFront → WAF → S3 (React SPA)                       │ │
│  │           → API GW → Lambda (FastAPI + Mangum)           │ │
│  │                         ↓                                │ │
│  │                    DynamoDB (multi-tenant, single-table)  │ │
│  │                    EventBridge (cross-account events)     │ │
│  │                    Cognito (IAM Identity Center SSO)      │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         │ cross-account IAM roles
         ▼
┌─ Workload OU ────────────────────────────────────────────────┐
│  {BU}-Prod Account                                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Bedrock AgentCore Runtime                                │ │
│  │   Agent A ──→ Harbor API (register, heartbeat, discover) │ │
│  │   Agent B ──→ Harbor API (policy check, communicate)     │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Role |
|-----------|------|
| **CloudFront** | CDN for React SPA and API reverse proxy. HTTPS-only, TLS 1.2+. |
| **WAF** | AWS Managed CommonRuleSet + rate limiting (1000 req/5 min/IP). |
| **S3** | Static hosting for the React SPA. No public access — OAC only. |
| **API Gateway (HTTP API)** | Routes `/api/*` to Lambda. Throttled at 100 req/s burst, 50 sustained. |
| **Lambda** | Python 3.12 on ARM64 (Graviton). FastAPI app wrapped by Mangum. 256 MB, 30s timeout. |
| **DynamoDB** | Single-table, PAY_PER_REQUEST, point-in-time recovery enabled. |
| **Cognito** | User pool with JWT issuance. Federated with IAM Identity Center for SSO. |
| **EventBridge** | `harbor-events` bus for lifecycle events, policy violations, cross-account routing. |

## Data Model

### DynamoDB Single-Table Design

Table: `harbor-agent-registry`

| PK | SK | Entity |
|----|-----|--------|
| `TENANT#{tid}#AGENT#{aid}` | `META` | Agent record |
| `TENANT#{tid}#AGENT#{aid}` | `VER#{version}` | Version snapshot |
| `TENANT#{tid}#AGENT#{aid}` | `HEALTH` | Health status |
| `TENANT#{tid}#AGENT#{aid}` | `AUDIT#{timestamp}` | Audit entry |
| `TENANT#{tid}#CAP#{cap}` | `AGENT#{aid}` | Capability index |
| `TENANT#{tid}#PHASE#{phase}` | `AGENT#{aid}` | Phase index |
| `TENANT#{tid}#POLICY` | `AGENT#{aid}` | Capability policy |
| `COMM_RULE#{rule_id}` | `META` | Communication rule |
| `SCHEDULE#{aid}` | `META` | Schedule policy |

### Global Secondary Indexes

| GSI | PK | SK | Purpose |
|-----|----|----|---------|
| `status-index` | `status` | `updated_at` | Query agents by operational status |
| `tenant-index` | `tenant_id` | `updated_at` | List all entities for a tenant |
| `lifecycle-index` | `lifecycle_status` | `updated_at` | Query agents by lifecycle phase |

### Table Rules

- All items have `pk` and `sk` fields.
- All agent items prefixed with `TENANT#{tenant_id}#`.
- Timestamps are ISO 8601 UTC strings.
- Billing mode: `PAY_PER_REQUEST`.
- Point-in-time recovery: enabled.
- TTL field: `ttl` (Unix epoch seconds) — used for audit log expiry.

### Agent Record Schema

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | Unique identifier (slug format) |
| `name` | string | Human-readable display name |
| `description` | string | What this agent does |
| `version` | string | Semantic version (e.g., `1.2.0`) |
| `tenant_id` | string | AWS account ID of the owning account |
| `owner` | string | Email or IAM principal of the agent owner |
| `visibility` | enum | `private`, `ou_shared`, `org_wide` |
| `lifecycle_status` | enum | Current lifecycle state (see below) |
| `status` | enum | Operational status: `active`, `inactive`, `maintenance` |
| `capabilities` | list[string] | What the agent can do (e.g., `["nlp", "summarize"]`) |
| `phase_affinity` | list[string] | Lifecycle phases where this agent operates |
| `routing_rules` | object | Load balancing and failover configuration |
| `endpoint` | string | Agent runtime endpoint URL |
| `a2a_card_url` | string | URL to the agent's A2A Agent Card |
| `tags` | dict | Arbitrary key-value metadata |
| `created_at` | string | ISO 8601 creation timestamp |
| `updated_at` | string | ISO 8601 last-modified timestamp |

## Multi-Tenant Model

### Tenant Hierarchy

```
Org (AWS Organization)
└── Business Unit (OU)
    └── Project (Account)
        └── Environment (account tag: dev / staging / prod)
```

- `tenant_id` = AWS Account ID of the caller.
- Harbor maps account ID → org/OU/project via Control Tower metadata.
- All DynamoDB queries include `tenant_id` in the key condition — no cross-tenant data leaks by construction.

### Visibility Scopes

| Scope | Who Can See | Use Case |
|-------|-------------|----------|
| `private` | Same account only | Dev/draft agents |
| `ou_shared` | Same OU (business unit) | Shared within a department |
| `org_wide` | Entire organization | Compliance agents, shared utilities |

Discovery queries respect visibility: an agent in account A with `private` visibility is invisible to account B, even if B searches for the same capability.

## Agent Lifecycle

```
Draft → Submitted → In Review → Approved → Published → [Suspended] → Deprecated → Retired
                        │
                   Rejected → Draft
```

### State Definitions

| State | Description |
|-------|-------------|
| `draft` | Initial state. Agent is registered but not visible. Owner can edit freely. |
| `submitted` | Owner has requested promotion. Awaiting review. |
| `in_review` | A reviewer has picked up the submission. |
| `approved` | All required approvals received. Ready to publish. |
| `rejected` | Review failed. Returns to `draft` with reviewer comments. |
| `published` | Live and discoverable. Only published agents appear in discovery results. |
| `suspended` | Emergency kill switch. Any admin can trigger. Agent is immediately undiscoverable. |
| `deprecated` | Sunset announced. Requires a sunset date. Dependents are notified via EventBridge. |
| `retired` | Archived. Removed from discovery. Record retained for audit. |

### Approval Policy by Environment

| Environment | Required Approvals |
|-------------|-------------------|
| `dev` | Auto-approve — owner can self-publish |
| `staging` | 1 approval from `project_admin` |
| `prod` | 2 approvals: `risk_officer` + `compliance_officer` |

Every lifecycle transition is recorded in the audit log with actor, timestamp, and reason.

## Runtime Policies

### Capability Boundaries

Control what tools, APIs, and MCP servers each agent can access:

```yaml
tools:
  allowed: ["db_query", "send_email"]
  denied: ["execute_trade"]
  require_human: ["large_transfer"]
mcp_servers:
  allowed: ["internal-kb", "market-data"]
  denied: ["external-*"]
apis:
  allowed: ["https://internal.api/*"]
  denied: ["https://external.api/*"]
data_classification:
  max_level: "confidential"
```

Evaluation logic: `denied` takes precedence over `allowed`. Wildcard patterns supported. `require_human` triggers a human-in-the-loop approval before the tool invocation proceeds.

### Communication ACL

Control which agents can talk to each other. Default mode is allowlist (deny-all unless explicitly permitted) — designed for regulated environments like financial services.

```yaml
default_action: deny
rules:
  - from: "trading-agent"
    to: "risk-assessment-agent"
    allowed: true
    required: true          # must call risk before acting
  - from: "external-*"
    to: "internal-*"
    allowed: false          # external agents blocked from internal
  - from: "support-agent"
    to: "knowledge-base-agent"
    allowed: true
    conditions:
      time_window: "business_hours"
```

Rules are evaluated top-to-bottom. First match wins. If no rule matches, `default_action` applies.

### Schedule Windows

Control when agents can operate:

```yaml
active_windows:
  - cron: "0 9-16 * * MON-FRI"
    timezone: "Asia/Taipei"
    label: "Business hours"
blackout_windows:
  - start: "2025-12-25T00:00:00Z"
    end: "2025-12-26T00:00:00Z"
    label: "Holiday freeze"
out_of_window_action: "reject"   # or "queue", "alert"
```

Blackout windows override active windows. `out_of_window_action` determines behavior when an agent attempts to operate outside its schedule.

## Authentication & Authorization

### Cognito User Pool

- Self-signup disabled (admin-created accounts only).
- Email as username.
- Custom attributes: `custom:tenant_id`, `custom:role`.
- JWT issued on login, validated by API Gateway authorizer and FastAPI middleware.

### Role-Based Access Control

| Role | Permissions |
|------|-------------|
| `viewer` | Read-only access to agents, discovery, audit logs |
| `developer` | Register agents, update own agents, submit for review |
| `project_admin` | Approve staging deployments, manage team agents |
| `risk_officer` | Approve prod deployments (risk sign-off) |
| `compliance_officer` | Approve prod deployments (compliance sign-off) |
| `admin` | Full access. Suspend/retire any agent. Manage policies. |

### Dev Bypass Mode

When `HARBOR_AUTH_DISABLED=true` (local development only), the auth middleware injects a default tenant context:

```python
TenantContext(tenant_id="dev-tenant", role="admin", owner="dev@harbor.local")
```

### Machine-to-Machine Auth

Cross-account agents authenticate via Cognito client credentials flow. The client's `tenant_id` is mapped from the originating AWS account's IAM role.

## Event System

### EventBridge Bus

Bus name: `harbor-events`

| Event Type | Source | Trigger |
|------------|--------|---------|
| `AgentLifecycleChanged` | `harbor.registry` | Any lifecycle state transition |
| `AgentHealthChanged` | `harbor.health` | Health status change (healthy → unhealthy) |
| `PolicyViolation` | `harbor.policy` | Agent attempts a denied action |
| `AgentRegistered` | `harbor.registry` | New agent registered |
| `AgentRetired` | `harbor.registry` | Agent moved to retired state |

### Event Schema

```json
{
  "source": "harbor.registry",
  "detail-type": "AgentLifecycleChanged",
  "detail": {
    "tenant_id": "123456789012",
    "agent_id": "trading-agent",
    "from_status": "approved",
    "to_status": "published",
    "actor": "admin@example.com",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Cross-Account Event Policy

Workload accounts can emit events to the Harbor bus via cross-account EventBridge policy. Harbor Central processes these events for health aggregation and audit logging.

### SNS Alerts

Critical events (`PolicyViolation`, `suspended` transitions) fan out to an SNS topic for email/Slack/PagerDuty integration.

## Control Tower Integration

Harbor deploys into existing Control Tower landing zones as a Shared Services workload:

| Integration | Purpose |
|-------------|---------|
| **StackSet template** | Auto-provisions `harbor-agent-reporter` IAM role in workload accounts via CT Account Factory |
| **SCP guardrails** | Protects Harbor Central resources, enforces agent tagging in workload accounts |
| **Cross-account IAM** | Workload agents assume role to call Harbor API with their account identity |
| **IAM Identity Center SSO** | Cognito SAML federation with enterprise IdP for console and CLI access |
| **Security Hub** | Custom findings for policy violations and unapproved agents running in production |
| **Config Rules** | Compliance checks: all agents in workload accounts must be registered in Harbor |

See [enterprise-integration-guide.md](enterprise-integration-guide.md) for the full deployment runbook.

## Data Flow

### Three-Layer Separation

```
API Route (FastAPI)
  │  HTTP concerns: request parsing, response formatting, error codes
  ▼
Service Layer (registry, discovery, health, audit, policy)
  │  Business logic: validation, orchestration, side effects
  ▼
Store Layer (DynamoDB)
  │  Persistence: serialization, queries, error handling
  ▼
DynamoDB Table
```

Rules:
- **API → Service → Store → DynamoDB**. No shortcuts.
- `store/` is the only layer that imports `boto3`.
- `policy/` is the only layer that evaluates governance rules.
- Services raise domain exceptions; the API layer maps them to HTTP status codes.
- Frontend calls API Gateway, which invokes Lambda. Frontend never touches DynamoDB.

### Cross-Account Data Flow

```
Workload Account Agent
  → assumes harbor-agent-reporter IAM role
  → calls Harbor API Gateway (HTTPS)
  → API GW validates Cognito JWT / IAM auth
  → Lambda extracts tenant_id from caller identity
  → DynamoDB query scoped to tenant_id
```

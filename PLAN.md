# Harbor — Development Plan

## Vision

Harbor is an **Agent Platform Management & Governance** system built on AWS.
It provides registry, discovery, lifecycle management, and enterprise governance
for AI agents running on AWS Bedrock AgentCore Runtime.

For enterprise customers (financial services), Harbor integrates with
**AWS Control Tower** landing zones to provide multi-tenant agent governance
with tenant isolation, approval workflows, runtime policy enforcement,
agent-to-agent communication control, and schedule-based access windows.

---

## Enterprise Governance Design

### Account Topology (Control Tower Landing Zone)

```
Management Account (Control Tower)
├── Security OU
│   ├── Log Archive Account — CloudTrail, Config logs
│   └── Audit Account — Security Hub, GuardDuty aggregation
├── Shared Services OU
│   └── Harbor Central Account — Harbor API, DynamoDB, UI
│       (Management plane only — no agents run here)
├── Workload OU (per business unit)
│   ├── CreditCard-Dev Account
│   ├── CreditCard-Staging Account
│   ├── CreditCard-Prod Account
│   ├── WealthMgmt-Dev Account
│   ├── WealthMgmt-Prod Account
│   └── ...
└── Sandbox OU
    └── Innovation Lab Account
```

Harbor lives in **Shared Services OU**. Agents run in **Workload accounts**.
Harbor reaches across accounts via cross-account IAM roles provisioned by CT.

### Tenant Model

- **Tenant = AWS Account** (not a user)
- Hierarchy: `Org → Business Unit (OU) → Project (Account) → Environment (tag)`
- Harbor derives `tenant_id` from the caller's AWS account ID
- CT Account Factory provisions new tenants automatically
- Agent visibility scopes: `private` (same account), `ou-shared` (same OU), `org-wide`

### DynamoDB Multi-Tenant Key Design

```
PK                                      SK                    Entity
TENANT#{tenant_id}#AGENT#{agent_id}     META                  Agent record
TENANT#{tenant_id}#AGENT#{agent_id}     VER#{version}         Version snapshot
TENANT#{tenant_id}#AGENT#{agent_id}     HEALTH                Health status
TENANT#{tenant_id}#AGENT#{agent_id}     AUDIT#{timestamp}     Audit entry
TENANT#{tenant_id}#CAP#{capability}     AGENT#{agent_id}      Capability index
TENANT#{tenant_id}#PHASE#{phase}        AGENT#{agent_id}      Phase index
TENANT#{tenant_id}#POLICY              AGENT#{agent_id}      Runtime policy
COMM_RULE#{rule_id}                     META                  Communication rule
SCHEDULE#{agent_id}                     META                  Schedule policy
```

GSIs:
- `status-index`: PK=status, SK=updated_at
- `tenant-index`: PK=tenant_id, SK=updated_at
- `lifecycle-index`: PK=lifecycle_status, SK=updated_at

### Agent Lifecycle (Governance Pipeline)

```
Draft → Submitted → In Review → Approved → Published → [Suspended] → Deprecated → Retired
                        │
                   Rejected → Draft
```

| State | Visibility | Who can transition |
|-------|-----------|-------------------|
| Draft | Owner only | Owner |
| Submitted | Owner + reviewers | Owner |
| In Review | Owner + reviewers | Assigned reviewer |
| Approved | Project members | Reviewer (approve) or reviewer (reject → Draft) |
| Published | Discoverable by policy | Project admin |
| Suspended | Hidden from discovery | Any admin (emergency) |
| Deprecated | Visible with sunset warning | Project admin |
| Retired | Archived, not visible | System (auto after sunset) |

Approval policy per environment:
- **dev**: auto-approve (owner can self-publish)
- **staging**: 1 approval from `project_admin`
- **prod**: 2 approvals (`risk_officer` + `compliance_officer`)

### Runtime Policy (Capability Boundary)

Each agent has a policy document defining what it can access:

```yaml
capability_policy:
  tools:
    allowed: ["db_query", "send_email"]
    denied: ["execute_trade"]
    require_human: ["large_transfer"]
  mcp_servers:
    allowed: ["internal-kb", "market-data"]
    denied: ["external-*"]
  apis:
    allowed: ["GET /accounts/*", "GET /transactions/*"]
    denied: ["DELETE *", "*/admin/*"]
  data_classification:
    max_level: "confidential"
```

### Communication Policy (Agent-to-Agent ACL)

```yaml
communication_policy:
  mode: "allowlist"   # default deny — required for financial
  rules:
    - from: "credit-scoring-agent"
      to: "customer-data-agent"
      conditions: ["same_tenant", "same_project"]
    - from: "trading-agent"
      to: "risk-assessment-agent"
      required: true          # must call risk before acting
    - from: "*"
      to: "compliance-agent"
      allowed: true           # everyone can ask compliance
    - from: "external-*"
      to: "internal-*"
      allowed: false          # external agents cannot call internal
```

### Schedule Policy

```yaml
schedule_policy:
  active_windows:
    - cron: "0 9-16 * * MON-FRI"
      timezone: "Asia/Taipei"
  blackout_windows:
    - cron: "0 2-4 * * SAT"
  out_of_window_action: "queue"   # queue | reject | fallback_agent
```

### Cross-Account Integration Pattern

```
Harbor Central (Shared Services) ←→ Workload Accounts:

1. CT provisions workload account via Account Factory
2. CT SCP ensures workload accounts can assume harbor-agent-reporter role
3. Agents in workload accounts call Harbor API via cross-account role
4. Harbor API validates caller's account ID → maps to tenant_id
5. EventBridge cross-account bus for async events (health, status changes)
```

### SCP Guardrails (CT enforced)

- Workload accounts cannot modify Harbor Central resources
- Workload accounts must tag all agent-related resources
- Prod accounts cannot deploy unapproved agents
- All agent invocations go through Harbor's communication policy check

### Architecture Diagram

```
┌─ Management Account (Control Tower) ─────────────────────────┐
│  CT Landing Zone │ SCPs │ Account Factory │ Config Rules      │
└──────────────────────────────────────────────────────────────┘
         │ governs
         ▼
┌─ Shared Services OU ─────────────────────────────────────────┐
│  Harbor Central Account                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ CloudFront → WAF → S3 (UI)                              │ │
│  │           → API GW → Lambda (FastAPI)                    │ │
│  │                         ↓                                │ │
│  │                    DynamoDB (multi-tenant)                │ │
│  │                    EventBridge (cross-account bus)        │ │
│  │                    Cognito (federated via IAM IC)         │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         │ cross-account IAM roles
         ▼
┌─ Workload OU ────────────────────────────────────────────────┐
│  CreditCard-Prod Account                                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Bedrock AgentCore Runtime                                │ │
│  │   Agent A ──→ Harbor API (register, heartbeat)           │ │
│  │   Agent B ──→ Harbor API (discover, communicate)         │ │
│  │   harbor-agent-reporter IAM Role                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  WealthMgmt-Prod Account                                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ (same pattern)                                           │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Project Foundation ✅

### 0.1 Development Environment
- [x] Initialize Python venv, install dependencies via uv
- [x] Configure ruff, mypy, pytest
- [x] Verify project builds and imports work

### 0.2 Install ui-ux-pro-max Skill
- [x] Install ui-ux-pro-max skill to `.kiro/steering/ui-ux-pro-max/`
- [x] Verify skill is available in Kiro CLI

---

## Phase 1: CDK Infrastructure ✅

### 1.1 CDK Project Setup
- [x] Initialize CDK app (TypeScript) under `infrastructure/`
- [x] Define CDK stack structure

### 1.2 Data Layer
- [x] DynamoDB table `harbor-agent-registry`
  - PK/SK composite key
  - GSI: `status-index` (PK=status, SK=updated_at)
  - PAY_PER_REQUEST billing
  - Point-in-time recovery enabled

### 1.3 Backend Compute
- [x] Lambda function for Harbor API
  - Python 3.12 runtime, ARM64, Mangum adapter
  - IAM role with DynamoDB read/write
  - Environment variables (TABLE_NAME)
- [x] API Gateway (HTTP API)
  - Routes: /api/* → Lambda integration
  - CORS configuration, throttling (100/50)

### 1.4 Frontend Hosting
- [x] S3 bucket (block public, versioned, SSE-S3)
- [x] CloudFront distribution (S3 + API GW origins, OAC, SPA routing)
- [x] WAF WebACL (CommonRuleSet + rate limit)

### 1.5 Auth
- [x] Cognito User Pool (admin-only, no self-signup, email as username)
- [x] Cognito App Client for frontend SPA (PKCE flow)
- [x] Cognito App Client for machine-to-machine (client credentials, for cross-account agents)
- [x] API Gateway JWT authorizer linked to Cognito
- [x] CDK config flag `enableAuth` to toggle authorizer (dev can disable)

### 1.6 Deploy Scripts
- [x] `scripts/deploy.sh` and `scripts/destroy.sh`

---

## Phase 2: Backend API — Multi-Tenant + Governance Models ✅

### 2.1 Core Models (Multi-Tenant)
- [x] Add `TenantInfo` model (tenant_id, org_id, project_id, environment)
- [x] Add `OwnerInfo` model (owner_id, team, org_id)
- [x] Refactor `AgentRecord` with tenant_id, owner, visibility, lifecycle_status
- [x] Add `AgentLifecycle` enum (draft → submitted → in_review → approved → published → suspended → deprecated → retired)
- [x] Add `Visibility` enum (private, ou_shared, org_wide)
- [x] Add `AgentVersion` model (version history snapshots)
- [x] Add `AuditEntry` model (who, what, when, tenant context)
- [x] Add `HealthStatus` model (heartbeat, last_seen, error_count)

### 2.2 Governance Policy Models
- [x] Add `CapabilityPolicy` model (tools, mcp_servers, apis, data_classification)
- [x] Add `CommunicationRule` model (from, to, conditions, required flag)
- [x] Add `CommunicationPolicy` model (mode: allowlist/denylist, rules)
- [x] Add `SchedulePolicy` model (active_windows, blackout_windows, out_of_window_action)
- [x] Add `ApprovalPolicy` model (required_roles, min_approvals, prerequisites)

### 2.3 DynamoDB Store (Multi-Tenant)
- [x] Refactor PK scheme: `TENANT#{tenant_id}#AGENT#{agent_id}` for all agent items
- [x] Add tenant-index GSI (PK=tenant_id, SK=updated_at)
- [x] Add lifecycle-index GSI (PK=lifecycle_status, SK=updated_at)
- [x] Add version snapshot writes (VER#{version} SK)
- [x] Add audit log writes (AUDIT#{timestamp} SK)
- [x] Add health status writes (HEALTH SK)
- [x] Add policy CRUD (POLICY SK, COMM_RULE#, SCHEDULE#)
- [x] Add pagination support (LastEvaluatedKey → cursor)
- [x] All queries scoped by tenant_id — no cross-tenant data leaks

### 2.4 Registry Service (Lifecycle Governance)
- [x] Register agent (always starts as Draft)
- [x] Submit for review (Draft → Submitted)
- [x] Review workflow (Submitted → In Review → Approved / Rejected)
- [x] Publish (Approved → Published, checks approval_policy)
- [x] Suspend (emergency kill switch, any admin)
- [x] Deprecate (set sunset date, notify dependents)
- [x] Retire (remove from discovery, archive)
- [x] Version management — register new version, rollback, list versions
- [x] Bulk import from JSON/YAML

### 2.5 Discovery Service (Tenant-Aware)
- [x] All discovery queries scoped by tenant_id
- [x] Cross-tenant discovery for `org_wide` visibility agents
- [x] Health-aware discovery — exclude unhealthy agents
- [x] Lifecycle-aware discovery — only `published` agents discoverable
- [x] Weighted routing — priority + random weight for load distribution
- [x] Communication policy check on discovery (can caller talk to target?)

### 2.6 Health & Monitoring
- [x] PUT /agents/{id}/health — heartbeat endpoint
- [x] Health status tracking (last_seen, consecutive_failures)
- [x] Stale agent detection — mark unhealthy after N missed heartbeats
- [x] GET /health/summary — per-tenant health overview

### 2.7 A2A Agent Card Sync
- [x] POST /agents/import-a2a — import from Agent Card URL
- [x] Map A2A fields to AgentRecord (with tenant context)
- [x] Periodic re-sync (EventBridge scheduled rule)

### 2.8 Audit Log
- [x] Record all mutations with tenant context
- [x] GET /agents/{id}/audit — agent audit trail
- [x] GET /audit — tenant-scoped global audit log
- [x] Audit entries include: actor, action, before/after diff, tenant_id

### 2.9 Policy Enforcement Service (New)
- [x] Validate capability_policy on agent invocation
- [x] Evaluate communication_policy (can agent A call agent B?)
- [x] Check schedule_policy (is agent within active window?)
- [x] Return allow/deny/queue decision

### 2.10 Authentication & Authorization
- [x] Add `auth/` module — JWT token validation, tenant context extraction
- [x] FastAPI dependency `get_current_user()` — decode Cognito JWT, extract tenant_id + roles
- [x] FastAPI dependency `get_current_tenant()` — derive tenant_id from JWT `custom:account_id` claim
- [x] Role-based access: `viewer`, `developer`, `project_admin`, `risk_officer`, `compliance_officer`
- [x] Protect write endpoints (POST/PATCH/DELETE/PUT) — require authenticated user
- [x] Protect read endpoints — require at least `viewer` role
- [x] Cross-account agent auth — validate machine-to-machine client credentials token
- [x] Tenant isolation enforcement — API layer rejects requests where JWT tenant ≠ resource tenant
- [x] Local dev bypass — when `HARBOR_AUTH_DISABLED=true`, use mock tenant context

### 2.11 Notifications (EventBridge)
- [x] Emit events on lifecycle transitions
- [x] Emit events on policy violations
- [x] Cross-account EventBridge bus for workload account events
- [x] SNS topic for alerts (suspension, policy breach)

---

## Phase 3: Frontend (React + Tailwind) ✅

### 3.1 Project Setup
- [x] Initialize React app under `frontend/`
- [x] Install Tailwind CSS, React Router
- [x] Configure build for S3 deployment

### 3.2 Authentication (Frontend)
- [x] Cognito Hosted UI or custom login page (PKCE flow)
- [x] Auth context provider — store JWT, user info, tenant context
- [x] Protected routes — redirect to login if unauthenticated
- [x] API client — attach JWT Bearer token to all requests
- [x] Role-based UI — show/hide actions based on user role
- [x] Logout + token refresh

### 3.3 Design System (via ui-ux-pro-max)
- [x] Generate design system (Harbor/nautical + enterprise dashboard theme)
- [x] Create shared UI components (Button, Card, Table, Badge, Modal, Form)

### 3.4 Pages — Dashboard
- [x] Agent count by lifecycle status (draft, published, suspended, etc.)
- [x] Health overview (healthy / unhealthy / unknown) per tenant
- [x] Recent activity feed (audit entries)
- [x] Policy violation alerts
- [x] Quick actions (register, discover, review queue)

### 3.5 Pages — Agent Catalog
- [x] Agent list with search, filter by status/capability/phase/lifecycle
- [x] Tenant scope selector (my project / my OU / org-wide)
- [x] Card or table view toggle
- [x] Lifecycle status badges

### 3.6 Pages — Agent Detail
- [x] Agent metadata display
- [x] Lifecycle status with transition actions (submit, approve, publish, suspend)
- [x] Runtime policy editor (capability_policy YAML/form)
- [x] Communication rules viewer
- [x] Schedule policy editor
- [x] Version history tab
- [x] Audit log tab
- [x] Health status tab

### 3.7 Pages — Register Agent
- [x] Form for creating new agent (starts as Draft)
- [x] JSON/URL import (A2A Agent Card)
- [x] Tenant context auto-filled from user session
- [x] Policy template selector

### 3.8 Pages — Review Queue (New)
- [x] List of agents pending review (Submitted / In Review)
- [x] Review detail: agent metadata, policy, test results
- [x] Approve / Reject with comments
- [x] Approval history

### 3.9 Pages — Policy Management (New)
- [x] Communication policy editor (allowlist rules)
- [x] Schedule policy templates
- [x] Capability policy templates
- [x] Policy audit trail

### 3.10 Pages — Discovery
- [x] Search by capability / phase / skill
- [x] Results filtered by communication policy
- [x] "Resolve best agent" with policy check

### 3.11 Pages — Dependency Graph
- [x] Visual graph of agent dependencies + communication rules
- [x] Color-coded by tenant / lifecycle status
- [x] Click node to navigate to agent detail

### 3.12 Pages — Audit Log
- [x] Global audit log (tenant-scoped)
- [x] Filter by agent, action, actor, date range
- [x] Policy violation entries highlighted

### 3.13 Pages — Settings / Tenant Admin
- [x] Tenant configuration
- [x] Default policies for new agents
- [x] User role management (viewer, developer, admin, risk_officer, compliance_officer)

### 3.14 Frontend Build & Deploy
- [x] Build script, S3 sync, CloudFront invalidation

---

## Phase 4: Integration & Testing ✅

### 4.1 Backend Unit Tests
- [x] Models — serialization, validation, lifecycle transitions
- [x] Store — multi-tenant CRUD, tenant isolation verification
- [x] Registry service — lifecycle governance, approval workflow
- [x] Discovery service — tenant-scoped routing, policy-aware resolution
- [x] Policy service — capability check, communication check, schedule check
- [x] Auth — JWT validation, tenant extraction, role-based access
- [x] API routes — endpoint tests (httpx + TestClient)

### 4.2 Infrastructure Tests
- [x] CDK snapshot tests
- [x] CDK assertion tests (resource properties, GSIs, IAM policies)

### 4.3 Integration Tests
- [x] Deploy to AWS, run API tests against real endpoints
- [x] Multi-tenant isolation test (tenant A cannot see tenant B data)
- [x] Lifecycle workflow end-to-end (draft → published)
- [x] Policy enforcement test (blocked communication, schedule window)

### 4.4 Frontend Tests
- [x] Component tests (React Testing Library)
- [x] E2E smoke test (Playwright)

---

## Phase 5: Noah Integration

### 5.1 Noah Orchestrator Integration
- [ ] Replace hardcoded agent list with Harbor API call
- [ ] Replace orchestrator_dispatch.py with Harbor discovery
- [ ] Add @noah_agent decorator for auto-registration

### 5.2 Noah Agent Migration
- [ ] Register all 9 Noah agents in Harbor (with tenant context)
- [ ] Add AgentDescriptor metadata to each agent class
- [ ] Verify orchestrator discovers and dispatches via Harbor

### 5.3 Bidirectional Sync
- [ ] Noah agents report health to Harbor
- [ ] Harbor lifecycle changes reflected in orchestrator behavior

---

## Phase 6: Advanced Features

- [ ] Agent A/B testing — route traffic percentage to different versions
- [ ] Cost tracking — per-agent LLM token usage aggregation
- [ ] SLA monitoring — response time tracking, alerting on degradation
- [ ] Agent marketplace — share agent definitions across OUs
- [x] CLI tool — `harbor register`, `harbor discover`, `harbor status`
- [ ] Terraform/CDK codegen — generate IaC from agent registry

---

## Phase 7: Control Tower Integration (Enterprise) ✅

### 7.1 Account Factory Integration
- [x] CT Account Factory customization — auto-provision harbor-agent-reporter IAM role
- [x] CT lifecycle hook — register new account as Harbor tenant on creation
- [x] Account tagging — environment, business_unit, project tags enforced

### 7.2 SCP Guardrails
- [x] SCP: workload accounts cannot modify Harbor Central resources
- [x] SCP: workload accounts must tag agent-related resources
- [x] SCP: prod accounts cannot deploy unapproved agents
- [x] SCP: agent invocations must go through Harbor communication policy

### 7.3 Cross-Account IAM
- [x] harbor-agent-reporter role in each workload account
- [x] Trust policy: workload account → Harbor Central account
- [x] Harbor API validates caller account ID → tenant_id mapping
- [x] Least-privilege: reporter role can only call Harbor API endpoints

### 7.4 IAM Identity Center (SSO)
- [x] Federate Cognito with IAM Identity Center
- [x] Permission sets: HarborViewer, HarborDeveloper, HarborAdmin, HarborRiskOfficer
- [x] Map CT groups to Harbor roles
- [x] SSO login for Harbor UI

### 7.5 Cross-Account EventBridge
- [x] EventBridge bus in Harbor Central account
- [x] Cross-account event rules for workload accounts
- [x] Events: agent health, lifecycle transitions, policy violations
- [x] Workload accounts can subscribe to relevant events

### 7.6 Security Hub Integration
- [x] Custom findings for policy violations
- [x] Custom findings for unapproved agent deployments
- [x] Custom findings for communication policy breaches
- [x] Aggregate in Audit account via Security Hub

### 7.7 Config Rules
- [x] Custom Config rule: all agent resources must be registered in Harbor
- [x] Custom Config rule: no agent running without published lifecycle status
- [x] Remediation: auto-suspend unregistered agents

---

## Architecture Summary

```
┌─ Management Account (Control Tower) ─────────────────────────┐
│  CT Landing Zone │ SCPs │ Account Factory │ Config Rules      │
└──────────────────────────────────────────────────────────────┘
         │ governs
         ▼
┌─ Shared Services OU ─────────────────────────────────────────┐
│  Harbor Central Account                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ CloudFront → WAF → S3 (React SPA)                       │ │
│  │           → API GW → Lambda (FastAPI + Mangum)           │ │
│  │                         ↓                                │ │
│  │                    DynamoDB (multi-tenant)                │ │
│  │                    EventBridge (cross-account bus)        │ │
│  │                    Cognito (federated via IAM IC)         │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         │ cross-account IAM roles
         ▼
┌─ Workload OU ────────────────────────────────────────────────┐
│  CreditCard-Prod Account                                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Bedrock AgentCore Runtime                                │ │
│  │   Agent A ──→ Harbor API (register, heartbeat)           │ │
│  │   Agent B ──→ Harbor API (discover, communicate)         │ │
│  │   harbor-agent-reporter IAM Role                         │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Tailwind CSS |
| Design | ui-ux-pro-max skill |
| API | FastAPI + Mangum (Lambda adapter) |
| Compute | AWS Lambda (Python 3.12, ARM64) |
| Gateway | API Gateway HTTP API |
| Storage | DynamoDB (single-table, multi-tenant) |
| CDN | CloudFront + S3 |
| Security | WAF + Cognito + IAM Identity Center |
| Governance | Control Tower + SCPs + Config Rules |
| Events | EventBridge (cross-account) |
| Monitoring | Security Hub + CloudTrail |
| IaC | AWS CDK (TypeScript) |
| CI/CD | GitHub Actions (future) |

# ⚓ Harbor

**The Management Plane for AI Agents on AWS**

Harbor is an agent platform management system that brings API Management (APIM) principles to AI agent ecosystems running on AWS Bedrock AgentCore. It provides a centralized registry, discovery, lifecycle governance, and runtime policy enforcement — the missing management layer between your agents and production.

> When you have 30+ agents across multiple teams and accounts, you need the same governance you'd apply to microservices: registration, discovery, lifecycle management, routing, and observability. Harbor is that governance layer.

---

## The Problem

AWS Bedrock AgentCore provides the runtime — identity, memory, tools, and gateway. But it doesn't answer:

- **Which agents exist?** No central registry across accounts and teams.
- **Who approved this agent for production?** No lifecycle governance or approval workflow.
- **Can Agent A talk to Agent B?** No communication policy enforcement.
- **What tools is this agent allowed to use?** No capability boundary control.
- **What happened at 3am?** No unified audit trail across your agent fleet.

These are the same problems API Management solved for microservices a decade ago. Harbor solves them for AI agents.

## Why Harbor

| Capability | Without Harbor | With Harbor |
|-----------|---------------|-------------|
| Agent inventory | Spreadsheets, tribal knowledge | Centralized registry with metadata |
| Deployment approval | Slack messages, hope | Lifecycle pipeline: draft → review → approve → publish |
| Cross-team discovery | "Hey, does anyone have an agent that does X?" | `harbor discover -c summarization` |
| Access control | All agents can call anything | Communication ACL + capability boundaries |
| Incident response | "Which agent is causing this?" | `harbor lifecycle agent-x suspended --reason "incident-1234"` |
| Compliance audit | Manual evidence collection | Immutable audit trail with tenant context |
| Multi-account governance | Per-account silos | Control Tower integrated, org-wide visibility |

## Key Differentiators

- **Built for AWS Bedrock AgentCore** — first management platform purpose-built for the AgentCore runtime, aligned with the A2A Agent Card protocol
- **Hot-swappable agent deployment** — register, publish, suspend, and retire agents without downtime; discovery queries always return the latest published state
- **Enterprise governance** — lifecycle approval pipeline with role-based access (risk officer, compliance officer sign-off for production)
- **Multi-tenant by design** — tenant = AWS Account; integrates with Control Tower landing zones for org-wide agent governance
- **Policy enforcement** — capability boundaries (what tools/APIs/MCP servers an agent can use), communication ACL (which agents can talk to each other), and schedule windows (when agents can operate)
- **Full observability** — health monitoring, audit trail, EventBridge events, Security Hub integration

## Architecture

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

## Agent Lifecycle

Harbor enforces a governance pipeline for every agent:

```
Draft → Submitted → In Review → Approved → Published → [Suspended] → Deprecated → Retired
                        │
                   Rejected → Draft
```

| Environment | Approval Required |
|------------|-------------------|
| dev | Auto-approve (self-publish) |
| staging | 1 approval from project admin |
| prod | 2 approvals: risk officer + compliance officer |

Only **published** agents are discoverable. **Suspended** is an emergency kill switch any admin can trigger.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yikaikao/harbor.git
cd harbor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,cli]"

# Run locally
uvicorn harbor.main:app --reload --port 8100

# Use the CLI
export HARBOR_URL=http://localhost:8100/api/v1
export HARBOR_TENANT=dev-tenant
export HARBOR_OWNER=dev@harbor.local

harbor register my-agent "My Agent" --capabilities nlp,summarize
harbor list
harbor lifecycle my-agent submitted
harbor discover -c nlp --resolve
harbor health my-agent
```

See [docs/getting-started.md](docs/getting-started.md) for the full setup guide.

## Runtime Policies

### Capability Boundaries

Control what each agent can access:

```yaml
tools:
  allowed: ["db_query", "send_email"]
  denied: ["execute_trade"]
  require_human: ["large_transfer"]
mcp_servers:
  allowed: ["internal-kb", "market-data"]
  denied: ["external-*"]
data_classification:
  max_level: "confidential"
```

### Communication ACL

Control which agents can talk to each other (default: allowlist / deny-all for financial services):

```yaml
rules:
  - from: "trading-agent"
    to: "risk-assessment-agent"
    required: true          # must call risk before acting
  - from: "external-*"
    to: "internal-*"
    allowed: false          # external agents blocked from internal
```

### Schedule Windows

Control when agents can operate:

```yaml
active_windows:
  - cron: "0 9-16 * * MON-FRI"
    timezone: "Asia/Taipei"
out_of_window_action: "reject"
```

## Control Tower Integration

Harbor deploys into existing Control Tower landing zones as a Shared Services workload. Integration includes:

- **StackSet template** — auto-provisions `harbor-agent-reporter` IAM role in workload accounts
- **SCP guardrails** — protects Harbor Central resources, enforces agent tagging
- **Cross-account EventBridge** — workload accounts emit health/status events to Harbor
- **IAM Identity Center SSO** — Cognito SAML federation with enterprise IdP
- **Security Hub** — custom findings for policy violations and unapproved agents
- **Config Rules** — compliance checks for agent registration

See [docs/enterprise-integration-guide.md](docs/enterprise-integration-guide.md) for the full runbook.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Tailwind CSS + Vite |
| API | FastAPI + Mangum (Lambda adapter) |
| Compute | AWS Lambda (Python 3.12, ARM64) |
| Gateway | API Gateway HTTP API + Cognito JWT |
| Storage | DynamoDB (single-table, multi-tenant) |
| CDN | CloudFront + S3 + WAF |
| Auth | Cognito + IAM Identity Center |
| Events | EventBridge + SNS |
| Governance | Control Tower + SCPs + Config Rules |
| Monitoring | Security Hub + CloudTrail |
| IaC | AWS CDK (TypeScript) |
| CLI | Click + httpx |

## Project Structure

```
harbor/
├── src/harbor/              # Python backend (FastAPI)
│   ├── models/              # Pydantic data models (agent, policy)
│   ├── store/               # DynamoDB persistence (single-table)
│   ├── registry/            # Agent lifecycle governance
│   ├── discovery/           # Capability & phase-based lookup
│   ├── policy/              # Runtime policy enforcement
│   ├── health/              # Health monitoring & heartbeat
│   ├── audit/               # Audit log service
│   ├── auth/                # JWT validation & RBAC
│   ├── events/              # EventBridge emitter
│   ├── sync/                # A2A Agent Card import
│   ├── cli/                 # CLI tool
│   └── api/                 # FastAPI routes (29 endpoints)
├── frontend/                # React SPA (8 pages)
├── infrastructure/          # AWS CDK + CT integration
│   ├── lib/                 # CDK stack (DynamoDB, Lambda, API GW, Cognito, CloudFront, WAF, EventBridge)
│   └── ct-integration/      # StackSets, SCPs, Security Hub, Config Rules
├── tests/                   # 93 tests (75 Python + 18 CDK)
├── docs/                    # Architecture, API reference, integration guides
└── scripts/                 # Deploy & destroy scripts
```

## Documentation

- [Architecture](docs/architecture.md) — system design, data model, lifecycle, policies
- [Getting Started](docs/getting-started.md) — local dev setup, API & CLI usage
- [API Reference](docs/api-reference.md) — all 29 endpoints with examples
- [Enterprise Integration Guide](docs/enterprise-integration-guide.md) — Control Tower deployment runbook
- [IAM Identity Center Setup](docs/iam-identity-center-setup.md) — SSO configuration

## API Overview

29 REST endpoints under `/api/v1`:

| Category | Endpoints |
|----------|-----------|
| Agent CRUD | POST/GET/PATCH/DELETE `/agents` |
| Lifecycle | PUT `/agents/{id}/lifecycle` |
| Versions | POST/GET `/agents/{id}/versions` |
| Health | PUT `/agents/{id}/health`, GET `/health/summary` |
| Audit | GET `/agents/{id}/audit`, GET `/audit` |
| Discovery | GET `/discover/capability/{cap}`, `/discover/phase/{phase}`, `/discover/resolve` |
| Policies | CRUD for capability, communication, schedule policies |
| Reviews | GET `/reviews/pending`, POST `/reviews/{id}` |

See [docs/api-reference.md](docs/api-reference.md) for full request/response examples.

## License

MIT

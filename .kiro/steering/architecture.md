# Harbor — Architecture Decisions

This document defines the architectural constraints for the Harbor project.
All code generation and modifications MUST comply with these decisions.

---

## System Architecture

### Deployment Model (Control Tower Landing Zone)

Harbor deploys into an AWS Organization managed by Control Tower:

```
Management Account (Control Tower)
├── Security OU
│   ├── Log Archive Account
│   └── Audit Account (Security Hub aggregation)
├── Shared Services OU
│   └── Harbor Central Account ← Harbor lives here
├── Workload OU
│   ├── {BU}-Dev Account      ← Agents run here
│   ├── {BU}-Staging Account
│   └── {BU}-Prod Account
└── Sandbox OU
```

### Harbor Central Account Architecture

```
User → WAF → CloudFront ─→ S3 (React SPA)
                          ─→ API Gateway HTTP API (/api/*) → Lambda (FastAPI + Mangum)
                                                                  ↓
                                                             DynamoDB (multi-tenant)
                                                             EventBridge (cross-account)
                                                             Cognito (IAM IC federated)
```

### Key Decisions

1. **Cloud-agnostic registry**: Agents from AWS, Azure, GCP, or on-prem all register with the same API.
   - Harbor is a registry, not a deployment tool. Operators deploy with their own tooling.
   - `RuntimeOrigin` captures provider, runtime, region, account. All optional.
2. **Serverless-first**: Lambda + API Gateway for backend. No ECS/Fargate.
   - Rationale: Management platform has low traffic; serverless is cost-optimal.
3. **Single-table DynamoDB**: All entities in one table with PK/SK composite keys.
   - Multi-tenant: all PKs prefixed with `TENANT#{tenant_id}#`
4. **FastAPI + Mangum**: FastAPI for API definition, Mangum as Lambda adapter.
   - Same code runs locally (uvicorn) and in Lambda (Mangum handler).
5. **React SPA + Tailwind CSS**: Static frontend on S3 + CloudFront.
   - No SSR. No Next.js. Pure client-side SPA.
6. **CDK (TypeScript)**: All infrastructure as code via AWS CDK.
   - One CDK app, multiple stacks if needed.
7. **A2A Agent Card alignment**: Agent metadata schema follows the A2A protocol spec.
   - Extended with APIM + governance fields.
8. **Multi-tenant by design**: Tenant = cloud account (AWS Account / Azure Sub / GCP Project).
   - All data access scoped by tenant_id. No cross-tenant leaks.
9. **Control Tower integration**: CT provides account provisioning, SCPs, and guardrails.
   - Harbor is a consumer of CT landing zone, not a replacement.

---

## Directory Structure (Canonical)

```
harbor/
├── .kiro/
│   ├── agents/              # Kiro custom agents
│   └── steering/            # Architecture & coding standards
├── src/harbor/              # Python backend
│   ├── models/              # Pydantic data models (pure data, no I/O)
│   ├── store/               # DynamoDB persistence layer (ONLY place for boto3 DynamoDB)
│   │   ├── base.py          # Shared table access, cursor encoding
│   │   ├── agent_store.py   # Agent CRUD + capability/phase indexes
│   │   ├── health_store.py  # Health status read/write
│   │   ├── audit_store.py   # Audit entry append/query
│   │   ├── policy_store.py  # Capability, communication, schedule policy CRUD
│   │   └── version_store.py # Version snapshot read/write
│   ├── auth/                # JWT validation, tenant context, role-based access
│   ├── events/              # EventBridge emitter (infrastructure adapter, injectable)
│   ├── registry/            # Agent lifecycle + governance service
│   ├── discovery/           # Agent lookup service (tenant-aware, policy-aware)
│   ├── health/              # Health check service
│   ├── audit/               # Audit log service
│   ├── policy/              # Policy evaluation (capability, communication, schedule)
│   ├── sync/                # A2A Agent Card sync
│   ├── api/                 # FastAPI routers (HTTP concerns only)
│   │   ├── deps.py          # Shared dependencies (auth, store, service injection)
│   │   ├── agents.py        # Agent CRUD + lifecycle
│   │   ├── discovery.py     # Discovery endpoints
│   │   ├── health.py        # Heartbeat + summary
│   │   ├── audit.py         # Audit log endpoints
│   │   ├── policies.py      # Policy CRUD + evaluate
│   │   └── reviews.py       # Review queue
│   └── main.py              # Composition root (wiring only, no logic)
├── frontend/                # React SPA
│   ├── src/
│   │   ├── components/      # Shared UI components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── api/             # API client functions
│   │   └── App.tsx
│   ├── public/
│   ├── tailwind.config.js
│   └── package.json
├── infrastructure/          # AWS CDK
│   ├── bin/                 # CDK app entry
│   ├── lib/                 # CDK stacks
│   └── package.json
├── tests/
│   ├── unit/                # Python unit tests (moto)
│   ├── integration/         # API integration tests
│   └── frontend/            # React component tests
├── scripts/                 # Deploy, destroy, seed scripts
├── PLAN.md                  # Development plan
└── pyproject.toml
```

### Rules

- Backend code ONLY in `src/harbor/`. No Python files outside this tree.
- Frontend code ONLY in `frontend/src/`. No JS/TS files outside this tree.
- CDK code ONLY in `infrastructure/`. No IaC files outside this tree.
- Tests mirror source structure: `tests/unit/test_<module>.py`.
- No circular imports between `src/harbor/` subpackages.
- `store/` is the ONLY layer that touches DynamoDB. Services use store, not boto3 directly.
- `events/` is the ONLY layer that touches EventBridge. It is an infrastructure adapter, injected into services.
- `policy/` is the ONLY layer that evaluates governance rules. Services call policy, not inline checks.
- `api/` uses `APIRouter` per resource group. No closures inside `create_app()`.
- `main.py` is the composition root — creates stores, services, app. No business logic.

---

## Data Flow Rules

1. **API → Service → Store → DynamoDB**: Three-layer separation. No shortcuts.
2. **API layer** handles HTTP concerns (request parsing, response formatting, error codes).
3. **Service layer** handles business logic (validation, orchestration, side effects).
4. **Store layer** handles persistence (DynamoDB operations, serialization).
5. **Policy layer** handles governance (capability check, communication ACL, schedule window).
6. **Frontend → API Gateway → Lambda**: Frontend NEVER calls DynamoDB directly.
7. **Cross-account**: Workload accounts call Harbor API via cross-account IAM role, never direct DynamoDB.

---

## Multi-Tenant Model

### Tenant Hierarchy

```
Org (AWS Organization)
└── Business Unit (OU)
    └── Project (Account)
        └── Environment (account tag: dev/staging/prod)
```

- `tenant_id` = AWS Account ID of the caller (or Azure Subscription / GCP Project / org-assigned ID)
- Harbor maps account ID → org/OU/project via CT metadata
- All DynamoDB queries MUST include tenant_id in the key condition

### Visibility Scopes

| Scope | Who can see | Use case |
|-------|-----------|----------|
| `private` | Same account only | Dev/draft agents |
| `ou_shared` | Same OU (business unit) | Shared within a department |
| `org_wide` | Entire organization | Compliance agents, shared utilities |

---

## DynamoDB Table Design

Table name: `harbor-agent-registry`

| PK Pattern | SK Pattern | Entity |
|------------|-----------|--------|
| `TENANT#{tenant_id}#AGENT#{agent_id}` | `META` | Agent record |
| `TENANT#{tenant_id}#AGENT#{agent_id}` | `VER#{version}` | Version snapshot |
| `TENANT#{tenant_id}#AGENT#{agent_id}` | `HEALTH` | Health status |
| `TENANT#{tenant_id}#AGENT#{agent_id}` | `AUDIT#{timestamp}` | Audit entry |
| `TENANT#{tenant_id}#CAP#{capability}` | `AGENT#{agent_id}` | Capability index |
| `TENANT#{tenant_id}#PHASE#{phase}` | `AGENT#{agent_id}` | Phase index |
| `TENANT#{tenant_id}#POLICY` | `AGENT#{agent_id}` | Runtime policy |
| `COMM_RULE#{rule_id}` | `META` | Communication rule |
| `SCHEDULE#{agent_id}` | `META` | Schedule policy |

GSIs:
- `status-index`: PK=status, SK=updated_at
- `tenant-index`: PK=tenant_id, SK=updated_at
- `lifecycle-index`: PK=lifecycle_status, SK=updated_at

### Rules

- All items MUST have `pk` and `sk` fields.
- All agent items MUST be prefixed with `TENANT#{tenant_id}#`.
- Timestamps MUST be ISO 8601 UTC strings.
- Use `PAY_PER_REQUEST` billing mode.
- Enable point-in-time recovery.
- TTL field: `ttl` (Unix epoch seconds) — used for audit log expiry.

---

## Agent Lifecycle

```
Draft → Submitted → In Review → Approved → Published → [Suspended] → Deprecated → Retired
                        │
                   Rejected → Draft
```

### Lifecycle Rules

- New agents ALWAYS start as `draft`.
- Only `published` agents are discoverable.
- `suspended` is an emergency kill switch — any admin can trigger.
- `deprecated` requires a sunset date; dependents are notified.
- `retired` agents are archived and removed from discovery.
- Lifecycle transitions are recorded in audit log.

### Approval Policy (per environment)

| Environment | Required approvals |
|------------|-------------------|
| dev | Auto-approve (owner can self-publish) |
| staging | 1 approval from `project_admin` |
| prod | 2 approvals: `risk_officer` + `compliance_officer` |

---

## API Design

Base path: `/api/v1`
All endpoints require tenant context (derived from auth token or cross-account role).

| Method | Path | Purpose |
|--------|------|---------|
| POST | /agents | Register agent (starts as draft) |
| GET | /agents | List agents (tenant-scoped, filter by lifecycle/status/capability) |
| GET | /agents/{id} | Get agent detail |
| PATCH | /agents/{id} | Update agent config |
| DELETE | /agents/{id} | Deregister agent |
| PUT | /agents/{id}/lifecycle | Transition lifecycle state |
| PUT | /agents/{id}/health | Report heartbeat |
| GET | /agents/{id}/versions | List version history |
| GET | /agents/{id}/audit | Agent audit log |
| POST | /agents/import-a2a | Import from A2A Agent Card URL |
| GET | /discover/capability/{cap} | Find agents by capability (policy-aware) |
| GET | /discover/phase/{phase} | Find agents by phase (policy-aware) |
| GET | /discover/resolve | Resolve best agent (policy-aware) |
| GET | /health/summary | Tenant health overview |
| GET | /audit | Tenant-scoped global audit log |
| POST | /policies/capability | Create/update capability policy |
| GET | /policies/capability/{agent_id} | Get agent capability policy |
| POST | /policies/communication | Create/update communication rules |
| GET | /policies/communication | List communication rules |
| POST | /policies/schedule | Create/update schedule policy |
| GET | /policies/schedule/{agent_id} | Get agent schedule policy |
| POST | /policies/evaluate | Evaluate policy (can A call B right now?) |
| GET | /reviews/pending | List agents pending review |
| POST | /reviews/{agent_id} | Submit review (approve/reject) |

### Rules

- All endpoints under `/api/v1` prefix.
- Response format: JSON. Use Pydantic models for serialization.
- Error responses: `{"detail": "message"}` with appropriate HTTP status.
- Pagination: `?limit=N&cursor=<token>` using DynamoDB LastEvaluatedKey.
- All endpoints require authentication (Cognito JWT or cross-account IAM).
- Tenant context derived from auth token — never passed as query param.

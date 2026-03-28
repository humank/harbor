# Harbor — Architecture Decisions

This document defines the architectural constraints for the Harbor project.
All code generation and modifications MUST comply with these decisions.

---

## System Architecture

```
User → WAF → CloudFront ─→ S3 (React SPA)
                          ─→ API Gateway HTTP API (/api/*) → Lambda (FastAPI + Mangum)
                                                                  ↓
                                                             DynamoDB
                                                        (harbor-agent-registry)
```

### Key Decisions

1. **Serverless-first**: Lambda + API Gateway for backend. No ECS/Fargate.
   - Rationale: Management platform has low traffic; serverless is cost-optimal.
2. **Single-table DynamoDB**: All entities in one table with PK/SK composite keys.
   - Partition key patterns: `AGENT#`, `CAP#`, `PHASE#`, `AUDIT#`, `HEALTH#`
3. **FastAPI + Mangum**: FastAPI for API definition, Mangum as Lambda adapter.
   - Same code runs locally (uvicorn) and in Lambda (Mangum handler).
4. **React SPA + Tailwind CSS**: Static frontend on S3 + CloudFront.
   - No SSR. No Next.js. Pure client-side SPA.
5. **CDK (TypeScript)**: All infrastructure as code via AWS CDK.
   - One CDK app, multiple stacks if needed.
6. **A2A Agent Card alignment**: Agent metadata schema follows the A2A protocol spec.
   - Fields: name, description, url, skills, capabilities, auth_schemes.
   - Extended with APIM fields: status, version, phase_affinity, routing_rules, tags.

---

## Directory Structure (Canonical)

```
harbor/
├── .kiro/
│   ├── agents/              # Kiro custom agents
│   └── steering/            # Architecture & coding standards
├── src/harbor/              # Python backend
│   ├── models/              # Pydantic data models
│   ├── store/               # DynamoDB persistence layer
│   ├── registry/            # Agent lifecycle service
│   ├── discovery/           # Agent lookup service
│   ├── health/              # Health check service
│   ├── audit/               # Audit log service
│   ├── sync/                # A2A Agent Card sync
│   ├── api/                 # FastAPI routes
│   └── main.py              # Entrypoint (uvicorn / Mangum)
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

---

## Data Flow Rules

1. **API → Service → Store → DynamoDB**: Three-layer separation. No shortcuts.
2. **API layer** handles HTTP concerns (request parsing, response formatting, error codes).
3. **Service layer** handles business logic (validation, orchestration, side effects).
4. **Store layer** handles persistence (DynamoDB operations, serialization).
5. **Frontend → API Gateway → Lambda**: Frontend NEVER calls DynamoDB directly.

---

## DynamoDB Table Design

Table name: `harbor-agent-registry`

| PK Pattern | SK Pattern | Entity |
|------------|-----------|--------|
| `AGENT#{agent_id}` | `META` | Agent record (current) |
| `AGENT#{agent_id}` | `VER#{version}` | Version snapshot |
| `AGENT#{agent_id}` | `HEALTH` | Health status |
| `AGENT#{agent_id}` | `AUDIT#{timestamp}` | Audit entry |
| `CAP#{capability}` | `AGENT#{agent_id}` | Capability index |
| `PHASE#{phase}` | `AGENT#{agent_id}` | Phase index |

GSI: `status-index` (PK=status, SK=updated_at)

### Rules

- All items MUST have `pk` and `sk` fields.
- Timestamps MUST be ISO 8601 UTC strings.
- Use `PAY_PER_REQUEST` billing mode.
- Enable point-in-time recovery.
- TTL field: `ttl` (Unix epoch seconds) — used for audit log expiry.

---

## API Design

Base path: `/api/v1`

| Method | Path | Purpose |
|--------|------|---------|
| POST | /agents | Register agent |
| GET | /agents | List agents (query: status, capability, phase) |
| GET | /agents/{id} | Get agent detail |
| PATCH | /agents/{id} | Update agent config |
| DELETE | /agents/{id} | Deregister agent |
| PUT | /agents/{id}/status | Set agent status |
| PUT | /agents/{id}/health | Report heartbeat |
| GET | /agents/{id}/versions | List version history |
| GET | /agents/{id}/audit | Agent audit log |
| POST | /agents/import-a2a | Import from A2A Agent Card URL |
| GET | /discover/capability/{cap} | Find agents by capability |
| GET | /discover/phase/{phase} | Find agents by phase |
| GET | /discover/resolve | Resolve best agent |
| GET | /health/summary | Platform health overview |
| GET | /audit | Global audit log |

### Rules

- All endpoints under `/api/v1` prefix.
- Response format: JSON. Use Pydantic models for serialization.
- Error responses: `{"detail": "message"}` with appropriate HTTP status.
- Pagination: `?limit=N&cursor=<token>` using DynamoDB LastEvaluatedKey.
- Write endpoints require authentication (Cognito JWT or API key).
- Read endpoints are public by default.

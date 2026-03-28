# Harbor — Getting Started

Quickstart guide for running Harbor locally, using the CLI, calling the API, and deploying to AWS.

## Prerequisites

- **Python 3.12+** — backend runtime
- **Node.js 20+** — frontend (Vite) and CDK
- **AWS CLI** configured — for deployment (`aws configure`)
- **Docker** — for Lambda bundling during CDK deploy
- **uv** (recommended) or **pip** — Python package management

## Local Development Setup

### Backend

```bash
git clone https://github.com/yikaikao/harbor.git
cd harbor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,cli]"

# Start the API server
uvicorn harbor.main:app --reload --port 8100
```

The API is now running at `http://localhost:8100`. Docs at `http://localhost:8100/docs`.

> **Note:** Auth is disabled locally (`HARBOR_AUTH_DISABLED=true`). DynamoDB calls will fail without a real table — use `moto` in tests or deploy to AWS for a live table.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. Vite proxies `/api` requests to `localhost:8100` automatically (configured in `vite.config.ts`).

### Running Tests

```bash
# Python unit tests (75 tests, uses moto mock for DynamoDB)
pytest tests/unit/ -v

# CDK infrastructure tests (18 tests)
cd infrastructure && npm test

# Lint & type check
ruff check src/harbor/
mypy src/harbor/
```

## Using the CLI

The `harbor` CLI is installed via `pip install -e ".[cli]"`. Set these environment variables first:

```bash
export HARBOR_URL=http://localhost:8100/api/v1
export HARBOR_TENANT=dev-tenant
export HARBOR_OWNER=dev@harbor.local
```

### `harbor register` — Register a new agent

```bash
harbor register my-agent "My Agent" \
  --capabilities nlp,summarize \
  --desc "Summarizes documents using NLP"
# ✓ Registered my-agent (lifecycle: draft)
```

### `harbor list` — List agents

```bash
harbor list
harbor list --lifecycle published
harbor list --lifecycle draft --limit 5
```

### `harbor status` — Show agent detail

```bash
harbor status my-agent
# Agent:      My Agent (my-agent)
# Lifecycle:  draft
# Visibility: private
# Caps:       nlp, summarize
```

### `harbor lifecycle` — Transition lifecycle state

```bash
harbor lifecycle my-agent submitted
harbor lifecycle my-agent published
harbor lifecycle my-agent suspended --reason "incident-1234"
```

Valid targets: `draft`, `submitted`, `in_review`, `approved`, `published`, `suspended`, `deprecated`, `retired`.

### `harbor discover` — Find agents by capability or phase

```bash
harbor discover -c nlp
harbor discover -p planning
harbor discover -c summarize --resolve   # returns best match
```

### `harbor health` — Heartbeat or health summary

```bash
harbor health my-agent    # send heartbeat for a specific agent
harbor health             # show tenant health summary
```

## Using the API

All endpoints are under `/api/v1`. Full reference: [docs/api-reference.md](api-reference.md).

### Register an agent

```bash
curl -X POST http://localhost:8100/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my-agent",
    "name": "My Agent",
    "description": "Summarizes documents",
    "tenant_id": "dev-tenant",
    "owner": {"owner_id": "dev@harbor.local", "team": "", "org_id": ""},
    "capabilities": ["nlp", "summarize"]
  }'
```

### List agents

```bash
curl http://localhost:8100/api/v1/agents
curl http://localhost:8100/api/v1/agents?lifecycle=published&limit=10
```

### Transition lifecycle

```bash
curl -X PUT "http://localhost:8100/api/v1/agents/my-agent/lifecycle?target=submitted"
```

### Discover by capability

```bash
curl http://localhost:8100/api/v1/discover/capability/nlp
curl http://localhost:8100/api/v1/discover/resolve?capability=summarize
```

### Send heartbeat

```bash
curl -X PUT http://localhost:8100/api/v1/agents/my-agent/health
```

## Deploying to AWS

```bash
cd infrastructure
npm install
npx cdk bootstrap   # first time only
npx cdk deploy
```

CDK outputs after deploy:

| Output | Description |
|--------|-------------|
| `ApiUrl` | API Gateway endpoint (`https://xxx.execute-api.region.amazonaws.com`) |
| `CloudFrontUrl` | CloudFront distribution URL (frontend + API) |
| `UserPoolId` | Cognito User Pool ID (if auth enabled) |

To deploy the frontend to S3:

```bash
cd frontend
npm run build
aws s3 sync dist/ s3://<frontend-bucket-name> --delete
aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
```

To tear down:

```bash
cd infrastructure
npx cdk destroy
```

## Frontend Development

### Directory structure

```
frontend/src/
├── components/
│   ├── ui/              # Button, Badge, Card, Modal, Table
│   └── layout/          # Sidebar, Header, PageContainer
├── pages/               # One file per route
│   ├── Dashboard.tsx
│   ├── AgentCatalog.tsx
│   ├── AgentDetail.tsx
│   ├── RegisterAgent.tsx
│   ├── Discovery.tsx
│   ├── PolicyManagement.tsx
│   ├── AuditLog.tsx
│   └── ReviewQueue.tsx
├── api/
│   └── client.ts        # Typed fetch wrapper
├── types/
│   └── agent.ts         # TypeScript types (mirrors backend models)
├── auth/                # AuthContext, ProtectedRoute
├── hooks/               # Custom React hooks
├── App.tsx              # Router + layout
└── main.tsx             # Entry point
```

### Adding a new page

1. Create `frontend/src/pages/MyPage.tsx`
2. Add a route in `App.tsx`
3. Use the API client from `api/client.ts` for data fetching

### API client usage

```typescript
import { getAgents, registerAgent } from '../api/client';

const agents = await getAgents();
const newAgent = await registerAgent({ agent_id: 'x', name: 'X', ... });
```

### Build for production

```bash
cd frontend
npm run build    # outputs to frontend/dist/
```

## Next Steps

- [API Reference](api-reference.md) — all 29 endpoints with request/response examples
- [Architecture](architecture.md) — system design, data model, lifecycle, policies
- [Enterprise Integration Guide](enterprise-integration-guide.md) — Control Tower deployment
- [IAM Identity Center Setup](iam-identity-center-setup.md) — SSO configuration

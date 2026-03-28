# 🚢 Harbor

**Agent Platform Management — Registry, Discovery, and Governance for AI Agents**

> The port authority for your AI agent fleet.

Harbor brings API Management (APIM) principles to AI agent ecosystems running on AWS Bedrock AgentCore. When you have 30+ agents, you need the same governance you'd apply to microservices: registration, discovery, lifecycle management, routing, and observability.

## Why

AWS Bedrock AgentCore provides the runtime, identity, memory, and gateway layers. What's missing is a **management plane** — a centralized registry where agents are registered, discovered, configured, and governed. Harbor fills that gap.

## Architecture

```
┌─────────────────────────────────────────┐
│  Management UI                          │  ← Users configure agents
│  CRUD agents / capabilities / routing   │
├─────────────────────────────────────────┤
│  Harbor API (FastAPI)                   │  ← REST API
│  POST/GET/PATCH/DELETE /agents          │
│  GET /discover/capability/{cap}         │
│  GET /discover/phase/{phase}            │
├─────────────────────────────────────────┤
│  Registry Service    Discovery Service  │  ← Business logic
├─────────────────────────────────────────┤
│  AgentStore (DynamoDB)                  │  ← Single-table design
│  AGENT# / CAP# / PHASE# partitions     │
├─────────────────────────────────────────┤
│  AWS Bedrock AgentCore Runtime          │  ← Agent execution
│  A2A Protocol / Agent Cards             │
└─────────────────────────────────────────┘
```

## Data Model

Agent metadata is aligned with the [A2A Agent Card](https://google.github.io/A2A/) schema, extended with APIM fields:

| Field | Source | Purpose |
|-------|--------|---------|
| `agent_id`, `name`, `url` | A2A Agent Card | Identity & endpoint |
| `skills`, `capabilities` | A2A Agent Card | What the agent can do |
| `auth_schemes` | A2A Agent Card | Authentication requirements |
| `status`, `version` | APIM | Lifecycle management |
| `phase_affinity`, `routing_rules` | APIM | Orchestrator dispatch |
| `model_id`, `timeout_seconds` | APIM | Runtime configuration |
| `tags`, `created_by` | APIM | Governance & audit |

## Quick Start

```bash
cd ~/git/harbor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run locally (needs DynamoDB local or moto for tests)
uvicorn harbor.main:app --reload --port 8100
```

## API

```bash
# Register an agent
curl -X POST http://localhost:8100/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-a-archaeologist",
    "name": "The Archaeologist",
    "capabilities": ["cobol_analysis", "ddd_discovery"],
    "phase_affinity": ["discovery"],
    "routing_rules": [{"phase": "discovery", "priority": 10}]
  }'

# Discover agents for a phase
curl http://localhost:8100/discover/phase/discovery

# Discover by capability
curl http://localhost:8100/discover/capability/cobol_analysis

# Resolve best agent
curl "http://localhost:8100/discover/resolve?phase=discovery"
```

## DynamoDB Table

Single-table design with composite keys:

```
PK                  SK                  Purpose
AGENT#{id}          META                Agent record
CAP#{capability}    AGENT#{id}          Capability → agent index
PHASE#{phase}       AGENT#{id}          Phase → agent index
```

See `infrastructure/README.md` for table creation commands.

## Project Structure

```
src/harbor/
├── models/         # Pydantic data models (A2A + APIM)
├── store/          # DynamoDB persistence
├── registry/       # Agent lifecycle management
├── discovery/      # Capability & phase-based lookup
├── api/            # FastAPI REST endpoints
└── main.py         # Entrypoint
```

## Roadmap

- [ ] Management UI (React)
- [ ] A2A Agent Card sync — auto-import from `/.well-known/agent-card.json`
- [ ] Health check / heartbeat monitoring
- [ ] Agent version management (A/B testing)
- [ ] Integration with Project Noah orchestrator
- [ ] Rate limiting & quota management
- [ ] Dependency graph visualization

## License

MIT

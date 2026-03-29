# Harbor — Design Principles

Enforced design principles for all code in this project.
Every new file, class, and function MUST comply. No exceptions.

---

## Core Identity

Harbor is a **registry and governance platform**, not a deployment tool.
Agents are deployed by their operators using their own tooling (Terraform, CDK, ARM Template, gcloud, etc.).
Harbor receives metadata, enforces lifecycle governance, provides discovery, and evaluates policies.

---

## Layered Architecture (Strict)

```
API (routes)  →  Service (business logic)  →  Store (persistence)  →  DynamoDB
     ↑                    ↑                          ↑
  HTTP concerns     Domain logic only         boto3 lives here ONLY
```

### Rules

1. **API → Service → Store → DynamoDB** — three-layer separation, no shortcuts.
2. **API layer** handles HTTP concerns only: request parsing, response formatting, error code mapping. No business logic. No direct store calls.
3. **Service layer** handles business logic: validation, orchestration, audit logging, event emission. Services call stores, never boto3 directly.
4. **Store layer** handles persistence only: DynamoDB operations, serialization, key construction. Returns Pydantic models, never raw dicts from public methods.
5. **Policy layer** handles governance rule evaluation. Services call policy, never inline checks.
6. **NEVER skip a layer.** If an API endpoint needs data, it goes through a service. If a service needs persistence, it goes through a store.

### Violations to watch for

- Route handler calling `store.put_*()` or `store.get_*()` directly → must go through service
- Service importing `boto3` → must go through store
- Route handler containing `if/else` business logic → must move to service
- Store method containing business rules (e.g., lifecycle validation) → must move to service

---

## Single Responsibility Principle (SRP)

Each class has ONE reason to change.

### Store classes — one per entity group

```
store/
├── base.py              # Shared DynamoDB table access, cursor encoding/decoding
├── agent_store.py       # Agent CRUD + capability/phase indexes
├── health_store.py      # Health status read/write
├── audit_store.py       # Audit entry append/query
├── policy_store.py      # Capability, communication, schedule policy CRUD
└── version_store.py     # Version snapshot read/write
```

- Each store class manages ONE entity type (or tightly related group).
- All store classes share the same DynamoDB table via a base class.
- No God Objects — if a store class exceeds ~150 lines, it probably has too many responsibilities.

### Service classes — one per domain concern

```
registry/service.py      # Agent registration + lifecycle transitions
discovery/service.py     # Agent lookup (capability, phase, resolve)
health/service.py        # Heartbeat processing, staleness detection
audit/service.py         # Audit log queries
policy/service.py        # Policy evaluation (capability, communication, schedule)
sync/service.py          # A2A Agent Card import
```

### API routers — one per resource group

```
api/
├── deps.py              # Shared FastAPI dependencies (auth, store, service injection)
├── agents.py            # Agent CRUD + lifecycle
├── discovery.py         # Discovery endpoints
├── health.py            # Heartbeat + summary
├── audit.py             # Audit log endpoints
├── policies.py          # Policy CRUD + evaluate
└── reviews.py           # Review queue
```

- Use FastAPI `APIRouter`, not closures inside `create_app()`.
- Each router file is independently testable.

---

## Dependency Injection

All dependencies flow through constructors. No hard-coded `new` inside classes.

```python
# GOOD — injectable, testable
class RegistryService:
    def __init__(self, store: AgentStore, events: EventEmitter) -> None:
        self.store = store
        self.events = events

# BAD — hidden dependency, untestable
class RegistryService:
    def __init__(self, store: AgentStore) -> None:
        self.store = store
        self._events = EventEmitter()  # can't mock this
```

### Rules

- Constructor parameters for ALL collaborators (stores, services, emitters).
- FastAPI `Depends()` for wiring in the API layer.
- `main.py` is the composition root — it creates all instances and wires them together.
- Tests inject mocks/fakes through the same constructors.

---

## boto3 Isolation

`boto3` is ONLY allowed in two places:

1. `src/harbor/store/` — DynamoDB operations
2. `src/harbor/events/emitter.py` — EventBridge operations (infrastructure concern, not business logic)

Nowhere else. If a new AWS service integration is needed, it gets its own module under `store/` or a dedicated infrastructure module.

### EventEmitter is an infrastructure adapter, not a store

EventEmitter wraps EventBridge. It is injected into services, never instantiated inside them.

---

## Data Models

- ALL data objects are Pydantic `BaseModel`. No plain classes for data transfer.
- Models live in `src/harbor/models/`. No model definitions elsewhere.
- Models are pure data — no I/O, no business logic, no side effects.
- If a response shape differs from the domain model, create a separate response model in the API layer.

```python
# GOOD — Pydantic model, serializable, validatable
class PolicyDecision(BaseModel):
    allowed: bool
    reason: str = ""

# BAD — plain class, can't serialize, can't validate
class PolicyDecision:
    def __init__(self, allowed, reason=""):
        self.allowed = allowed
        self.reason = reason
```

---

## Error Handling

- Domain exceptions defined in `src/harbor/exceptions.py`.
- Store layer catches `ClientError` → raises domain exceptions.
- Service layer raises domain exceptions for business rule violations.
- API layer catches domain exceptions → maps to HTTP status codes.
- NEVER catch bare `Exception` unless re-raising.
- NEVER raise `HTTPException` outside the API layer.

```
Store:    ClientError         → AgentNotFoundError
Service:  business rule fail  → InvalidLifecycleTransitionError
API:      AgentNotFoundError  → HTTPException(404)
```

---

## Query Efficiency

- No N+1 queries. If you need data for N items, use a batch operation or a GSI query.
- Tenant-wide queries (e.g., audit across all agents) MUST use a GSI, not iterate-and-query.
- If a method does `for item in items: store.get(item)`, it's an N+1 and must be refactored.

---

## Cross-Cloud Agent Model

Harbor supports agents from any cloud provider. The data model reflects this:

- `RuntimeOrigin` — where the agent runs (provider, runtime, region, account)
- `EndpointInfo` — how to reach the agent (url, protocol, auth)
- `ComplianceInfo` — governance metadata (certifications, data residency, PII handling)
- `DependencyInfo` — what the agent needs (other agents, tools, models)

All these are optional with sensible defaults. Minimum registration requires only: `agent_id`, `name`, `tenant_id`, `owner`.

---

## Testing Principles

- Each test tests ONE behavior.
- Tests use constructor injection — same constructors as production code.
- Use `moto` for DynamoDB mocking. No real AWS calls in unit tests.
- Store tests verify persistence. Service tests verify business logic. API tests verify HTTP contract.
- If a class is hard to test, the design is wrong — fix the design, not the test.

---

## Checklist for New Code

Before writing any new code, verify:

- [ ] Does the API handler delegate ALL logic to a service?
- [ ] Does the service use store methods, never boto3 directly?
- [ ] Are all collaborators injected via constructor?
- [ ] Is the data model a Pydantic BaseModel?
- [ ] Are domain exceptions used (not HTTPException in services)?
- [ ] Is there an audit trail for state-changing operations?
- [ ] Are queries efficient (no N+1)?
- [ ] Is the class under ~150 lines (SRP check)?

# Harbor — API Reference

Base URL: `/api/v1`

**Authentication:** Bearer token (Cognito JWT). In dev mode (`HARBOR_AUTH_DISABLED=true`), auth is bypassed and a dev tenant context is used.

**Tenant context:** Derived from the auth token — never passed as a query parameter. All data access is scoped to the caller's tenant.

**Pagination:** Cursor-based. Use `?limit=N&cursor=<token>`. List responses return `{"items": [...], "cursor": "..."}`.

**Errors:** All errors return `{"detail": "message"}` with the appropriate HTTP status code.

---

## Agent CRUD

### POST /agents

Register a new agent. Starts in `draft` lifecycle state.

**Role required:** `developer`

**Request body:**

```json
{
  "agent_id": "credit-scoring-agent",
  "name": "Credit Scoring Agent",
  "description": "Evaluates creditworthiness using ML models",
  "version": "1.0.0",
  "tenant_id": "123456789012",
  "owner": {
    "owner_id": "alice@megabank.com",
    "team": "risk",
    "org_id": "megabank"
  },
  "visibility": "private",
  "capabilities": ["credit-scoring", "risk-assessment"],
  "skills": [
    {
      "id": "score-applicant",
      "name": "Score Applicant",
      "description": "Generates a credit score for a loan applicant",
      "input_modes": ["text"],
      "output_modes": ["text"],
      "tags": ["credit", "scoring"]
    }
  ],
  "phase_affinity": ["underwriting"],
  "model_id": "anthropic.claude-sonnet-4-20250514",
  "max_concurrency": 5,
  "timeout_seconds": 300,
  "tags": {"department": "lending", "cost-center": "CC-1234"}
}
```

**Response:** `201 Created`

```json
{
  "agent_id": "credit-scoring-agent",
  "name": "Credit Scoring Agent",
  "description": "Evaluates creditworthiness using ML models",
  "version": "1.0.0",
  "tenant_id": "123456789012",
  "owner": {"owner_id": "alice@megabank.com", "team": "risk", "org_id": "megabank"},
  "visibility": "private",
  "lifecycle_status": "draft",
  "capabilities": ["credit-scoring", "risk-assessment"],
  "skills": [{"id": "score-applicant", "name": "Score Applicant", "description": "Generates a credit score for a loan applicant", "input_modes": ["text"], "output_modes": ["text"], "tags": ["credit", "scoring"]}],
  "phase_affinity": ["underwriting"],
  "routing_rules": [],
  "tags": {"department": "lending", "cost-center": "CC-1234"},
  "model_id": "anthropic.claude-sonnet-4-20250514",
  "max_concurrency": 5,
  "timeout_seconds": 300,
  "retry_policy": {"max_retries": 3, "backoff": "exponential"},
  "url": null,
  "auth_schemes": [],
  "sunset_date": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "created_by": "alice@megabank.com"
}
```

**Errors:**

| Status | Detail |
|--------|--------|
| 409 | `Agent credit-scoring-agent already exists` |

---

### GET /agents

List agents scoped to the caller's tenant.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `lifecycle` | string | — | Filter by lifecycle status |
| `limit` | int | 50 | Max items per page |
| `cursor` | string | — | Pagination cursor from previous response |

**Response:** `200 OK`

```json
{
  "items": [
    {
      "agent_id": "credit-scoring-agent",
      "name": "Credit Scoring Agent",
      "lifecycle_status": "published",
      "capabilities": ["credit-scoring", "risk-assessment"],
      "owner": {"owner_id": "alice@megabank.com", "team": "risk", "org_id": "megabank"},
      "...": "..."
    }
  ],
  "cursor": "eyJwayI6ICJURU5BTlQjMTIzNDU2Nzg5MDEyI0FHRU5UI2NyZWRpdC1zY29yaW5nLWFnZW50In0="
}
```

`cursor` is `null` when there are no more pages.

---

### GET /agents/{agent_id}

Get a single agent by ID.

**Response:** `200 OK` — Full `AgentRecord` (same shape as POST response).

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | `Agent credit-scoring-agent not found` |

---

### PATCH /agents/{agent_id}

Update agent configuration fields.

**Role required:** `developer`

**Request body:** Partial update — only include fields to change.

```json
{
  "description": "Updated credit scoring with v2 model",
  "max_concurrency": 10,
  "tags": {"department": "lending", "cost-center": "CC-5678"}
}
```

**Response:** `200 OK` — Full updated `AgentRecord`.

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | `Agent credit-scoring-agent not found` |

---

### DELETE /agents/{agent_id}

Deregister an agent. Removes from registry and discovery.

**Role required:** `project_admin`

**Response:** `200 OK`

```json
{
  "deleted": "credit-scoring-agent"
}
```

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | `Agent credit-scoring-agent not found` |

---

## Lifecycle

### PUT /agents/{agent_id}/lifecycle

Transition an agent's lifecycle state.

**Role required:** `project_admin`

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | string | yes | Target lifecycle state |
| `reason` | string | no | Reason for transition |

Valid lifecycle states: `draft`, `submitted`, `in_review`, `approved`, `published`, `suspended`, `deprecated`, `retired`.

**Valid transitions:**

```
draft → submitted → in_review → approved → published → deprecated → retired
                        ↓                      ↓
                    rejected → draft        suspended
```

**Example:** `PUT /api/v1/agents/credit-scoring-agent/lifecycle?target=submitted&reason=Ready+for+review`

**Response:** `200 OK` — Full `AgentRecord` with updated `lifecycle_status`.

**Errors:**

| Status | Detail |
|--------|--------|
| 400 | `Cannot transition from draft to published` |
| 404 | `Agent credit-scoring-agent not found` |

---

## Versions

### POST /agents/{agent_id}/versions

Create an immutable version snapshot of the agent's current state.

**Role required:** `developer`

**Response:** `200 OK`

```json
{
  "agent_id": "credit-scoring-agent",
  "tenant_id": "123456789012",
  "version": "1.0.0",
  "snapshot": {
    "agent_id": "credit-scoring-agent",
    "name": "Credit Scoring Agent",
    "capabilities": ["credit-scoring", "risk-assessment"],
    "lifecycle_status": "published",
    "...": "..."
  },
  "created_at": "2025-01-15T14:00:00Z",
  "created_by": "alice@megabank.com"
}
```

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | `Agent credit-scoring-agent not found` |

---

### GET /agents/{agent_id}/versions

List all version snapshots for an agent.

**Response:** `200 OK`

```json
[
  {
    "agent_id": "credit-scoring-agent",
    "tenant_id": "123456789012",
    "version": "1.0.0",
    "snapshot": {"...": "..."},
    "created_at": "2025-01-15T14:00:00Z",
    "created_by": "alice@megabank.com"
  },
  {
    "agent_id": "credit-scoring-agent",
    "tenant_id": "123456789012",
    "version": "0.9.0",
    "snapshot": {"...": "..."},
    "created_at": "2025-01-10T09:00:00Z",
    "created_by": "alice@megabank.com"
  }
]
```

---

## Health

### PUT /agents/{agent_id}/health

Send a heartbeat to report the agent is alive.

**Response:** `200 OK`

```json
{
  "agent_id": "credit-scoring-agent",
  "tenant_id": "123456789012",
  "state": "healthy",
  "last_seen": "2025-01-15T15:30:00Z",
  "consecutive_failures": 0,
  "error_message": null,
  "updated_at": "2025-01-15T15:30:00Z"
}
```

---

### GET /health/summary

Get a health overview for all agents in the caller's tenant.

**Response:** `200 OK`

```json
{
  "healthy": 12,
  "unhealthy": 2,
  "unknown": 3
}
```

---

## Audit

### GET /agents/{agent_id}/audit

Get the audit trail for a specific agent.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max entries to return |

**Response:** `200 OK`

```json
[
  {
    "agent_id": "credit-scoring-agent",
    "tenant_id": "123456789012",
    "action": "lifecycle_changed",
    "actor": "alice@megabank.com",
    "timestamp": "2025-01-15T14:00:00Z",
    "details": {"from": "draft", "to": "submitted", "reason": "Ready for review"}
  },
  {
    "agent_id": "credit-scoring-agent",
    "tenant_id": "123456789012",
    "action": "registered",
    "actor": "alice@megabank.com",
    "timestamp": "2025-01-15T10:30:00Z",
    "details": {}
  }
]
```

---

### GET /audit

Get the tenant-wide audit log across all agents.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 100 | Max entries to return |

**Response:** `200 OK` — Same shape as agent audit, but includes entries from all agents in the tenant.

---

## Discovery

Only `published` agents are returned by discovery endpoints.

### GET /discover/capability/{capability}

Find agents that have a specific capability.

**Example:** `GET /api/v1/discover/capability/credit-scoring`

**Response:** `200 OK`

```json
[
  {
    "agent_id": "credit-scoring-agent",
    "name": "Credit Scoring Agent",
    "capabilities": ["credit-scoring", "risk-assessment"],
    "lifecycle_status": "published",
    "owner": {"owner_id": "alice@megabank.com", "team": "risk", "org_id": "megabank"},
    "...": "..."
  }
]
```

---

### GET /discover/phase/{phase}

Find agents with affinity for a specific phase.

**Example:** `GET /api/v1/discover/phase/underwriting`

**Response:** `200 OK` — Same shape as capability discovery.

---

### GET /discover/resolve

Resolve the single best agent for a given capability and/or phase, using routing rules and priority.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `capability` | string | Capability to match |
| `phase` | string | Phase to match |

At least one of `capability` or `phase` must be provided.

**Example:** `GET /api/v1/discover/resolve?capability=credit-scoring&phase=underwriting`

**Response:** `200 OK` — Single `AgentRecord` or `null` if no match.

```json
{
  "agent_id": "credit-scoring-agent",
  "name": "Credit Scoring Agent",
  "capabilities": ["credit-scoring", "risk-assessment"],
  "phase_affinity": ["underwriting"],
  "routing_rules": [{"phase": "underwriting", "capability": "credit-scoring", "priority": 10, "condition": null}],
  "...": "..."
}
```

---

## Policies

### POST /policies/capability

Create or update a capability boundary policy for an agent.

**Role required:** `project_admin`

**Request body:**

```json
{
  "agent_id": "credit-scoring-agent",
  "tenant_id": "123456789012",
  "tools": {
    "allowed": ["db_query", "credit_bureau_lookup"],
    "denied": ["execute_trade"],
    "require_human": ["manual_override"]
  },
  "mcp_servers": {
    "allowed": ["internal-kb", "credit-data"],
    "denied": ["external-*"],
    "require_human": []
  },
  "apis": {
    "allowed": ["risk-api", "scoring-api"],
    "denied": [],
    "require_human": []
  },
  "data_classification_max": "confidential"
}
```

**Response:** `200 OK`

```json
{"status": "ok"}
```

---

### GET /policies/capability/{agent_id}

Get the capability policy for an agent.

**Example:** `GET /api/v1/policies/capability/credit-scoring-agent`

**Response:** `200 OK` — Full `CapabilityPolicy` object, or `null` if none set.

```json
{
  "agent_id": "credit-scoring-agent",
  "tenant_id": "123456789012",
  "tools": {"allowed": ["db_query", "credit_bureau_lookup"], "denied": ["execute_trade"], "require_human": ["manual_override"]},
  "mcp_servers": {"allowed": ["internal-kb", "credit-data"], "denied": ["external-*"], "require_human": []},
  "apis": {"allowed": ["risk-api", "scoring-api"], "denied": [], "require_human": []},
  "data_classification_max": "confidential",
  "updated_at": "2025-01-15T16:00:00Z"
}
```

---

### POST /policies/communication

Create or update an agent-to-agent communication ACL rule.

**Role required:** `project_admin`

**Request body:**

```json
{
  "rule_id": "rule-001",
  "from_agent": "credit-scoring-agent",
  "to_agent": "risk-assessment-agent",
  "allowed": true,
  "required": true,
  "conditions": ["same_tenant"]
}
```

**Response:** `200 OK`

```json
{"status": "ok"}
```

---

### GET /policies/communication

List all communication ACL rules.

**Response:** `200 OK`

```json
[
  {
    "rule_id": "rule-001",
    "from_agent": "credit-scoring-agent",
    "to_agent": "risk-assessment-agent",
    "allowed": true,
    "required": true,
    "conditions": ["same_tenant"]
  },
  {
    "rule_id": "rule-002",
    "from_agent": "external-*",
    "to_agent": "internal-*",
    "allowed": false,
    "required": false,
    "conditions": []
  }
]
```

---

### POST /policies/schedule

Create or update a schedule (time-window) policy for an agent.

**Role required:** `project_admin`

**Request body:**

```json
{
  "agent_id": "credit-scoring-agent",
  "tenant_id": "123456789012",
  "active_windows": [
    {"cron": "0 9-17 * * MON-FRI", "timezone": "America/New_York"}
  ],
  "blackout_windows": [
    {"cron": "0 0-6 * * *", "timezone": "America/New_York"}
  ],
  "out_of_window_action": "reject",
  "fallback_agent_id": null
}
```

**Response:** `200 OK`

```json
{"status": "ok"}
```

---

### GET /policies/schedule/{agent_id}

Get the schedule policy for an agent.

**Response:** `200 OK` — Full `SchedulePolicy` object, or `null` if none set.

```json
{
  "agent_id": "credit-scoring-agent",
  "tenant_id": "123456789012",
  "active_windows": [{"cron": "0 9-17 * * MON-FRI", "timezone": "America/New_York"}],
  "blackout_windows": [{"cron": "0 0-6 * * *", "timezone": "America/New_York"}],
  "out_of_window_action": "reject",
  "fallback_agent_id": null,
  "updated_at": "2025-01-15T16:30:00Z"
}
```

---

### POST /policies/evaluate

Evaluate whether a communication between two agents is allowed right now, considering communication ACL, capability boundaries, and schedule windows.

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `from_agent` | string | yes | Calling agent ID |
| `to_agent` | string | yes | Target agent ID |
| `resource_type` | string | no | Resource type (e.g. `tool`, `mcp_server`, `api`) |
| `resource_name` | string | no | Specific resource name to check |

**Example:** `POST /api/v1/policies/evaluate?from_agent=credit-scoring-agent&to_agent=risk-assessment-agent`

**Response:** `200 OK`

```json
{
  "allowed": true,
  "reason": "Communication allowed by rule rule-001"
}
```

**Denied example:**

```json
{
  "allowed": false,
  "reason": "Agent credit-scoring-agent is outside active schedule window"
}
```

---

## Reviews

### GET /reviews/pending

List agents awaiting review (in `submitted` or `in_review` lifecycle state).

**Role required:** `project_admin`

**Response:** `200 OK`

```json
{
  "items": [
    {
      "agent_id": "credit-scoring-agent",
      "name": "Credit Scoring Agent",
      "lifecycle_status": "submitted",
      "owner": {"owner_id": "alice@megabank.com", "team": "risk", "org_id": "megabank"},
      "capabilities": ["credit-scoring", "risk-assessment"],
      "...": "..."
    }
  ]
}
```

---

### POST /reviews/{agent_id}

Submit a review decision for an agent.

**Role required:** `project_admin`

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | yes | `approve` or `reject` |
| `reason` | string | no | Reason for the decision |

**Example:** `POST /api/v1/reviews/credit-scoring-agent?action=approve&reason=Meets+compliance+requirements`

**Response:** `200 OK`

```json
{
  "agent_id": "credit-scoring-agent",
  "action": "approve"
}
```

**Errors:**

| Status | Detail |
|--------|--------|
| 400 | `Invalid action: hold` |
| 400 | `Cannot transition from draft to approved` |

---

## Health Check

### GET /health

Service-level health check. No authentication required. Note: this endpoint is at `/health`, not under `/api/v1`.

**Response:** `200 OK`

```json
{
  "status": "ok",
  "service": "harbor"
}
```

---

## Common Error Responses

| Status | Meaning | Example |
|--------|---------|---------|
| 400 | Bad request / invalid transition | `{"detail": "Cannot transition from draft to published"}` |
| 401 | Missing or invalid auth token | `{"detail": "Not authenticated"}` |
| 403 | Insufficient role | `{"detail": "Role project_admin required"}` |
| 404 | Agent not found | `{"detail": "Agent credit-scoring-agent not found"}` |
| 409 | Duplicate agent | `{"detail": "Agent credit-scoring-agent already exists"}` |
| 422 | Validation error | `{"detail": [{"loc": ["body", "agent_id"], "msg": "Field required"}]}` |

---

## Data Types Reference

### AgentLifecycle

`draft` | `submitted` | `in_review` | `approved` | `published` | `suspended` | `deprecated` | `retired`

### Visibility

`private` | `ou_shared` | `org_wide`

### HealthState

`healthy` | `unhealthy` | `unknown`

### OutOfWindowAction

`queue` | `reject` | `fallback_agent`

### PolicyMode

`allowlist` | `denylist`

# Harbor — Python Backend Coding Standards

All Python code in `src/harbor/` and `tests/` MUST follow these standards.

---

## Language & Runtime

- Python 3.12+ required.
- Use type hints on ALL function signatures (parameters and return types).
- Use `from __future__ import annotations` is NOT needed (3.12+ native).

## Dependencies

- **Pydantic v2** for all data models. Use `BaseModel`, not dataclasses.
- **FastAPI** for API routes. Use dependency injection for services.
- **structlog** for logging. Never use `print()` or `logging.getLogger()`.
- **boto3** ONLY in `src/harbor/store/`. Nowhere else.
- **httpx** for outbound HTTP calls (A2A sync). Never use `requests`.

## Code Style

- Formatter: `ruff format` (line length 100).
- Linter: `ruff check` with default rules.
- Type checker: `mypy --strict`.
- All public functions and classes MUST have docstrings.
- Private functions (prefixed `_`) docstrings optional.

## Module Rules

### models/
- Pure Pydantic models. No business logic. No I/O.
- Each model file exports via `__init__.py`.
- Use `Field(default_factory=...)` for mutable defaults.
- Enum values MUST be lowercase strings.

### store/
- ONLY layer that imports boto3.
- Each store class takes `table_name` and `region` as constructor args.
- Use lazy initialization for DynamoDB resources (property pattern).
- All DynamoDB items MUST include `pk` and `sk` fields.
- Return Pydantic models from public methods, not raw dicts.
- Handle `ClientError` gracefully — log and return None or raise domain exception.

### registry/, discovery/, health/, audit/, sync/
- Service classes. Take a store instance via constructor injection.
- No direct boto3 usage. Use store methods only.
- Raise domain-specific exceptions (not HTTP exceptions).
- Keep methods focused — one responsibility per method.

### api/
- FastAPI router definitions.
- Convert domain exceptions to HTTP responses here.
- Use Pydantic models for request/response schemas.
- No business logic in route handlers — delegate to services.
- Use `Depends()` for service injection.

### main.py
- Wiring only. Create store, services, app. No logic.
- Export `app` for uvicorn and `handler` for Mangum/Lambda.

## Error Handling

- Define domain exceptions in `src/harbor/exceptions.py`.
- Examples: `AgentNotFoundError`, `DuplicateAgentError`, `ValidationError`.
- API layer catches domain exceptions and maps to HTTP status codes.
- Store layer catches `ClientError` and raises domain exceptions.
- NEVER catch bare `Exception` unless re-raising.

## Testing

- Use `pytest` with `pytest-asyncio`.
- Use `moto` to mock DynamoDB in unit tests.
- Test file naming: `tests/unit/test_<module_name>.py`.
- Each test function tests ONE behavior.
- Use fixtures for store/service setup.
- No tests call real AWS services (unit tests are offline).
- Integration tests (in `tests/integration/`) MAY call real AWS.

## Logging

- Use `structlog.get_logger(__name__)` at module level.
- Log key events: agent_registered, agent_updated, agent_deleted, discovery_resolved.
- Include `agent_id` in all agent-related log entries.
- Use structured key-value pairs, not string formatting.

```python
# Good
logger.info("agent_registered", agent_id=record.agent_id, capabilities=record.capabilities)

# Bad
logger.info(f"Registered agent {record.agent_id}")
```

## Imports

- Standard library first, then third-party, then local.
- Use absolute imports from `harbor.*` (not relative).
- No wildcard imports (`from x import *`).

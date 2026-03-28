"""Harbor API — REST endpoints for agent registry, discovery, and governance."""

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request

from harbor.audit.service import AuditService
from harbor.auth.service import AuthContext, get_auth_context, require_role
from harbor.discovery.service import DiscoveryService
from harbor.exceptions import (
    AgentNotFoundError,
    DuplicateAgentError,
    InvalidLifecycleTransitionError,
)
from harbor.health.service import HealthService
from harbor.models.agent import AgentLifecycle, AgentRecord, AgentVersion, AuditEntry, HealthStatus
from harbor.models.policy import CapabilityPolicy, CommunicationRule, SchedulePolicy
from harbor.policy.service import PolicyService
from harbor.registry.service import RegistryService
from harbor.store.dynamo import AgentStore


def create_app(store: AgentStore | None = None) -> FastAPI:
    """Create and wire the FastAPI application."""
    app = FastAPI(title="Harbor", description="Agent Platform Management", version="0.2.0")
    _store = store or AgentStore()
    registry = RegistryService(_store)
    discovery = DiscoveryService(_store)
    health_svc = HealthService(_store)
    audit_svc = AuditService(_store)
    policy_svc = PolicyService(_store)

    def _auth(request: Request) -> AuthContext:
        return get_auth_context(request)

    # ── Registry CRUD ─────────────────────────────────────

    @app.post("/api/v1/agents", response_model=AgentRecord)
    def register_agent(record: AgentRecord, ctx: AuthContext = Depends(_auth)) -> AgentRecord:
        require_role(ctx, "developer")
        try:
            return registry.register(record)
        except DuplicateAgentError as e:
            raise HTTPException(409, str(e))

    @app.get("/api/v1/agents")
    def list_agents(
        lifecycle: AgentLifecycle | None = None,
        limit: int = 50,
        cursor: str | None = None,
        ctx: AuthContext = Depends(_auth),
    ) -> dict[str, Any]:
        records, next_cursor = registry.list_agents(ctx.tenant_id, lifecycle, limit, cursor)
        return {"items": [r.model_dump(mode="json") for r in records], "cursor": next_cursor}

    @app.get("/api/v1/agents/{agent_id}", response_model=AgentRecord)
    def get_agent(agent_id: str, ctx: AuthContext = Depends(_auth)) -> AgentRecord:
        try:
            return registry.get(ctx.tenant_id, agent_id)
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")

    @app.patch("/api/v1/agents/{agent_id}", response_model=AgentRecord)
    def update_agent(
        agent_id: str, updates: dict[str, Any], ctx: AuthContext = Depends(_auth)
    ) -> AgentRecord:
        require_role(ctx, "developer")
        try:
            return registry.update_config(ctx.tenant_id, agent_id, updates)
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")

    @app.delete("/api/v1/agents/{agent_id}")
    def delete_agent(agent_id: str, ctx: AuthContext = Depends(_auth)) -> dict[str, str]:
        require_role(ctx, "project_admin")
        try:
            registry.deregister(ctx.tenant_id, agent_id, actor=ctx.user_id)
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")
        return {"deleted": agent_id}

    # ── Lifecycle ─────────────────────────────────────────

    @app.put("/api/v1/agents/{agent_id}/lifecycle", response_model=AgentRecord)
    def transition_lifecycle(
        agent_id: str,
        target: AgentLifecycle,
        reason: str = "",
        ctx: AuthContext = Depends(_auth),
    ) -> AgentRecord:
        require_role(ctx, "project_admin")
        try:
            return registry.transition(
                ctx.tenant_id, agent_id, target, actor=ctx.user_id, reason=reason
            )
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")
        except InvalidLifecycleTransitionError as e:
            raise HTTPException(400, str(e))

    # ── Versions ──────────────────────────────────────────

    @app.post("/api/v1/agents/{agent_id}/versions", response_model=AgentVersion)
    def create_version(agent_id: str, ctx: AuthContext = Depends(_auth)) -> AgentVersion:
        require_role(ctx, "developer")
        try:
            return registry.create_version(ctx.tenant_id, agent_id, actor=ctx.user_id)
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")

    @app.get("/api/v1/agents/{agent_id}/versions", response_model=list[AgentVersion])
    def list_versions(agent_id: str, ctx: AuthContext = Depends(_auth)) -> list[AgentVersion]:
        return registry.list_versions(ctx.tenant_id, agent_id)

    # ── Health ────────────────────────────────────────────

    @app.put("/api/v1/agents/{agent_id}/health", response_model=HealthStatus)
    def heartbeat(agent_id: str, ctx: AuthContext = Depends(_auth)) -> HealthStatus:
        return health_svc.heartbeat(ctx.tenant_id, agent_id)

    @app.get("/api/v1/health/summary")
    def health_summary(ctx: AuthContext = Depends(_auth)) -> dict[str, int]:
        return health_svc.summary(ctx.tenant_id)

    # ── Audit ─────────────────────────────────────────────

    @app.get("/api/v1/agents/{agent_id}/audit", response_model=list[AuditEntry])
    def agent_audit(
        agent_id: str, limit: int = 50, ctx: AuthContext = Depends(_auth)
    ) -> list[AuditEntry]:
        return audit_svc.get_agent_audit(ctx.tenant_id, agent_id, limit)

    @app.get("/api/v1/audit", response_model=list[AuditEntry])
    def tenant_audit(limit: int = 100, ctx: AuthContext = Depends(_auth)) -> list[AuditEntry]:
        return audit_svc.get_tenant_audit(ctx.tenant_id, limit)

    # ── Discovery ─────────────────────────────────────────

    @app.get("/api/v1/discover/capability/{capability}", response_model=list[AgentRecord])
    def discover_by_capability(
        capability: str, ctx: AuthContext = Depends(_auth)
    ) -> list[AgentRecord]:
        return discovery.by_capability(ctx.tenant_id, capability)

    @app.get("/api/v1/discover/phase/{phase}", response_model=list[AgentRecord])
    def discover_by_phase(phase: str, ctx: AuthContext = Depends(_auth)) -> list[AgentRecord]:
        return discovery.by_phase(ctx.tenant_id, phase)

    @app.get("/api/v1/discover/resolve", response_model=AgentRecord | None)
    def resolve_agent(
        capability: str | None = None,
        phase: str | None = None,
        ctx: AuthContext = Depends(_auth),
    ) -> AgentRecord | None:
        return discovery.resolve(ctx.tenant_id, capability=capability, phase=phase)

    # ── Policy CRUD ───────────────────────────────────────

    @app.post("/api/v1/policies/capability")
    def put_capability_policy(
        policy: CapabilityPolicy, ctx: AuthContext = Depends(_auth)
    ) -> dict[str, str]:
        require_role(ctx, "project_admin")
        _store.put_capability_policy(policy)
        return {"status": "ok"}

    @app.get("/api/v1/policies/capability/{agent_id}", response_model=CapabilityPolicy | None)
    def get_capability_policy(
        agent_id: str, ctx: AuthContext = Depends(_auth)
    ) -> CapabilityPolicy | None:
        return _store.get_capability_policy(ctx.tenant_id, agent_id)

    @app.post("/api/v1/policies/communication")
    def put_communication_rule(
        rule: CommunicationRule, ctx: AuthContext = Depends(_auth)
    ) -> dict[str, str]:
        require_role(ctx, "project_admin")
        _store.put_communication_rule(rule)
        return {"status": "ok"}

    @app.get("/api/v1/policies/communication", response_model=list[CommunicationRule])
    def list_communication_rules(
        ctx: AuthContext = Depends(_auth),
    ) -> list[CommunicationRule]:
        return _store.list_communication_rules()

    @app.post("/api/v1/policies/schedule")
    def put_schedule_policy(
        policy: SchedulePolicy, ctx: AuthContext = Depends(_auth)
    ) -> dict[str, str]:
        require_role(ctx, "project_admin")
        _store.put_schedule_policy(policy)
        return {"status": "ok"}

    @app.get("/api/v1/policies/schedule/{agent_id}", response_model=SchedulePolicy | None)
    def get_schedule_policy(
        agent_id: str, ctx: AuthContext = Depends(_auth)
    ) -> SchedulePolicy | None:
        return _store.get_schedule_policy(agent_id)

    @app.post("/api/v1/policies/evaluate")
    def evaluate_policy(
        from_agent: str,
        to_agent: str,
        resource_type: str | None = None,
        resource_name: str | None = None,
        ctx: AuthContext = Depends(_auth),
    ) -> dict[str, Any]:
        decision = policy_svc.evaluate(
            ctx.tenant_id, from_agent, to_agent, resource_type, resource_name
        )
        return {"allowed": decision.allowed, "reason": decision.reason}

    # ── Reviews ───────────────────────────────────────────

    @app.get("/api/v1/reviews/pending")
    def list_pending_reviews(ctx: AuthContext = Depends(_auth)) -> dict[str, Any]:
        require_role(ctx, "project_admin")
        submitted, _ = _store.list_by_lifecycle(AgentLifecycle.SUBMITTED, limit=100)
        in_review, _ = _store.list_by_lifecycle(AgentLifecycle.IN_REVIEW, limit=100)
        return {"items": [r.model_dump(mode="json") for r in submitted + in_review]}

    @app.post("/api/v1/reviews/{agent_id}")
    def submit_review(
        agent_id: str, action: str, reason: str = "", ctx: AuthContext = Depends(_auth)
    ) -> dict[str, str]:
        require_role(ctx, "project_admin")
        try:
            if action == "approve":
                registry.approve(ctx.tenant_id, agent_id, actor=ctx.user_id, reason=reason)
            elif action == "reject":
                registry.reject(ctx.tenant_id, agent_id, actor=ctx.user_id, reason=reason)
            else:
                raise HTTPException(400, f"Invalid action: {action}")
        except (AgentNotFoundError, InvalidLifecycleTransitionError) as e:
            raise HTTPException(400, str(e))
        return {"agent_id": agent_id, "action": action}

    # ── Health check ──────────────────────────────────────

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "harbor"}

    return app

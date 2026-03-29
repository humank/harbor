"""Policy CRUD and evaluation endpoints."""

from fastapi import APIRouter, Depends, Request

from harbor.api.deps import AuthContext, Services, get_auth_context, require_role
from harbor.models.policy import (
    CapabilityPolicy,
    CommunicationRule,
    PolicyDecision,
    SchedulePolicy,
)


def create_router(svc: Services) -> APIRouter:
    """Create policy router with injected services."""
    router = APIRouter(prefix="/api/v1", tags=["policies"])

    def _auth(request: Request) -> AuthContext:
        return get_auth_context(request)

    @router.post("/policies/capability")
    def put_capability_policy(
        policy: CapabilityPolicy, ctx: AuthContext = Depends(_auth),
    ) -> dict[str, str]:
        require_role(ctx, "project_admin")
        svc.policy.put_capability_policy(policy, actor=ctx.user_id)
        return {"status": "ok"}

    @router.get("/policies/capability/{agent_id}", response_model=CapabilityPolicy | None)
    def get_capability_policy(
        agent_id: str, ctx: AuthContext = Depends(_auth),
    ) -> CapabilityPolicy | None:
        return svc.policy.get_capability_policy(ctx.tenant_id, agent_id)

    @router.post("/policies/communication")
    def put_communication_rule(
        rule: CommunicationRule, ctx: AuthContext = Depends(_auth),
    ) -> dict[str, str]:
        require_role(ctx, "project_admin")
        svc.policy.put_communication_rule(rule, actor=ctx.user_id)
        return {"status": "ok"}

    @router.get("/policies/communication", response_model=list[CommunicationRule])
    def list_communication_rules(ctx: AuthContext = Depends(_auth)) -> list[CommunicationRule]:
        return svc.policy.list_communication_rules()

    @router.post("/policies/schedule")
    def put_schedule_policy(
        policy: SchedulePolicy, ctx: AuthContext = Depends(_auth),
    ) -> dict[str, str]:
        require_role(ctx, "project_admin")
        svc.policy.put_schedule_policy(policy, actor=ctx.user_id)
        return {"status": "ok"}

    @router.get("/policies/schedule/{agent_id}", response_model=SchedulePolicy | None)
    def get_schedule_policy(
        agent_id: str, ctx: AuthContext = Depends(_auth),
    ) -> SchedulePolicy | None:
        return svc.policy.get_schedule_policy(agent_id)

    @router.post("/policies/evaluate", response_model=PolicyDecision)
    def evaluate_policy(
        from_agent: str, to_agent: str,
        resource_type: str | None = None, resource_name: str | None = None,
        ctx: AuthContext = Depends(_auth),
    ) -> PolicyDecision:
        return svc.policy.evaluate(
            ctx.tenant_id, from_agent, to_agent, resource_type, resource_name,
        )

    return router

"""Discovery endpoints."""

from fastapi import APIRouter, Depends, Request

from harbor.api.deps import AuthContext, Services, get_auth_context
from harbor.models.agent import AgentRecord


def create_router(svc: Services) -> APIRouter:
    """Create discovery router with injected services."""
    router = APIRouter(prefix="/api/v1", tags=["discovery"])

    def _auth(request: Request) -> AuthContext:
        return get_auth_context(request)

    @router.get("/discover/capability/{capability}", response_model=list[AgentRecord])
    def discover_by_capability(
        capability: str, ctx: AuthContext = Depends(_auth),
    ) -> list[AgentRecord]:
        return svc.discovery.by_capability(ctx.tenant_id, capability)

    @router.get("/discover/phase/{phase}", response_model=list[AgentRecord])
    def discover_by_phase(phase: str, ctx: AuthContext = Depends(_auth)) -> list[AgentRecord]:
        return svc.discovery.by_phase(ctx.tenant_id, phase)

    @router.get("/discover/resolve", response_model=AgentRecord | None)
    def resolve_agent(
        capability: str | None = None, phase: str | None = None,
        ctx: AuthContext = Depends(_auth),
    ) -> AgentRecord | None:
        return svc.discovery.resolve(ctx.tenant_id, capability=capability, phase=phase)

    return router

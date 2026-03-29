"""Health endpoints — heartbeat and summary."""

from fastapi import APIRouter, Depends, Request

from harbor.api.deps import AuthContext, Services, get_auth_context
from harbor.models.agent import HealthStatus


def create_router(svc: Services) -> APIRouter:
    """Create health router with injected services."""
    router = APIRouter(prefix="/api/v1", tags=["health"])

    def _auth(request: Request) -> AuthContext:
        return get_auth_context(request)

    @router.put("/agents/{agent_id}/health", response_model=HealthStatus)
    def heartbeat(agent_id: str, ctx: AuthContext = Depends(_auth)) -> HealthStatus:
        return svc.health.heartbeat(ctx.tenant_id, agent_id)

    @router.get("/health/summary")
    def health_summary(ctx: AuthContext = Depends(_auth)) -> dict[str, int]:
        return svc.health.summary(ctx.tenant_id)

    return router

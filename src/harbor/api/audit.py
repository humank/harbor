"""Audit log endpoints."""

from fastapi import APIRouter, Depends, Request

from harbor.api.deps import AuthContext, Services, get_auth_context
from harbor.models.agent import AuditEntry


def create_router(svc: Services) -> APIRouter:
    """Create audit router with injected services."""
    router = APIRouter(prefix="/api/v1", tags=["audit"])

    def _auth(request: Request) -> AuthContext:
        return get_auth_context(request)

    @router.get("/agents/{agent_id}/audit", response_model=list[AuditEntry])
    def agent_audit(
        agent_id: str, limit: int = 50, ctx: AuthContext = Depends(_auth),
    ) -> list[AuditEntry]:
        return svc.audit.get_agent_audit(ctx.tenant_id, agent_id, limit)

    @router.get("/audit", response_model=list[AuditEntry])
    def tenant_audit(limit: int = 100, ctx: AuthContext = Depends(_auth)) -> list[AuditEntry]:
        return svc.audit.get_tenant_audit(ctx.tenant_id, limit)

    return router

"""Review queue endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from harbor.api.deps import AuthContext, Services, get_auth_context, require_role
from harbor.exceptions import AgentNotFoundError, InvalidLifecycleTransitionError
from harbor.models.agent import AgentLifecycle


def create_router(svc: Services) -> APIRouter:
    """Create reviews router with injected services."""
    router = APIRouter(prefix="/api/v1", tags=["reviews"])

    def _auth(request: Request) -> AuthContext:
        return get_auth_context(request)

    @router.get("/reviews/pending")
    def list_pending_reviews(ctx: AuthContext = Depends(_auth)) -> dict[str, Any]:
        require_role(ctx, "project_admin")
        submitted, _ = svc.registry.list_agents(ctx.tenant_id, AgentLifecycle.SUBMITTED, limit=100)
        in_review, _ = svc.registry.list_agents(ctx.tenant_id, AgentLifecycle.IN_REVIEW, limit=100)
        return {"items": [r.model_dump(mode="json") for r in submitted + in_review]}

    @router.post("/reviews/{agent_id}")
    def submit_review(
        agent_id: str, action: str, reason: str = "", ctx: AuthContext = Depends(_auth),
    ) -> dict[str, str]:
        require_role(ctx, "project_admin")
        try:
            if action == "approve":
                svc.registry.approve(ctx.tenant_id, agent_id, actor=ctx.user_id, reason=reason)
            elif action == "reject":
                svc.registry.reject(ctx.tenant_id, agent_id, actor=ctx.user_id, reason=reason)
            else:
                raise HTTPException(400, f"Invalid action: {action}")
        except (AgentNotFoundError, InvalidLifecycleTransitionError) as e:
            raise HTTPException(400, str(e))
        return {"agent_id": agent_id, "action": action}

    return router

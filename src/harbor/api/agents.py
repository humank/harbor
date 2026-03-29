"""Agent CRUD, lifecycle, and version endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from harbor.api.deps import AuthContext, Services, get_auth_context, require_role
from harbor.exceptions import (
    AgentNotFoundError,
    DuplicateAgentError,
    InvalidLifecycleTransitionError,
)
from harbor.models.agent import AgentLifecycle, AgentRecord, AgentVersion


def create_router(svc: Services) -> APIRouter:
    """Create agent router with injected services."""
    router = APIRouter(prefix="/api/v1", tags=["agents"])

    def _auth(request: Request) -> AuthContext:
        return get_auth_context(request)

    @router.post("/agents", response_model=AgentRecord)
    def register_agent(record: AgentRecord, ctx: AuthContext = Depends(_auth)) -> AgentRecord:
        require_role(ctx, "developer")
        try:
            return svc.registry.register(record)
        except DuplicateAgentError as e:
            raise HTTPException(409, str(e))

    @router.get("/agents")
    def list_agents(
        lifecycle: AgentLifecycle | None = None, limit: int = 50,
        cursor: str | None = None, ctx: AuthContext = Depends(_auth),
    ) -> dict[str, Any]:
        records, next_cursor = svc.registry.list_agents(ctx.tenant_id, lifecycle, limit, cursor)
        return {"items": [r.model_dump(mode="json") for r in records], "cursor": next_cursor}

    @router.get("/agents/{agent_id}", response_model=AgentRecord)
    def get_agent(agent_id: str, ctx: AuthContext = Depends(_auth)) -> AgentRecord:
        try:
            return svc.registry.get(ctx.tenant_id, agent_id)
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")

    @router.patch("/agents/{agent_id}", response_model=AgentRecord)
    def update_agent(
        agent_id: str, updates: dict[str, Any], ctx: AuthContext = Depends(_auth),
    ) -> AgentRecord:
        require_role(ctx, "developer")
        try:
            return svc.registry.update_config(ctx.tenant_id, agent_id, updates)
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")

    @router.delete("/agents/{agent_id}")
    def delete_agent(agent_id: str, ctx: AuthContext = Depends(_auth)) -> dict[str, str]:
        require_role(ctx, "project_admin")
        try:
            svc.registry.deregister(ctx.tenant_id, agent_id, actor=ctx.user_id)
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")
        return {"deleted": agent_id}

    @router.put("/agents/{agent_id}/lifecycle", response_model=AgentRecord)
    def transition_lifecycle(
        agent_id: str, target: AgentLifecycle, reason: str = "",
        ctx: AuthContext = Depends(_auth),
    ) -> AgentRecord:
        require_role(ctx, "project_admin")
        try:
            return svc.registry.transition(
                ctx.tenant_id, agent_id, target, actor=ctx.user_id, reason=reason,
            )
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")
        except InvalidLifecycleTransitionError as e:
            raise HTTPException(400, str(e))

    @router.post("/agents/{agent_id}/versions", response_model=AgentVersion)
    def create_version(agent_id: str, ctx: AuthContext = Depends(_auth)) -> AgentVersion:
        require_role(ctx, "developer")
        try:
            return svc.registry.create_version(ctx.tenant_id, agent_id, actor=ctx.user_id)
        except AgentNotFoundError:
            raise HTTPException(404, f"Agent {agent_id} not found")

    @router.get("/agents/{agent_id}/versions", response_model=list[AgentVersion])
    def list_versions(agent_id: str, ctx: AuthContext = Depends(_auth)) -> list[AgentVersion]:
        return svc.registry.list_versions(ctx.tenant_id, agent_id)

    return router

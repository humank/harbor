"""Harbor API — REST endpoints for agent registry and discovery."""

from fastapi import FastAPI, HTTPException

from harbor.discovery.service import DiscoveryService
from harbor.models.agent import AgentRecord, AgentStatus
from harbor.registry.service import RegistryService
from harbor.store.dynamo import AgentStore


def create_app(store: AgentStore | None = None) -> FastAPI:
    app = FastAPI(title="Harbor", description="Agent Platform Management", version="0.1.0")
    _store = store or AgentStore()
    registry = RegistryService(_store)
    discovery = DiscoveryService(_store)

    # ── Registry CRUD ─────────────────────────────────────

    @app.post("/agents", response_model=AgentRecord)
    def register_agent(record: AgentRecord):
        return registry.register(record)

    @app.get("/agents", response_model=list[AgentRecord])
    def list_agents(status: AgentStatus | None = None):
        return registry.list_agents(status)

    @app.get("/agents/{agent_id}", response_model=AgentRecord)
    def get_agent(agent_id: str):
        r = registry.get(agent_id)
        if not r:
            raise HTTPException(404, f"Agent {agent_id} not found")
        return r

    @app.patch("/agents/{agent_id}", response_model=AgentRecord)
    def update_agent(agent_id: str, updates: dict):
        r = registry.update_config(agent_id, updates)
        if not r:
            raise HTTPException(404, f"Agent {agent_id} not found")
        return r

    @app.delete("/agents/{agent_id}")
    def delete_agent(agent_id: str):
        if not registry.deregister(agent_id):
            raise HTTPException(404, f"Agent {agent_id} not found")
        return {"deleted": agent_id}

    @app.put("/agents/{agent_id}/status")
    def set_agent_status(agent_id: str, status: AgentStatus):
        r = registry.set_status(agent_id, status)
        if not r:
            raise HTTPException(404, f"Agent {agent_id} not found")
        return {"agent_id": agent_id, "status": status.value}

    # ── Discovery ─────────────────────────────────────────

    @app.get("/discover/capability/{capability}", response_model=list[AgentRecord])
    def discover_by_capability(capability: str):
        return discovery.by_capability(capability)

    @app.get("/discover/phase/{phase}", response_model=list[AgentRecord])
    def discover_by_phase(phase: str):
        return discovery.by_phase(phase)

    @app.get("/discover/resolve", response_model=AgentRecord | None)
    def resolve_agent(capability: str | None = None, phase: str | None = None):
        return discovery.resolve(capability=capability, phase=phase)

    # ── Health ────────────────────────────────────────────

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "harbor"}

    return app

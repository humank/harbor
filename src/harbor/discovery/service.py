"""Discovery service — tenant-aware agent lookup."""

import structlog

from harbor.models.agent import AgentRecord
from harbor.store.agent_store import AgentStore

logger = structlog.get_logger(__name__)


class DiscoveryService:
    """Find agents by capability, phase, or skill — scoped by tenant."""

    def __init__(self, store: AgentStore) -> None:
        self.store = store

    def by_capability(self, tenant_id: str, capability: str) -> list[AgentRecord]:
        """Find published agents by capability within a tenant."""
        return self.store.find_by_capability(tenant_id, capability)

    def by_phase(self, tenant_id: str, phase: str) -> list[AgentRecord]:
        """Find published agents by phase within a tenant."""
        return self.store.find_by_phase(tenant_id, phase)

    def resolve(
        self, tenant_id: str, *, capability: str | None = None, phase: str | None = None,
    ) -> AgentRecord | None:
        """Resolve the best published agent for a capability or phase."""
        candidates: list[AgentRecord] = []
        if capability:
            candidates = self.by_capability(tenant_id, capability)
        elif phase:
            candidates = self.by_phase(tenant_id, phase)
        return candidates[0] if candidates else None

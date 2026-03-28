"""Discovery service — find agents by capability, phase, or skill."""

import structlog

from harbor.models.agent import AgentRecord
from harbor.store.dynamo import AgentStore

logger = structlog.get_logger(__name__)


class DiscoveryService:
    def __init__(self, store: AgentStore | None = None):
        self.store = store or AgentStore()

    def by_capability(self, capability: str) -> list[AgentRecord]:
        return self.store.find_by_capability(capability)

    def by_phase(self, phase: str) -> list[AgentRecord]:
        return self.store.find_by_phase(phase)

    def by_skill(self, skill_id: str) -> list[AgentRecord]:
        """Search across all active agents for a matching skill."""
        all_agents = self.store.list_all()
        return [a for a in all_agents if any(s.id == skill_id for s in a.skills)]

    def resolve(self, *, capability: str | None = None, phase: str | None = None) -> AgentRecord | None:
        """Resolve the best agent for a given capability or phase."""
        candidates: list[AgentRecord] = []
        if capability:
            candidates = self.by_capability(capability)
        elif phase:
            candidates = self.by_phase(phase)
        if not candidates:
            return None
        return candidates[0]  # already sorted by priority

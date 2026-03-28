"""Registry service — agent lifecycle management."""

import structlog

from harbor.models.agent import AgentRecord, AgentStatus
from harbor.store.dynamo import AgentStore

logger = structlog.get_logger(__name__)


class RegistryService:
    def __init__(self, store: AgentStore | None = None):
        self.store = store or AgentStore()

    def register(self, record: AgentRecord) -> AgentRecord:
        existing = self.store.get(record.agent_id)
        if existing:
            logger.info("agent_updated", agent_id=record.agent_id)
        else:
            logger.info("agent_registered", agent_id=record.agent_id)
        self.store.put(record)
        return record

    def deregister(self, agent_id: str) -> bool:
        return self.store.delete(agent_id)

    def get(self, agent_id: str) -> AgentRecord | None:
        return self.store.get(agent_id)

    def update_config(self, agent_id: str, updates: dict) -> AgentRecord | None:
        return self.store.update(agent_id, updates)

    def set_status(self, agent_id: str, status: AgentStatus) -> AgentRecord | None:
        return self.store.update(agent_id, {"status": status})

    def list_agents(self, status: AgentStatus | None = None) -> list[AgentRecord]:
        return self.store.list_all(status)

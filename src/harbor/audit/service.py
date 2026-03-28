"""Audit log service."""

import structlog

from harbor.models.agent import AuditEntry
from harbor.store.dynamo import AgentStore

logger = structlog.get_logger(__name__)


class AuditService:
    """Query audit logs."""

    def __init__(self, store: AgentStore) -> None:
        self.store = store

    def get_agent_audit(self, tenant_id: str, agent_id: str, limit: int = 50) -> list[AuditEntry]:
        """Get audit trail for a specific agent."""
        return self.store.list_audit(tenant_id, agent_id, limit)

    def get_tenant_audit(self, tenant_id: str, limit: int = 100) -> list[AuditEntry]:
        """Get recent audit entries across all agents in a tenant."""
        agents, _ = self.store.list_by_tenant(tenant_id, limit=500)
        all_entries: list[AuditEntry] = []
        for agent in agents:
            entries = self.store.list_audit(tenant_id, agent.agent_id, limit=10)
            all_entries.extend(entries)
        all_entries.sort(key=lambda e: e.timestamp, reverse=True)
        return all_entries[:limit]

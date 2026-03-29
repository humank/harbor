"""Audit log service."""

import structlog

from harbor.models.agent import AuditEntry
from harbor.store.audit_store import AuditStore

logger = structlog.get_logger(__name__)


class AuditService:
    """Query audit logs."""

    def __init__(self, audit_store: AuditStore) -> None:
        self.audit_store = audit_store

    def get_agent_audit(self, tenant_id: str, agent_id: str, limit: int = 50) -> list[AuditEntry]:
        """Get audit trail for a specific agent."""
        return self.audit_store.list_audit(tenant_id, agent_id, limit)

    def get_tenant_audit(self, tenant_id: str, limit: int = 100) -> list[AuditEntry]:
        """Get recent audit entries across all agents in a tenant."""
        return self.audit_store.list_by_tenant(tenant_id, limit)

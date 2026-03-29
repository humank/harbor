"""Audit store — immutable audit log entries."""

from harbor.models.agent import AuditEntry
from harbor.store.base import BaseStore


class AuditStore(BaseStore):
    """Append and query audit log entries."""

    def put_audit(self, entry: AuditEntry) -> None:
        """Append an audit log entry."""
        self.table.put_item(
            Item={
                "pk": self._agent_pk(entry.tenant_id, entry.agent_id),
                "sk": f"AUDIT#{entry.timestamp.isoformat()}",
                **entry.model_dump(mode="json"),
            }
        )

    def list_audit(self, tenant_id: str, agent_id: str, limit: int = 50) -> list[AuditEntry]:
        """List audit entries for an agent (newest first)."""
        resp = self.table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={
                ":pk": self._agent_pk(tenant_id, agent_id),
                ":prefix": "AUDIT#",
            },
            ScanIndexForward=False,
            Limit=limit,
        )
        return [AuditEntry(**item) for item in resp.get("Items", [])]

    def list_by_tenant(self, tenant_id: str, limit: int = 100) -> list[AuditEntry]:
        """List recent audit entries across all agents in a tenant (single query)."""
        resp = self.table.query(
            IndexName="tenant-index",
            KeyConditionExpression="tenant_id = :tid",
            FilterExpression="begins_with(sk, :prefix)",
            ExpressionAttributeValues={":tid": tenant_id, ":prefix": "AUDIT#"},
            ScanIndexForward=False,
            Limit=limit,
        )
        return [AuditEntry(**item) for item in resp.get("Items", [])]

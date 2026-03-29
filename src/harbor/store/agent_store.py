"""Agent store — CRUD, listing, capability/phase indexes."""

from datetime import datetime, timezone
from typing import Any

import structlog
from botocore.exceptions import ClientError

from harbor.models.agent import AgentLifecycle, AgentRecord
from harbor.store.base import BaseStore

logger = structlog.get_logger(__name__)


class AgentStore(BaseStore):
    """Agent CRUD and discovery indexes."""

    # ── CRUD ──────────────────────────────────────────────

    def put_agent(self, record: AgentRecord) -> None:
        """Create or update an agent record."""
        record.updated_at = datetime.now(timezone.utc)
        item = {
            "pk": self._agent_pk(record.tenant_id, record.agent_id),
            "sk": "META",
            "tenant_id": record.tenant_id,
            "lifecycle_status": record.lifecycle_status.value,
            "status": record.lifecycle_status.value,
            "updated_at": record.updated_at.isoformat(),
            **record.model_dump(mode="json"),
        }
        self.table.put_item(Item=item)
        self._write_indexes(record)
        logger.info("agent_stored", agent_id=record.agent_id, tenant_id=record.tenant_id)

    def get_agent(self, tenant_id: str, agent_id: str) -> AgentRecord | None:
        """Get a single agent by tenant + agent ID."""
        resp = self.table.get_item(Key={"pk": self._agent_pk(tenant_id, agent_id), "sk": "META"})
        item = resp.get("Item")
        return AgentRecord(**item) if item else None

    def delete_agent(self, tenant_id: str, agent_id: str) -> bool:
        """Delete an agent and its indexes."""
        existing = self.get_agent(tenant_id, agent_id)
        if not existing:
            return False
        self.table.delete_item(Key={"pk": self._agent_pk(tenant_id, agent_id), "sk": "META"})
        self._delete_indexes(existing)
        logger.info("agent_deleted", agent_id=agent_id, tenant_id=tenant_id)
        return True

    def update_agent(
        self, tenant_id: str, agent_id: str, updates: dict[str, Any]
    ) -> AgentRecord | None:
        """Merge updates into an existing agent."""
        existing = self.get_agent(tenant_id, agent_id)
        if not existing:
            return None
        merged = existing.model_copy(update=updates)
        self.put_agent(merged)
        return merged

    # ── List / Query ──────────────────────────────────────

    def list_by_tenant(
        self,
        tenant_id: str,
        lifecycle: AgentLifecycle | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[AgentRecord], str | None]:
        """List agents for a tenant with optional lifecycle filter."""
        kwargs: dict[str, Any] = {
            "IndexName": "tenant-index",
            "KeyConditionExpression": "tenant_id = :tid",
            "ExpressionAttributeValues": {":tid": tenant_id},
            "Limit": limit,
            "ScanIndexForward": False,
        }
        if lifecycle:
            kwargs["FilterExpression"] = "lifecycle_status = :ls"
            kwargs["ExpressionAttributeValues"][":ls"] = lifecycle.value
        if cursor:
            kwargs["ExclusiveStartKey"] = self.decode_cursor(cursor)

        resp = self.table.query(**kwargs)
        records = [
            AgentRecord(**item) for item in resp.get("Items", []) if item.get("sk") == "META"
        ]
        return records, self.encode_cursor(resp.get("LastEvaluatedKey"))

    def list_by_lifecycle(
        self,
        lifecycle: AgentLifecycle,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[AgentRecord], str | None]:
        """List agents across tenants by lifecycle status."""
        kwargs: dict[str, Any] = {
            "IndexName": "lifecycle-index",
            "KeyConditionExpression": "lifecycle_status = :ls",
            "ExpressionAttributeValues": {":ls": lifecycle.value},
            "Limit": limit,
            "ScanIndexForward": False,
        }
        if cursor:
            kwargs["ExclusiveStartKey"] = self.decode_cursor(cursor)

        resp = self.table.query(**kwargs)
        records = [
            AgentRecord(**item) for item in resp.get("Items", []) if item.get("sk") == "META"
        ]
        return records, self.encode_cursor(resp.get("LastEvaluatedKey"))

    # ── Discovery indexes ─────────────────────────────────

    def find_by_capability(self, tenant_id: str, capability: str) -> list[AgentRecord]:
        """Find published agents by capability."""
        resp = self.table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": self._cap_pk(tenant_id, capability)},
        )
        agent_ids = [item["agent_id"] for item in resp.get("Items", [])]
        return self._resolve_published(tenant_id, agent_ids)

    def find_by_phase(self, tenant_id: str, phase: str) -> list[AgentRecord]:
        """Find published agents by phase."""
        resp = self.table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": self._phase_pk(tenant_id, phase)},
        )
        agent_ids = [item["agent_id"] for item in resp.get("Items", [])]
        return self._resolve_published(tenant_id, agent_ids)

    # ── Internal ──────────────────────────────────────────

    @staticmethod
    def _cap_pk(tenant_id: str, capability: str) -> str:
        return f"TENANT#{tenant_id}#CAP#{capability}"

    @staticmethod
    def _phase_pk(tenant_id: str, phase: str) -> str:
        return f"TENANT#{tenant_id}#PHASE#{phase}"

    def _resolve_published(self, tenant_id: str, agent_ids: list[str]) -> list[AgentRecord]:
        """Resolve agent IDs to published records, sorted by priority."""
        results = []
        for aid in agent_ids:
            r = self.get_agent(tenant_id, aid)
            if r and r.lifecycle_status == AgentLifecycle.PUBLISHED:
                results.append(r)
        return sorted(results, key=lambda r: self._max_priority(r), reverse=True)

    @staticmethod
    def _max_priority(r: AgentRecord) -> int:
        if not r.routing_rules:
            return 0
        return max(rule.priority for rule in r.routing_rules)

    def _write_indexes(self, record: AgentRecord) -> None:
        """Write capability and phase index entries."""
        for cap in record.capabilities:
            self.table.put_item(
                Item={
                    "pk": self._cap_pk(record.tenant_id, cap),
                    "sk": f"AGENT#{record.agent_id}",
                    "agent_id": record.agent_id,
                }
            )
        for phase in record.phase_affinity:
            self.table.put_item(
                Item={
                    "pk": self._phase_pk(record.tenant_id, phase),
                    "sk": f"AGENT#{record.agent_id}",
                    "agent_id": record.agent_id,
                }
            )

    def _delete_indexes(self, record: AgentRecord) -> None:
        """Remove capability and phase index entries."""
        for cap in record.capabilities:
            try:
                self.table.delete_item(
                    Key={
                        "pk": self._cap_pk(record.tenant_id, cap),
                        "sk": f"AGENT#{record.agent_id}",
                    }
                )
            except ClientError:
                pass
        for phase in record.phase_affinity:
            try:
                self.table.delete_item(
                    Key={
                        "pk": self._phase_pk(record.tenant_id, phase),
                        "sk": f"AGENT#{record.agent_id}",
                    }
                )
            except ClientError:
                pass

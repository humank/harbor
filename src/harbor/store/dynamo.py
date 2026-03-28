"""DynamoDB-backed agent store — multi-tenant single-table design.

Table schema:
    PK                                      SK                  Purpose
    TENANT#{tid}#AGENT#{aid}                META                Agent record
    TENANT#{tid}#AGENT#{aid}                VER#{version}       Version snapshot
    TENANT#{tid}#AGENT#{aid}                HEALTH              Health status
    TENANT#{tid}#AGENT#{aid}                AUDIT#{timestamp}   Audit entry
    TENANT#{tid}#CAP#{capability}           AGENT#{aid}         Capability index
    TENANT#{tid}#PHASE#{phase}              AGENT#{aid}         Phase index
    TENANT#{tid}#POLICY                     AGENT#{aid}         Capability policy
    COMM_RULE#{rule_id}                     META                Communication rule
    SCHEDULE#{aid}                          META                Schedule policy

GSIs:
    status-index:    PK=status, SK=updated_at
    tenant-index:    PK=tenant_id, SK=updated_at
    lifecycle-index: PK=lifecycle_status, SK=updated_at
"""

import os
from datetime import datetime, timezone
from typing import Any

import boto3
import structlog
from botocore.exceptions import ClientError

from harbor.models.agent import (
    AgentLifecycle,
    AgentRecord,
    AgentVersion,
    AuditEntry,
    HealthStatus,
)
from harbor.models.policy import (
    CapabilityPolicy,
    CommunicationRule,
    SchedulePolicy,
)

logger = structlog.get_logger(__name__)

DEFAULT_TABLE = "harbor-agent-registry"


class AgentStore:
    """Multi-tenant DynamoDB store for agent registry."""

    def __init__(self, table_name: str | None = None, region: str | None = None) -> None:
        self.table_name = table_name or os.environ.get("HARBOR_TABLE", DEFAULT_TABLE)
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._table: Any = None

    @property
    def table(self) -> Any:
        """Lazy-init DynamoDB table resource."""
        if self._table is None:
            self._table = boto3.resource("dynamodb", region_name=self.region).Table(self.table_name)
        return self._table

    # ── Key helpers ───────────────────────────────────────

    @staticmethod
    def _agent_pk(tenant_id: str, agent_id: str) -> str:
        return f"TENANT#{tenant_id}#AGENT#{agent_id}"

    @staticmethod
    def _cap_pk(tenant_id: str, capability: str) -> str:
        return f"TENANT#{tenant_id}#CAP#{capability}"

    @staticmethod
    def _phase_pk(tenant_id: str, phase: str) -> str:
        return f"TENANT#{tenant_id}#PHASE#{phase}"

    @staticmethod
    def _policy_pk(tenant_id: str) -> str:
        return f"TENANT#{tenant_id}#POLICY"

    # ── Agent CRUD ────────────────────────────────────────

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
        """List agents for a tenant with optional lifecycle filter and pagination."""
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
            kwargs["ExclusiveStartKey"] = self._decode_cursor(cursor)

        resp = self.table.query(**kwargs)
        records = [
            AgentRecord(**item) for item in resp.get("Items", []) if item.get("sk") == "META"
        ]
        next_cursor = self._encode_cursor(resp.get("LastEvaluatedKey"))
        return records, next_cursor

    def list_by_lifecycle(
        self,
        lifecycle: AgentLifecycle,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[AgentRecord], str | None]:
        """List agents across tenants by lifecycle status (for admin views)."""
        kwargs: dict[str, Any] = {
            "IndexName": "lifecycle-index",
            "KeyConditionExpression": "lifecycle_status = :ls",
            "ExpressionAttributeValues": {":ls": lifecycle.value},
            "Limit": limit,
            "ScanIndexForward": False,
        }
        if cursor:
            kwargs["ExclusiveStartKey"] = self._decode_cursor(cursor)

        resp = self.table.query(**kwargs)
        records = [
            AgentRecord(**item) for item in resp.get("Items", []) if item.get("sk") == "META"
        ]
        next_cursor = self._encode_cursor(resp.get("LastEvaluatedKey"))
        return records, next_cursor

    # ── Discovery ─────────────────────────────────────────

    def find_by_capability(self, tenant_id: str, capability: str) -> list[AgentRecord]:
        """Find agents by capability within a tenant."""
        resp = self.table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": self._cap_pk(tenant_id, capability)},
        )
        agent_ids = [item["agent_id"] for item in resp.get("Items", [])]
        return self._resolve_published(tenant_id, agent_ids)

    def find_by_phase(self, tenant_id: str, phase: str) -> list[AgentRecord]:
        """Find agents by phase within a tenant."""
        resp = self.table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": self._phase_pk(tenant_id, phase)},
        )
        agent_ids = [item["agent_id"] for item in resp.get("Items", [])]
        return self._resolve_published(tenant_id, agent_ids)

    # ── Version Snapshots ─────────────────────────────────

    def put_version(self, version: AgentVersion) -> None:
        """Store an immutable version snapshot."""
        self.table.put_item(
            Item={
                "pk": self._agent_pk(version.tenant_id, version.agent_id),
                "sk": f"VER#{version.version}",
                **version.model_dump(mode="json"),
            }
        )

    def list_versions(self, tenant_id: str, agent_id: str) -> list[AgentVersion]:
        """List all versions for an agent."""
        resp = self.table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={
                ":pk": self._agent_pk(tenant_id, agent_id),
                ":prefix": "VER#",
            },
        )
        return [AgentVersion(**item) for item in resp.get("Items", [])]

    # ── Health ────────────────────────────────────────────

    def put_health(self, health: HealthStatus) -> None:
        """Update agent health status."""
        self.table.put_item(
            Item={
                "pk": self._agent_pk(health.tenant_id, health.agent_id),
                "sk": "HEALTH",
                **health.model_dump(mode="json"),
            }
        )

    def get_health(self, tenant_id: str, agent_id: str) -> HealthStatus | None:
        """Get agent health status."""
        resp = self.table.get_item(Key={"pk": self._agent_pk(tenant_id, agent_id), "sk": "HEALTH"})
        item = resp.get("Item")
        return HealthStatus(**item) if item else None

    # ── Audit ─────────────────────────────────────────────

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

    # ── Capability Policy ─────────────────────────────────

    def put_capability_policy(self, policy: CapabilityPolicy) -> None:
        """Store capability policy for an agent."""
        self.table.put_item(
            Item={
                "pk": self._policy_pk(policy.tenant_id),
                "sk": f"AGENT#{policy.agent_id}",
                **policy.model_dump(mode="json"),
            }
        )

    def get_capability_policy(self, tenant_id: str, agent_id: str) -> CapabilityPolicy | None:
        """Get capability policy for an agent."""
        resp = self.table.get_item(
            Key={"pk": self._policy_pk(tenant_id), "sk": f"AGENT#{agent_id}"}
        )
        item = resp.get("Item")
        return CapabilityPolicy(**item) if item else None

    # ── Communication Rules ───────────────────────────────

    def put_communication_rule(self, rule: CommunicationRule) -> None:
        """Store a communication rule."""
        self.table.put_item(
            Item={
                "pk": f"COMM_RULE#{rule.rule_id}",
                "sk": "META",
                **rule.model_dump(mode="json"),
            }
        )

    def get_communication_rule(self, rule_id: str) -> CommunicationRule | None:
        """Get a communication rule by ID."""
        resp = self.table.get_item(Key={"pk": f"COMM_RULE#{rule_id}", "sk": "META"})
        item = resp.get("Item")
        return CommunicationRule(**item) if item else None

    def list_communication_rules(self) -> list[CommunicationRule]:
        """List all communication rules (scan — small dataset)."""
        resp = self.table.scan(
            FilterExpression="begins_with(pk, :prefix) AND sk = :meta",
            ExpressionAttributeValues={":prefix": "COMM_RULE#", ":meta": "META"},
        )
        return [CommunicationRule(**item) for item in resp.get("Items", [])]

    # ── Schedule Policy ───────────────────────────────────

    def put_schedule_policy(self, policy: SchedulePolicy) -> None:
        """Store schedule policy for an agent."""
        self.table.put_item(
            Item={
                "pk": f"SCHEDULE#{policy.agent_id}",
                "sk": "META",
                **policy.model_dump(mode="json"),
            }
        )

    def get_schedule_policy(self, agent_id: str) -> SchedulePolicy | None:
        """Get schedule policy for an agent."""
        resp = self.table.get_item(Key={"pk": f"SCHEDULE#{agent_id}", "sk": "META"})
        item = resp.get("Item")
        return SchedulePolicy(**item) if item else None

    # ── Internal ──────────────────────────────────────────

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

    @staticmethod
    def _encode_cursor(key: dict[str, Any] | None) -> str | None:
        """Encode LastEvaluatedKey as a cursor string."""
        if not key:
            return None
        import json
        import base64

        return base64.urlsafe_b64encode(json.dumps(key).encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> dict[str, Any]:
        """Decode a cursor string back to LastEvaluatedKey."""
        import json
        import base64

        return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())  # type: ignore[no-any-return]

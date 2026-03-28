"""DynamoDB-backed agent store — single-table design.

Table schema:
    PK              SK                  Purpose
    AGENT#{id}      META                Agent record
    AGENT#{id}      VER#{version}       Version snapshot
    CAP#{capability} AGENT#{id}         Reverse index: capability → agent
    PHASE#{phase}   AGENT#{id}          Reverse index: phase → agent

GSI: status-index
    PK: status      SK: updated_at
"""

import os
from datetime import datetime, timezone

import boto3
import structlog
from botocore.exceptions import ClientError

from harbor.models.agent import AgentRecord, AgentStatus

logger = structlog.get_logger(__name__)

DEFAULT_TABLE = "harbor-agent-registry"


class AgentStore:
    def __init__(self, table_name: str | None = None, region: str | None = None):
        self.table_name = table_name or os.environ.get("HARBOR_TABLE", DEFAULT_TABLE)
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._table = None

    @property
    def table(self):
        if self._table is None:
            self._table = boto3.resource("dynamodb", region_name=self.region).Table(
                self.table_name
            )
        return self._table

    # ── CRUD ──────────────────────────────────────────────

    def put(self, record: AgentRecord) -> None:
        record.updated_at = datetime.now(timezone.utc)
        item = {"pk": f"AGENT#{record.agent_id}", "sk": "META", **record.model_dump(mode="json")}
        self.table.put_item(Item=item)
        self._write_indexes(record)
        logger.info("agent_stored", agent_id=record.agent_id)

    def get(self, agent_id: str) -> AgentRecord | None:
        resp = self.table.get_item(Key={"pk": f"AGENT#{agent_id}", "sk": "META"})
        item = resp.get("Item")
        return AgentRecord(**item) if item else None

    def delete(self, agent_id: str) -> bool:
        existing = self.get(agent_id)
        if not existing:
            return False
        self.table.delete_item(Key={"pk": f"AGENT#{agent_id}", "sk": "META"})
        self._delete_indexes(existing)
        return True

    def update(self, agent_id: str, updates: dict) -> AgentRecord | None:
        existing = self.get(agent_id)
        if not existing:
            return None
        merged = existing.model_copy(update=updates)
        self.put(merged)
        return merged

    # ── Discovery ─────────────────────────────────────────

    def find_by_capability(self, capability: str) -> list[AgentRecord]:
        resp = self.table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": f"CAP#{capability}"},
        )
        agent_ids = [item["agent_id"] for item in resp.get("Items", [])]
        return self._resolve_active(agent_ids)

    def find_by_phase(self, phase: str) -> list[AgentRecord]:
        resp = self.table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": f"PHASE#{phase}"},
        )
        agent_ids = [item["agent_id"] for item in resp.get("Items", [])]
        return self._resolve_active(agent_ids)

    def list_all(self, status: AgentStatus | None = None) -> list[AgentRecord]:
        scan_kwargs: dict = {
            "FilterExpression": "sk = :meta",
            "ExpressionAttributeValues": {":meta": "META"},
        }
        if status:
            scan_kwargs["FilterExpression"] += " AND #s = :status"
            scan_kwargs["ExpressionAttributeNames"] = {"#s": "status"}
            scan_kwargs["ExpressionAttributeValues"][":status"] = status.value
        resp = self.table.scan(**scan_kwargs)
        records = [AgentRecord(**item) for item in resp.get("Items", [])]
        return sorted(records, key=lambda r: r.name)

    # ── Internal ──────────────────────────────────────────

    def _resolve_active(self, agent_ids: list[str]) -> list[AgentRecord]:
        results = []
        for aid in agent_ids:
            r = self.get(aid)
            if r and r.status == AgentStatus.ACTIVE:
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
                    "pk": f"CAP#{cap}",
                    "sk": f"AGENT#{record.agent_id}",
                    "agent_id": record.agent_id,
                }
            )
        for phase in record.phase_affinity:
            self.table.put_item(
                Item={
                    "pk": f"PHASE#{phase}",
                    "sk": f"AGENT#{record.agent_id}",
                    "agent_id": record.agent_id,
                }
            )

    def _delete_indexes(self, record: AgentRecord) -> None:
        for cap in record.capabilities:
            try:
                self.table.delete_item(
                    Key={"pk": f"CAP#{cap}", "sk": f"AGENT#{record.agent_id}"}
                )
            except ClientError:
                pass
        for phase in record.phase_affinity:
            try:
                self.table.delete_item(
                    Key={"pk": f"PHASE#{phase}", "sk": f"AGENT#{record.agent_id}"}
                )
            except ClientError:
                pass

"""Policy store — capability, communication, and schedule policy persistence."""

from harbor.models.policy import CapabilityPolicy, CommunicationRule, SchedulePolicy
from harbor.store.base import BaseStore


class PolicyStore(BaseStore):
    """CRUD for governance policies."""

    # ── Capability Policy ─────────────────────────────────

    @staticmethod
    def _policy_pk(tenant_id: str) -> str:
        return f"TENANT#{tenant_id}#POLICY"

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

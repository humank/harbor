"""Policy enforcement service — CRUD + capability, communication, schedule checks."""

import fnmatch
from datetime import datetime, timezone

import structlog

from harbor.events.emitter import EventEmitter
from harbor.models.agent import AuditEntry
from harbor.models.policy import (
    CapabilityPolicy,
    CommunicationRule,
    PolicyDecision,
    SchedulePolicy,
)
from harbor.store.audit_store import AuditStore
from harbor.store.policy_store import PolicyStore

logger = structlog.get_logger(__name__)


class PolicyService:
    """Policy CRUD and governance evaluation."""

    def __init__(self, store: PolicyStore, audit_store: AuditStore, events: EventEmitter) -> None:
        self.store = store
        self.audit_store = audit_store
        self.events = events

    # ── CRUD (with audit) ─────────────────────────────────

    def put_capability_policy(self, policy: CapabilityPolicy, actor: str = "system") -> None:
        """Create or update a capability policy."""
        self.store.put_capability_policy(policy)
        self._audit(policy.tenant_id, policy.agent_id, "capability_policy_updated", actor)
        logger.info("capability_policy_updated", agent_id=policy.agent_id)

    def get_capability_policy(self, tenant_id: str, agent_id: str) -> CapabilityPolicy | None:
        """Get capability policy for an agent."""
        return self.store.get_capability_policy(tenant_id, agent_id)

    def put_communication_rule(self, rule: CommunicationRule, actor: str = "system") -> None:
        """Create or update a communication rule."""
        self.store.put_communication_rule(rule)
        logger.info("communication_rule_updated", rule_id=rule.rule_id)

    def list_communication_rules(self) -> list[CommunicationRule]:
        """List all communication rules."""
        return self.store.list_communication_rules()

    def put_schedule_policy(self, policy: SchedulePolicy, actor: str = "system") -> None:
        """Create or update a schedule policy."""
        self.store.put_schedule_policy(policy)
        self._audit(policy.tenant_id, policy.agent_id, "schedule_policy_updated", actor)
        logger.info("schedule_policy_updated", agent_id=policy.agent_id)

    def get_schedule_policy(self, agent_id: str) -> SchedulePolicy | None:
        """Get schedule policy for an agent."""
        return self.store.get_schedule_policy(agent_id)

    # ── Evaluation ────────────────────────────────────────

    def check_capability(
        self, tenant_id: str, agent_id: str, resource_type: str, resource_name: str,
    ) -> PolicyDecision:
        """Check if an agent is allowed to use a specific resource."""
        policy = self.store.get_capability_policy(tenant_id, agent_id)
        if not policy:
            return PolicyDecision(allowed=True, reason="no policy — allowed by default")

        perms = getattr(policy, resource_type, None)
        if perms is None:
            return PolicyDecision(allowed=True, reason=f"no {resource_type} policy")

        for pattern in perms.denied:
            if fnmatch.fnmatch(resource_name, pattern):
                return PolicyDecision(allowed=False, reason=f"denied by pattern: {pattern}")

        if perms.allowed:
            for pattern in perms.allowed:
                if fnmatch.fnmatch(resource_name, pattern):
                    return PolicyDecision(allowed=True, reason=f"allowed by pattern: {pattern}")
            return PolicyDecision(allowed=False, reason="not in allowed list")

        return PolicyDecision(allowed=True, reason="no restrictions")

    def check_communication(self, from_agent: str, to_agent: str) -> PolicyDecision:
        """Check if agent A is allowed to communicate with agent B."""
        rules = self.store.list_communication_rules()
        if not rules:
            return PolicyDecision(allowed=True, reason="no communication rules")

        matching = [r for r in rules if self._rule_matches(r, from_agent, to_agent)]
        if not matching:
            return PolicyDecision(
                allowed=False, reason="no matching rule — default deny (allowlist mode)",
            )

        rule = matching[0]
        return PolicyDecision(
            allowed=rule.allowed, reason=f"rule {rule.rule_id}: allowed={rule.allowed}",
        )

    @staticmethod
    def _rule_matches(rule: CommunicationRule, from_agent: str, to_agent: str) -> bool:
        return fnmatch.fnmatch(from_agent, rule.from_agent) and fnmatch.fnmatch(
            to_agent, rule.to_agent,
        )

    def check_schedule(self, agent_id: str) -> PolicyDecision:
        """Check if an agent is within its active schedule window."""
        policy = self.store.get_schedule_policy(agent_id)
        if not policy:
            return PolicyDecision(allowed=True, reason="no schedule policy")
        if not policy.active_windows and not policy.blackout_windows:
            return PolicyDecision(allowed=True, reason="no windows defined")
        return PolicyDecision(allowed=True, reason="schedule check — cron eval not yet implemented")

    def evaluate(
        self, tenant_id: str, from_agent: str, to_agent: str,
        resource_type: str | None = None, resource_name: str | None = None,
    ) -> PolicyDecision:
        """Full policy evaluation: communication + schedule + capability."""
        comm = self.check_communication(from_agent, to_agent)
        if not comm.allowed:
            self.events.policy_violation(tenant_id, to_agent, "communication", comm.reason)
            return comm

        sched = self.check_schedule(to_agent)
        if not sched.allowed:
            self.events.policy_violation(tenant_id, to_agent, "schedule", sched.reason)
            return sched

        if resource_type and resource_name:
            cap = self.check_capability(tenant_id, to_agent, resource_type, resource_name)
            if not cap.allowed:
                self.events.policy_violation(tenant_id, to_agent, "capability", cap.reason)
                return cap

        return PolicyDecision(allowed=True, reason="all policies passed")

    # ── Internal ──────────────────────────────────────────

    def _audit(self, tenant_id: str, agent_id: str, action: str, actor: str) -> None:
        self.audit_store.put_audit(AuditEntry(
            agent_id=agent_id, tenant_id=tenant_id, action=action,
            actor=actor, timestamp=datetime.now(timezone.utc),
        ))

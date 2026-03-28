"""Policy enforcement service — capability, communication, schedule checks."""

import fnmatch

import structlog

from harbor.events.emitter import EventEmitter
from harbor.models.policy import (
    CommunicationRule,
)
from harbor.store.dynamo import AgentStore

logger = structlog.get_logger(__name__)


class PolicyDecision:
    """Result of a policy evaluation."""

    def __init__(self, allowed: bool, reason: str = "") -> None:
        self.allowed = allowed
        self.reason = reason

    def __bool__(self) -> bool:
        return self.allowed


class PolicyService:
    """Evaluate governance policies."""

    def __init__(self, store: AgentStore) -> None:
        self.store = store
        self._events = EventEmitter()

    # ── Capability check ──────────────────────────────────

    def check_capability(
        self, tenant_id: str, agent_id: str, resource_type: str, resource_name: str
    ) -> PolicyDecision:
        """Check if an agent is allowed to use a specific resource."""
        policy = self.store.get_capability_policy(tenant_id, agent_id)
        if not policy:
            return PolicyDecision(True, "no policy — allowed by default")

        perms = getattr(policy, resource_type, None)
        if perms is None:
            return PolicyDecision(True, f"no {resource_type} policy")

        # Check denied first
        for pattern in perms.denied:
            if fnmatch.fnmatch(resource_name, pattern):
                return PolicyDecision(False, f"denied by pattern: {pattern}")

        # Check allowed
        if perms.allowed:
            for pattern in perms.allowed:
                if fnmatch.fnmatch(resource_name, pattern):
                    return PolicyDecision(True, f"allowed by pattern: {pattern}")
            return PolicyDecision(False, "not in allowed list")

        return PolicyDecision(True, "no restrictions")

    # ── Communication check ───────────────────────────────

    def check_communication(self, from_agent: str, to_agent: str) -> PolicyDecision:
        """Check if agent A is allowed to communicate with agent B."""
        rules = self.store.list_communication_rules()
        if not rules:
            return PolicyDecision(True, "no communication rules")

        # Find matching rules (most specific first)
        matching = [r for r in rules if self._rule_matches(r, from_agent, to_agent)]

        if not matching:
            # Default: allowlist mode = deny, denylist mode = allow
            return PolicyDecision(False, "no matching rule — default deny (allowlist mode)")

        # Use first matching rule
        rule = matching[0]
        return PolicyDecision(rule.allowed, f"rule {rule.rule_id}: allowed={rule.allowed}")

    @staticmethod
    def _rule_matches(rule: CommunicationRule, from_agent: str, to_agent: str) -> bool:
        return fnmatch.fnmatch(from_agent, rule.from_agent) and fnmatch.fnmatch(
            to_agent, rule.to_agent
        )

    # ── Schedule check ────────────────────────────────────

    def check_schedule(self, agent_id: str) -> PolicyDecision:
        """Check if an agent is within its active schedule window."""
        policy = self.store.get_schedule_policy(agent_id)
        if not policy:
            return PolicyDecision(True, "no schedule policy")
        if not policy.active_windows and not policy.blackout_windows:
            return PolicyDecision(True, "no windows defined")
        # Full cron evaluation deferred — for now, allow if policy exists
        # TODO: implement cron window evaluation
        return PolicyDecision(True, "schedule check — cron eval not yet implemented")

    # ── Combined evaluation ───────────────────────────────

    def evaluate(
        self,
        tenant_id: str,
        from_agent: str,
        to_agent: str,
        resource_type: str | None = None,
        resource_name: str | None = None,
    ) -> PolicyDecision:
        """Full policy evaluation: communication + schedule + capability."""
        # 1. Communication
        comm = self.check_communication(from_agent, to_agent)
        if not comm:
            logger.warning(
                "policy_denied",
                check="communication",
                from_agent=from_agent,
                to_agent=to_agent,
                reason=comm.reason,
            )
            self._events.policy_violation(tenant_id, to_agent, "communication", comm.reason)
            return comm

        # 2. Schedule
        sched = self.check_schedule(to_agent)
        if not sched:
            logger.warning(
                "policy_denied", check="schedule", agent_id=to_agent, reason=sched.reason
            )
            self._events.policy_violation(tenant_id, to_agent, "schedule", sched.reason)
            return sched

        # 3. Capability (if resource specified)
        if resource_type and resource_name:
            cap = self.check_capability(tenant_id, to_agent, resource_type, resource_name)
            if not cap:
                logger.warning(
                    "policy_denied",
                    check="capability",
                    agent_id=to_agent,
                    resource=resource_name,
                    reason=cap.reason,
                )
                self._events.policy_violation(tenant_id, to_agent, "capability", cap.reason)
                return cap

        return PolicyDecision(True, "all policies passed")

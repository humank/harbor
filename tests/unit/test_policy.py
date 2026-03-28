"""Unit tests for the policy enforcement service."""

import pytest

from harbor.models.policy import CapabilityPolicy, CommunicationRule, ResourcePermission
from harbor.policy.service import PolicyDecision, PolicyService

TENANT = "tenant-001"


@pytest.fixture
def policy_svc(store):
    return PolicyService(store)


# ── Capability tests ──────────────────────────────────────


def test_capability_allowed(store, policy_svc):
    store.put_capability_policy(
        CapabilityPolicy(
            agent_id="agent-1",
            tenant_id=TENANT,
            tools=ResourcePermission(allowed=["db_query"]),
        )
    )
    result = policy_svc.check_capability(TENANT, "agent-1", "tools", "db_query")
    assert result.allowed is True


def test_capability_denied(store, policy_svc):
    store.put_capability_policy(
        CapabilityPolicy(
            agent_id="agent-1",
            tenant_id=TENANT,
            tools=ResourcePermission(denied=["execute_trade"]),
        )
    )
    result = policy_svc.check_capability(TENANT, "agent-1", "tools", "execute_trade")
    assert result.allowed is False


def test_capability_wildcard_deny(store, policy_svc):
    store.put_capability_policy(
        CapabilityPolicy(
            agent_id="agent-1",
            tenant_id=TENANT,
            tools=ResourcePermission(denied=["external-*"]),
        )
    )
    result = policy_svc.check_capability(TENANT, "agent-1", "tools", "external-api")
    assert result.allowed is False


def test_capability_not_in_allowed_list(store, policy_svc):
    store.put_capability_policy(
        CapabilityPolicy(
            agent_id="agent-1",
            tenant_id=TENANT,
            tools=ResourcePermission(allowed=["db_query"]),
        )
    )
    result = policy_svc.check_capability(TENANT, "agent-1", "tools", "send_email")
    assert result.allowed is False


def test_capability_no_policy(policy_svc):
    result = policy_svc.check_capability(TENANT, "agent-1", "tools", "anything")
    assert result.allowed is True


# ── Communication tests ───────────────────────────────────


def test_communication_allowed(store, policy_svc):
    store.put_communication_rule(
        CommunicationRule(rule_id="r1", from_agent="agent-a", to_agent="agent-b", allowed=True)
    )
    result = policy_svc.check_communication("agent-a", "agent-b")
    assert result.allowed is True


def test_communication_denied(store, policy_svc):
    store.put_communication_rule(
        CommunicationRule(rule_id="r1", from_agent="*", to_agent="internal-*", allowed=False)
    )
    result = policy_svc.check_communication("ext", "internal-db")
    assert result.allowed is False


def test_communication_no_rules(policy_svc):
    result = policy_svc.check_communication("agent-a", "agent-b")
    assert result.allowed is True


# ── Evaluate (combined) tests ─────────────────────────────


def test_evaluate_all_pass(store, policy_svc):
    store.put_communication_rule(
        CommunicationRule(rule_id="r1", from_agent="agent-a", to_agent="agent-b", allowed=True)
    )
    store.put_capability_policy(
        CapabilityPolicy(
            agent_id="agent-b",
            tenant_id=TENANT,
            tools=ResourcePermission(allowed=["db_query"]),
        )
    )
    result = policy_svc.evaluate(TENANT, "agent-a", "agent-b", "tools", "db_query")
    assert result.allowed is True


def test_evaluate_comm_denied(store, policy_svc):
    store.put_communication_rule(
        CommunicationRule(rule_id="r1", from_agent="agent-a", to_agent="agent-b", allowed=False)
    )
    result = policy_svc.evaluate(TENANT, "agent-a", "agent-b")
    assert result.allowed is False

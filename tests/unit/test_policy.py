"""Unit tests for the policy enforcement service."""

from unittest.mock import MagicMock

import pytest
from moto import mock_aws

from harbor.models.policy import CapabilityPolicy, CommunicationRule, ResourcePermission
from harbor.policy.service import PolicyService
from harbor.store.policy_store import PolicyStore
from harbor.store.audit_store import AuditStore
from tests.unit.conftest import TABLE_NAME, _create_table

TENANT = "tenant-001"


@pytest.fixture
def setup():
    with mock_aws():
        _create_table(TABLE_NAME)
        kwargs = {"table_name": TABLE_NAME, "region": "us-east-1"}
        store = PolicyStore(**kwargs)
        audit = AuditStore(**kwargs)
        svc = PolicyService(store, audit, events=MagicMock())
        yield store, svc


# ── Capability tests ──────────────────────────────────────


def test_capability_allowed(setup):
    store, svc = setup
    store.put_capability_policy(
        CapabilityPolicy(agent_id="agent-1", tenant_id=TENANT, tools=ResourcePermission(allowed=["db_query"]))
    )
    assert svc.check_capability(TENANT, "agent-1", "tools", "db_query").allowed is True


def test_capability_denied(setup):
    store, svc = setup
    store.put_capability_policy(
        CapabilityPolicy(agent_id="agent-1", tenant_id=TENANT, tools=ResourcePermission(denied=["execute_trade"]))
    )
    assert svc.check_capability(TENANT, "agent-1", "tools", "execute_trade").allowed is False


def test_capability_wildcard_deny(setup):
    store, svc = setup
    store.put_capability_policy(
        CapabilityPolicy(agent_id="agent-1", tenant_id=TENANT, tools=ResourcePermission(denied=["external-*"]))
    )
    assert svc.check_capability(TENANT, "agent-1", "tools", "external-api").allowed is False


def test_capability_not_in_allowed_list(setup):
    store, svc = setup
    store.put_capability_policy(
        CapabilityPolicy(agent_id="agent-1", tenant_id=TENANT, tools=ResourcePermission(allowed=["db_query"]))
    )
    assert svc.check_capability(TENANT, "agent-1", "tools", "send_email").allowed is False


def test_capability_no_policy(setup):
    _, svc = setup
    assert svc.check_capability(TENANT, "agent-1", "tools", "anything").allowed is True


# ── Communication tests ───────────────────────────────────


def test_communication_allowed(setup):
    store, svc = setup
    store.put_communication_rule(CommunicationRule(rule_id="r1", from_agent="agent-a", to_agent="agent-b", allowed=True))
    assert svc.check_communication("agent-a", "agent-b").allowed is True


def test_communication_denied(setup):
    store, svc = setup
    store.put_communication_rule(CommunicationRule(rule_id="r1", from_agent="*", to_agent="internal-*", allowed=False))
    assert svc.check_communication("ext", "internal-db").allowed is False


def test_communication_no_rules(setup):
    _, svc = setup
    assert svc.check_communication("agent-a", "agent-b").allowed is True


# ── Evaluate (combined) tests ─────────────────────────────


def test_evaluate_all_pass(setup):
    store, svc = setup
    store.put_communication_rule(CommunicationRule(rule_id="r1", from_agent="agent-a", to_agent="agent-b", allowed=True))
    store.put_capability_policy(
        CapabilityPolicy(agent_id="agent-b", tenant_id=TENANT, tools=ResourcePermission(allowed=["db_query"]))
    )
    assert svc.evaluate(TENANT, "agent-a", "agent-b", "tools", "db_query").allowed is True


def test_evaluate_comm_denied(setup):
    store, svc = setup
    store.put_communication_rule(CommunicationRule(rule_id="r1", from_agent="agent-a", to_agent="agent-b", allowed=False))
    assert svc.evaluate(TENANT, "agent-a", "agent-b").allowed is False

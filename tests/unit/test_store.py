"""Unit tests for DynamoDB stores."""

import pytest
from moto import mock_aws

from harbor.models.agent import (
    AgentLifecycle,
    AgentRecord,
    AgentVersion,
    AuditEntry,
    HealthState,
    HealthStatus,
    OwnerInfo,
)
from harbor.models.policy import (
    CapabilityPolicy,
    CommunicationRule,
    ResourcePermission,
    SchedulePolicy,
)
from harbor.store.agent_store import AgentStore
from harbor.store.audit_store import AuditStore
from harbor.store.health_store import HealthStore
from harbor.store.policy_store import PolicyStore
from harbor.store.version_store import VersionStore
from tests.unit.conftest import TABLE_NAME, _create_table


@pytest.fixture
def stores():
    """Provide all stores sharing the same moto table."""
    with mock_aws():
        _create_table(TABLE_NAME)
        kwargs = {"table_name": TABLE_NAME, "region": "us-east-1"}
        yield {
            "agent": AgentStore(**kwargs),
            "audit": AuditStore(**kwargs),
            "health": HealthStore(**kwargs),
            "policy": PolicyStore(**kwargs),
            "version": VersionStore(**kwargs),
        }


def _make_record(agent_id: str = "agent-1", tenant_id: str = "tenant-001", **kw) -> AgentRecord:
    defaults = dict(
        agent_id=agent_id,
        name=f"Agent {agent_id}",
        tenant_id=tenant_id,
        owner=OwnerInfo(owner_id="u1", team="eng", org_id="org1"),
    )
    return AgentRecord(**{**defaults, **kw})


# ── AgentStore ────────────────────────────────────────────


def test_put_and_get_agent(stores):
    stores["agent"].put_agent(_make_record())
    result = stores["agent"].get_agent("tenant-001", "agent-1")
    assert result is not None
    assert result.agent_id == "agent-1"


def test_get_nonexistent(stores):
    assert stores["agent"].get_agent("tenant-001", "no-such") is None


def test_delete_agent(stores):
    stores["agent"].put_agent(_make_record())
    assert stores["agent"].delete_agent("tenant-001", "agent-1") is True
    assert stores["agent"].get_agent("tenant-001", "agent-1") is None


def test_update_agent(stores):
    stores["agent"].put_agent(_make_record())
    updated = stores["agent"].update_agent("tenant-001", "agent-1", {"description": "updated"})
    assert updated is not None
    assert updated.description == "updated"


def test_tenant_isolation(stores):
    stores["agent"].put_agent(_make_record(agent_id="a1", tenant_id="tenant-001"))
    stores["agent"].put_agent(_make_record(agent_id="a2", tenant_id="tenant-002"))
    assert stores["agent"].get_agent("tenant-001", "a2") is None
    assert stores["agent"].get_agent("tenant-002", "a1") is None


def test_list_by_tenant(stores):
    for i in range(3):
        stores["agent"].put_agent(_make_record(agent_id=f"a{i}"))
    records, _ = stores["agent"].list_by_tenant("tenant-001")
    assert len(records) == 3


def test_list_by_tenant_with_lifecycle_filter(stores):
    stores["agent"].put_agent(_make_record(agent_id="draft-1", lifecycle_status=AgentLifecycle.DRAFT))
    stores["agent"].put_agent(_make_record(agent_id="pub-1", lifecycle_status=AgentLifecycle.PUBLISHED))
    records, _ = stores["agent"].list_by_tenant("tenant-001", lifecycle=AgentLifecycle.PUBLISHED)
    assert len(records) == 1
    assert records[0].agent_id == "pub-1"


def test_find_by_capability(stores):
    stores["agent"].put_agent(
        _make_record(agent_id="cap-agent", capabilities=["cap1"], lifecycle_status=AgentLifecycle.PUBLISHED)
    )
    results = stores["agent"].find_by_capability("tenant-001", "cap1")
    assert len(results) == 1


def test_find_by_phase(stores):
    stores["agent"].put_agent(
        _make_record(agent_id="phase-agent", phase_affinity=["discovery"], lifecycle_status=AgentLifecycle.PUBLISHED)
    )
    results = stores["agent"].find_by_phase("tenant-001", "discovery")
    assert len(results) == 1


def test_pagination(stores):
    for i in range(5):
        stores["agent"].put_agent(_make_record(agent_id=f"a{i}"))
    page1, cursor = stores["agent"].list_by_tenant("tenant-001", limit=2)
    assert len(page1) == 2
    assert cursor is not None
    page2, _ = stores["agent"].list_by_tenant("tenant-001", limit=2, cursor=cursor)
    assert len(page2) > 0


# ── VersionStore ──────────────────────────────────────────


def test_put_and_list_versions(stores):
    for v in ["1.0.0", "2.0.0"]:
        stores["version"].put_version(
            AgentVersion(agent_id="agent-1", tenant_id="tenant-001", version=v, snapshot={"v": v})
        )
    versions = stores["version"].list_versions("tenant-001", "agent-1")
    assert len(versions) == 2


# ── HealthStore ───────────────────────────────────────────


def test_put_and_get_health(stores):
    stores["health"].put_health(
        HealthStatus(agent_id="agent-1", tenant_id="tenant-001", state=HealthState.HEALTHY)
    )
    health = stores["health"].get_health("tenant-001", "agent-1")
    assert health is not None
    assert health.state == HealthState.HEALTHY


# ── AuditStore ────────────────────────────────────────────


def test_put_and_list_audit(stores):
    for action in ["registered", "updated"]:
        stores["audit"].put_audit(
            AuditEntry(agent_id="agent-1", tenant_id="tenant-001", action=action, actor="user1")
        )
    entries = stores["audit"].list_audit("tenant-001", "agent-1")
    assert len(entries) == 2


# ── PolicyStore ───────────────────────────────────────────


def test_capability_policy_crud(stores):
    policy = CapabilityPolicy(
        agent_id="agent-1", tenant_id="tenant-001",
        tools=ResourcePermission(allowed=["tool-a"], denied=["tool-b"]),
    )
    stores["policy"].put_capability_policy(policy)
    result = stores["policy"].get_capability_policy("tenant-001", "agent-1")
    assert result is not None
    assert result.tools.allowed == ["tool-a"]


def test_communication_rule_crud(stores):
    rule = CommunicationRule(rule_id="rule-1", from_agent="agent-a", to_agent="agent-b", allowed=True)
    stores["policy"].put_communication_rule(rule)
    rules = stores["policy"].list_communication_rules()
    assert len(rules) == 1


def test_schedule_policy_crud(stores):
    policy = SchedulePolicy(agent_id="agent-1", tenant_id="tenant-001")
    stores["policy"].put_schedule_policy(policy)
    result = stores["policy"].get_schedule_policy("agent-1")
    assert result is not None

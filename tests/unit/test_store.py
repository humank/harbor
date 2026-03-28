"""Unit tests for DynamoDB agent store."""

import pytest

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


def _make_record(agent_id: str = "agent-1", tenant_id: str = "tenant-001", **kw) -> AgentRecord:
    defaults = dict(
        agent_id=agent_id,
        name=f"Agent {agent_id}",
        tenant_id=tenant_id,
        owner=OwnerInfo(owner_id="u1", team="eng", org_id="org1"),
    )
    return AgentRecord(**{**defaults, **kw})


def test_put_and_get_agent(store):
    record = _make_record()
    store.put_agent(record)
    result = store.get_agent("tenant-001", "agent-1")
    assert result is not None
    assert result.agent_id == "agent-1"
    assert result.name == "Agent agent-1"
    assert result.tenant_id == "tenant-001"


def test_get_nonexistent(store):
    assert store.get_agent("tenant-001", "no-such-agent") is None


def test_delete_agent(store):
    store.put_agent(_make_record())
    assert store.delete_agent("tenant-001", "agent-1") is True
    assert store.get_agent("tenant-001", "agent-1") is None


def test_update_agent(store):
    store.put_agent(_make_record())
    updated = store.update_agent("tenant-001", "agent-1", {"description": "updated desc"})
    assert updated is not None
    assert updated.description == "updated desc"
    fetched = store.get_agent("tenant-001", "agent-1")
    assert fetched.description == "updated desc"


def test_tenant_isolation(store):
    store.put_agent(_make_record(agent_id="a1", tenant_id="tenant-001"))
    store.put_agent(_make_record(agent_id="a2", tenant_id="tenant-002"))
    assert store.get_agent("tenant-001", "a1") is not None
    assert store.get_agent("tenant-002", "a2") is not None
    assert store.get_agent("tenant-001", "a2") is None
    assert store.get_agent("tenant-002", "a1") is None


def test_list_by_tenant(store):
    for i in range(3):
        store.put_agent(_make_record(agent_id=f"a{i}"))
    records, _ = store.list_by_tenant("tenant-001")
    assert len(records) == 3


def test_list_by_tenant_with_lifecycle_filter(store):
    store.put_agent(_make_record(agent_id="draft-1", lifecycle_status=AgentLifecycle.DRAFT))
    store.put_agent(_make_record(agent_id="pub-1", lifecycle_status=AgentLifecycle.PUBLISHED))
    records, _ = store.list_by_tenant("tenant-001", lifecycle=AgentLifecycle.PUBLISHED)
    assert len(records) == 1
    assert records[0].agent_id == "pub-1"


def test_find_by_capability(store):
    store.put_agent(
        _make_record(
            agent_id="cap-agent",
            capabilities=["cap1"],
            lifecycle_status=AgentLifecycle.PUBLISHED,
        )
    )
    results = store.find_by_capability("tenant-001", "cap1")
    assert len(results) == 1
    assert results[0].agent_id == "cap-agent"


def test_find_by_phase(store):
    store.put_agent(
        _make_record(
            agent_id="phase-agent",
            phase_affinity=["discovery"],
            lifecycle_status=AgentLifecycle.PUBLISHED,
        )
    )
    results = store.find_by_phase("tenant-001", "discovery")
    assert len(results) == 1
    assert results[0].agent_id == "phase-agent"


def test_put_and_list_versions(store):
    for v in ["1.0.0", "2.0.0"]:
        store.put_version(
            AgentVersion(
                agent_id="agent-1", tenant_id="tenant-001", version=v, snapshot={"v": v}
            )
        )
    versions = store.list_versions("tenant-001", "agent-1")
    assert len(versions) == 2
    assert {v.version for v in versions} == {"1.0.0", "2.0.0"}


def test_put_and_get_health(store):
    store.put_health(
        HealthStatus(
            agent_id="agent-1", tenant_id="tenant-001", state=HealthState.HEALTHY
        )
    )
    health = store.get_health("tenant-001", "agent-1")
    assert health is not None
    assert health.state == HealthState.HEALTHY


def test_put_and_list_audit(store):
    for action in ["registered", "updated"]:
        store.put_audit(
            AuditEntry(
                agent_id="agent-1", tenant_id="tenant-001", action=action, actor="user1"
            )
        )
    entries = store.list_audit("tenant-001", "agent-1")
    assert len(entries) == 2
    assert {e.action for e in entries} == {"registered", "updated"}


def test_capability_policy_crud(store):
    policy = CapabilityPolicy(
        agent_id="agent-1",
        tenant_id="tenant-001",
        tools=ResourcePermission(allowed=["tool-a"], denied=["tool-b"]),
    )
    store.put_capability_policy(policy)
    result = store.get_capability_policy("tenant-001", "agent-1")
    assert result is not None
    assert result.tools.allowed == ["tool-a"]
    assert result.tools.denied == ["tool-b"]


def test_communication_rule_crud(store):
    rule = CommunicationRule(
        rule_id="rule-1", from_agent="agent-a", to_agent="agent-b", allowed=True
    )
    store.put_communication_rule(rule)
    rules = store.list_communication_rules()
    assert len(rules) == 1
    assert rules[0].rule_id == "rule-1"
    assert rules[0].from_agent == "agent-a"


def test_schedule_policy_crud(store):
    policy = SchedulePolicy(agent_id="agent-1", tenant_id="tenant-001")
    store.put_schedule_policy(policy)
    result = store.get_schedule_policy("agent-1")
    assert result is not None
    assert result.agent_id == "agent-1"


def test_pagination(store):
    for i in range(5):
        store.put_agent(_make_record(agent_id=f"a{i}"))
    page1, cursor = store.list_by_tenant("tenant-001", limit=2)
    assert len(page1) == 2
    assert cursor is not None
    page2, _ = store.list_by_tenant("tenant-001", limit=2, cursor=cursor)
    assert len(page2) > 0
    all_ids = {r.agent_id for r in page1} | {r.agent_id for r in page2}
    assert len(all_ids) > 2

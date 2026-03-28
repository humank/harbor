"""Unit tests for the discovery service."""

import pytest

from harbor.discovery.service import DiscoveryService
from harbor.models.agent import AgentLifecycle, AgentRecord, OwnerInfo, RoutingRule


def _make_record(agent_id: str = "agent-1", tenant_id: str = "tenant-001", **kw: object) -> AgentRecord:
    defaults = dict(
        agent_id=agent_id,
        name=f"Agent {agent_id}",
        tenant_id=tenant_id,
        owner=OwnerInfo(owner_id="u1", team="eng", org_id="org1"),
    )
    return AgentRecord(**{**defaults, **kw})


@pytest.fixture
def discovery(store):
    return DiscoveryService(store)


def test_by_capability_returns_published(store, discovery):
    record = _make_record(capabilities=["nlp"], lifecycle_status=AgentLifecycle.PUBLISHED)
    store.put_agent(record)

    result = discovery.by_capability("tenant-001", "nlp")
    assert len(result) == 1
    assert result[0].agent_id == "agent-1"


def test_by_capability_excludes_draft(store, discovery):
    record = _make_record(capabilities=["nlp"])
    store.put_agent(record)

    result = discovery.by_capability("tenant-001", "nlp")
    assert result == []


def test_by_phase_returns_published(store, discovery):
    record = _make_record(phase_affinity=["discovery"], lifecycle_status=AgentLifecycle.PUBLISHED)
    store.put_agent(record)

    result = discovery.by_phase("tenant-001", "discovery")
    assert len(result) == 1
    assert result[0].agent_id == "agent-1"


def test_resolve_returns_best(store, discovery):
    low = _make_record(
        agent_id="low",
        capabilities=["nlp"],
        routing_rules=[RoutingRule(capability="nlp", priority=1)],
        lifecycle_status=AgentLifecycle.PUBLISHED,
    )
    high = _make_record(
        agent_id="high",
        capabilities=["nlp"],
        routing_rules=[RoutingRule(capability="nlp", priority=10)],
        lifecycle_status=AgentLifecycle.PUBLISHED,
    )
    store.put_agent(low)
    store.put_agent(high)

    result = discovery.resolve("tenant-001", capability="nlp")
    assert result is not None
    assert result.agent_id == "high"


def test_resolve_returns_none_when_empty(discovery):
    result = discovery.resolve("tenant-001", capability="nonexistent")
    assert result is None


def test_tenant_scoped(store, discovery):
    record = _make_record(
        tenant_id="tenant-001",
        capabilities=["nlp"],
        lifecycle_status=AgentLifecycle.PUBLISHED,
    )
    store.put_agent(record)

    result = discovery.by_capability("tenant-002", "nlp")
    assert result == []

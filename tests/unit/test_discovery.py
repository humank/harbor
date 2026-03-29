"""Unit tests for the discovery service."""

import pytest
from moto import mock_aws

from harbor.discovery.service import DiscoveryService
from harbor.models.agent import AgentLifecycle, AgentRecord, OwnerInfo, RoutingRule
from harbor.store.agent_store import AgentStore
from tests.unit.conftest import TABLE_NAME, _create_table


def _make_record(agent_id: str = "agent-1", tenant_id: str = "tenant-001", **kw: object) -> AgentRecord:
    defaults = dict(
        agent_id=agent_id,
        name=f"Agent {agent_id}",
        tenant_id=tenant_id,
        owner=OwnerInfo(owner_id="u1", team="eng", org_id="org1"),
    )
    return AgentRecord(**{**defaults, **kw})


@pytest.fixture
def setup():
    with mock_aws():
        _create_table(TABLE_NAME)
        store = AgentStore(table_name=TABLE_NAME, region="us-east-1")
        discovery = DiscoveryService(store)
        yield store, discovery


def test_by_capability_returns_published(setup):
    store, discovery = setup
    store.put_agent(_make_record(capabilities=["nlp"], lifecycle_status=AgentLifecycle.PUBLISHED))
    result = discovery.by_capability("tenant-001", "nlp")
    assert len(result) == 1


def test_by_capability_excludes_draft(setup):
    store, discovery = setup
    store.put_agent(_make_record(capabilities=["nlp"]))
    assert discovery.by_capability("tenant-001", "nlp") == []


def test_by_phase_returns_published(setup):
    store, discovery = setup
    store.put_agent(_make_record(phase_affinity=["discovery"], lifecycle_status=AgentLifecycle.PUBLISHED))
    result = discovery.by_phase("tenant-001", "discovery")
    assert len(result) == 1


def test_resolve_returns_best(setup):
    store, discovery = setup
    store.put_agent(_make_record(
        agent_id="low", capabilities=["nlp"],
        routing_rules=[RoutingRule(capability="nlp", priority=1)],
        lifecycle_status=AgentLifecycle.PUBLISHED,
    ))
    store.put_agent(_make_record(
        agent_id="high", capabilities=["nlp"],
        routing_rules=[RoutingRule(capability="nlp", priority=10)],
        lifecycle_status=AgentLifecycle.PUBLISHED,
    ))
    result = discovery.resolve("tenant-001", capability="nlp")
    assert result is not None
    assert result.agent_id == "high"


def test_resolve_returns_none_when_empty(setup):
    _, discovery = setup
    assert discovery.resolve("tenant-001", capability="nonexistent") is None


def test_tenant_scoped(setup):
    store, discovery = setup
    store.put_agent(_make_record(capabilities=["nlp"], lifecycle_status=AgentLifecycle.PUBLISHED))
    assert discovery.by_capability("tenant-002", "nlp") == []

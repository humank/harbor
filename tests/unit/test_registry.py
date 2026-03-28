"""Unit tests for the registry service."""

from datetime import datetime, timezone

import pytest

from harbor.exceptions import (
    AgentNotFoundError,
    DuplicateAgentError,
    InvalidLifecycleTransitionError,
)
from harbor.models.agent import AgentLifecycle, AgentRecord, OwnerInfo
from harbor.registry.service import TRANSITIONS, RegistryService


def _make_record(agent_id: str = "agent-1", tenant_id: str = "tenant-001", **kw) -> AgentRecord:
    defaults = dict(
        agent_id=agent_id,
        name=f"Agent {agent_id}",
        tenant_id=tenant_id,
        owner=OwnerInfo(owner_id="u1", team="eng", org_id="org1"),
    )
    return AgentRecord(**{**defaults, **kw})


@pytest.fixture
def registry(store):
    return RegistryService(store)


def _publish(registry: RegistryService, tid: str, aid: str) -> AgentRecord:
    """Walk an agent through draft → submitted → in_review → approved → published."""
    registry.submit(tid, aid)
    registry.transition(tid, aid, AgentLifecycle.IN_REVIEW)
    registry.approve(tid, aid)
    return registry.publish(tid, aid)


class TestRegister:
    def test_register_creates_draft(self, registry):
        record = registry.register(_make_record())
        assert record.lifecycle_status == AgentLifecycle.DRAFT

    def test_register_duplicate_raises(self, registry):
        registry.register(_make_record())
        with pytest.raises(DuplicateAgentError):
            registry.register(_make_record())


class TestGet:
    def test_get_not_found_raises(self, registry):
        with pytest.raises(AgentNotFoundError):
            registry.get("tenant-001", "nonexistent")


class TestLifecycle:
    def test_full_lifecycle_happy_path(self, registry):
        tid, aid = "tenant-001", "agent-1"
        r = registry.register(_make_record(aid, tid))
        assert r.lifecycle_status == AgentLifecycle.DRAFT

        r = registry.submit(tid, aid)
        assert r.lifecycle_status == AgentLifecycle.SUBMITTED

        r = registry.transition(tid, aid, AgentLifecycle.IN_REVIEW)
        assert r.lifecycle_status == AgentLifecycle.IN_REVIEW

        r = registry.approve(tid, aid)
        assert r.lifecycle_status == AgentLifecycle.APPROVED

        r = registry.publish(tid, aid)
        assert r.lifecycle_status == AgentLifecycle.PUBLISHED

    def test_invalid_transition_raises(self, registry):
        tid, aid = "tenant-001", "agent-1"
        registry.register(_make_record(aid, tid))
        with pytest.raises(InvalidLifecycleTransitionError):
            registry.transition(tid, aid, AgentLifecycle.PUBLISHED)

    def test_suspend_published(self, registry):
        tid, aid = "tenant-001", "agent-1"
        registry.register(_make_record(aid, tid))
        _publish(registry, tid, aid)
        r = registry.suspend(tid, aid, reason="incident")
        assert r.lifecycle_status == AgentLifecycle.SUSPENDED

    def test_deprecate_and_retire(self, registry):
        tid, aid = "tenant-001", "agent-1"
        registry.register(_make_record(aid, tid))
        _publish(registry, tid, aid)
        sunset = datetime(2025, 12, 31, tzinfo=timezone.utc)
        r = registry.deprecate(tid, aid, sunset_date=sunset)
        assert r.lifecycle_status == AgentLifecycle.DEPRECATED
        assert r.sunset_date == sunset

        r = registry.retire(tid, aid)
        assert r.lifecycle_status == AgentLifecycle.RETIRED

    def test_reject_returns_to_draft(self, registry):
        tid, aid = "tenant-001", "agent-1"
        registry.register(_make_record(aid, tid))
        registry.submit(tid, aid)
        registry.transition(tid, aid, AgentLifecycle.IN_REVIEW)
        r = registry.reject(tid, aid, reason="needs work")
        assert r.lifecycle_status == AgentLifecycle.DRAFT


class TestVersions:
    def test_create_version(self, registry):
        tid, aid = "tenant-001", "agent-1"
        registry.register(_make_record(aid, tid))
        registry.create_version(tid, aid)
        versions = registry.list_versions(tid, aid)
        assert len(versions) == 1
        assert versions[0].agent_id == aid


class TestAudit:
    def test_audit_trail(self, registry, store):
        tid, aid = "tenant-001", "agent-1"
        registry.register(_make_record(aid, tid))
        entries = store.list_audit(tid, aid)
        assert len(entries) >= 1
        assert entries[0].action == "registered"


class TestDeregister:
    def test_deregister(self, registry):
        tid, aid = "tenant-001", "agent-1"
        registry.register(_make_record(aid, tid))
        registry.deregister(tid, aid)
        with pytest.raises(AgentNotFoundError):
            registry.get(tid, aid)


class TestUpdateConfig:
    def test_update_config(self, registry):
        tid, aid = "tenant-001", "agent-1"
        registry.register(_make_record(aid, tid))
        updated = registry.update_config(tid, aid, {"description": "new desc"})
        assert updated.description == "new desc"

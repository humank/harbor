"""Unit tests for Pydantic models."""

from harbor.models.agent import (
    AgentLifecycle,
    AgentRecord,
    AgentVersion,
    AuditEntry,
    HealthState,
    HealthStatus,
    OwnerInfo,
    Visibility,
)
from harbor.models.policy import (
    CapabilityPolicy,
    CommunicationRule,
    PolicyMode,
    ResourcePermission,
    SchedulePolicy,
    TimeWindow,
)


def _make_record(**overrides: object) -> AgentRecord:
    defaults = {
        "agent_id": "test-agent",
        "name": "Test Agent",
        "tenant_id": "tenant-001",
        "owner": OwnerInfo(owner_id="user-1", team="eng", org_id="org-1"),
    }
    return AgentRecord(**{**defaults, **overrides})


class TestAgentRecord:
    def test_defaults(self) -> None:
        r = _make_record()
        assert r.lifecycle_status == AgentLifecycle.DRAFT
        assert r.visibility == Visibility.PRIVATE
        assert r.version == "1.0.0"
        assert r.timeout_seconds == 600

    def test_serialization_roundtrip(self) -> None:
        r = _make_record(capabilities=["cap1", "cap2"])
        data = r.model_dump(mode="json")
        r2 = AgentRecord(**data)
        assert r2.agent_id == r.agent_id
        assert r2.capabilities == ["cap1", "cap2"]
        assert r2.owner.owner_id == "user-1"

    def test_lifecycle_enum_values(self) -> None:
        assert AgentLifecycle.DRAFT.value == "draft"
        assert AgentLifecycle.PUBLISHED.value == "published"
        assert AgentLifecycle.SUSPENDED.value == "suspended"
        assert len(AgentLifecycle) == 8

    def test_visibility_enum(self) -> None:
        assert Visibility.PRIVATE.value == "private"
        assert Visibility.ORG_WIDE.value == "org_wide"

    def test_lifecycle_assignment(self) -> None:
        r = _make_record(lifecycle_status=AgentLifecycle.PUBLISHED)
        assert r.lifecycle_status == AgentLifecycle.PUBLISHED


class TestAgentVersion:
    def test_create(self) -> None:
        v = AgentVersion(
            agent_id="a1", tenant_id="t1", version="1.0.0", snapshot={"name": "test"}
        )
        assert v.version == "1.0.0"
        assert v.snapshot["name"] == "test"


class TestHealthStatus:
    def test_defaults(self) -> None:
        h = HealthStatus(agent_id="a1", tenant_id="t1")
        assert h.state == HealthState.UNKNOWN
        assert h.consecutive_failures == 0


class TestAuditEntry:
    def test_create(self) -> None:
        e = AuditEntry(agent_id="a1", tenant_id="t1", action="registered", actor="user-1")
        assert e.action == "registered"
        assert e.details == {}


class TestPolicyModels:
    def test_capability_policy(self) -> None:
        p = CapabilityPolicy(
            agent_id="a1",
            tenant_id="t1",
            tools=ResourcePermission(allowed=["db_query"], denied=["execute_trade"]),
        )
        assert "db_query" in p.tools.allowed
        assert "execute_trade" in p.tools.denied

    def test_communication_rule(self) -> None:
        r = CommunicationRule(
            rule_id="r1", from_agent="agent-a", to_agent="agent-b", allowed=True
        )
        assert r.allowed is True
        assert r.required is False

    def test_schedule_policy(self) -> None:
        s = SchedulePolicy(
            agent_id="a1",
            tenant_id="t1",
            active_windows=[TimeWindow(cron="0 9-17 * * MON-FRI", timezone="Asia/Taipei")],
        )
        assert len(s.active_windows) == 1
        assert s.active_windows[0].timezone == "Asia/Taipei"

    def test_policy_mode_enum(self) -> None:
        assert PolicyMode.ALLOWLIST.value == "allowlist"
        assert PolicyMode.DENYLIST.value == "denylist"

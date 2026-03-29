"""Governance policy models — capability, communication, schedule, approval."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


# ── Capability Policy ─────────────────────────────────────


class ResourcePermission(BaseModel):
    """Allowed/denied resource patterns."""

    allowed: list[str] = Field(default_factory=list)
    denied: list[str] = Field(default_factory=list)
    require_human: list[str] = Field(default_factory=list)


class CapabilityPolicy(BaseModel):
    """Defines what an agent is allowed to access."""

    agent_id: str
    tenant_id: str
    tools: ResourcePermission = Field(default_factory=ResourcePermission)
    mcp_servers: ResourcePermission = Field(default_factory=ResourcePermission)
    apis: ResourcePermission = Field(default_factory=ResourcePermission)
    data_classification_max: str = "internal"  # public | internal | confidential | restricted
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Communication Policy ──────────────────────────────────


class CommunicationRule(BaseModel):
    """A single agent-to-agent communication ACL rule."""

    rule_id: str
    from_agent: str  # agent_id or wildcard pattern
    to_agent: str
    allowed: bool = True
    required: bool = False  # Must call before acting
    conditions: list[str] = Field(default_factory=list)  # same_tenant, same_project, etc.


class PolicyMode(str, Enum):
    """Communication policy default stance."""

    ALLOWLIST = "allowlist"
    DENYLIST = "denylist"


class CommunicationPolicy(BaseModel):
    """Tenant-level agent-to-agent communication policy."""

    tenant_id: str
    mode: PolicyMode = PolicyMode.ALLOWLIST
    rules: list[CommunicationRule] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Schedule Policy ───────────────────────────────────────


class TimeWindow(BaseModel):
    """A cron-based time window."""

    cron: str  # e.g. "0 9-16 * * MON-FRI"
    timezone: str = "UTC"


class OutOfWindowAction(str, Enum):
    """What to do when agent is called outside active window."""

    QUEUE = "queue"
    REJECT = "reject"
    FALLBACK = "fallback_agent"


class SchedulePolicy(BaseModel):
    """Time-based access control for an agent."""

    agent_id: str
    tenant_id: str
    active_windows: list[TimeWindow] = Field(default_factory=list)
    blackout_windows: list[TimeWindow] = Field(default_factory=list)
    out_of_window_action: OutOfWindowAction = OutOfWindowAction.REJECT
    fallback_agent_id: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Approval Policy ───────────────────────────────────────


class ApprovalPolicy(BaseModel):
    """Defines who must approve an agent for a lifecycle transition."""

    environment: str  # dev | staging | prod
    required_roles: list[str] = Field(default_factory=list)
    min_approvals: int = 1
    prerequisites: dict[str, bool] = Field(default_factory=dict)


# ── Policy Decision ───────────────────────────────────────


class PolicyDecision(BaseModel):
    """Result of a policy evaluation."""

    allowed: bool
    reason: str = ""

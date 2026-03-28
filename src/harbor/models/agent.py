"""Agent data models — aligned with A2A Agent Card schema + APIM + governance extensions."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────


class AgentLifecycle(str, Enum):
    """Governance lifecycle states."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class Visibility(str, Enum):
    """Who can discover this agent."""

    PRIVATE = "private"
    OU_SHARED = "ou_shared"
    ORG_WIDE = "org_wide"


class HealthState(str, Enum):
    """Agent health status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# ── Tenant & Owner ────────────────────────────────────────


class TenantInfo(BaseModel):
    """Tenant context derived from AWS account."""

    tenant_id: str  # AWS Account ID
    org_id: str = ""  # AWS Organization ID
    ou_id: str = ""  # Organizational Unit ID
    project_id: str = ""  # Project identifier (account alias or tag)
    environment: str = "dev"  # dev | staging | prod


class OwnerInfo(BaseModel):
    """Agent owner metadata."""

    owner_id: str  # User or service principal
    team: str = ""
    org_id: str = ""


# ── A2A-compatible sub-models ─────────────────────────────


class AgentSkill(BaseModel):
    """A2A-compatible skill descriptor."""

    id: str
    name: str
    description: str
    input_modes: list[str] = Field(default_factory=lambda: ["text"])
    output_modes: list[str] = Field(default_factory=lambda: ["text"])
    tags: list[str] = Field(default_factory=list)


class RoutingRule(BaseModel):
    """Defines when this agent should be selected."""

    phase: str | None = None
    capability: str | None = None
    priority: int = 0
    condition: str | None = None


# ── Core Agent Record ─────────────────────────────────────


class AgentRecord(BaseModel):
    """Core agent metadata — A2A + APIM + governance fields."""

    # Identity
    agent_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"

    # Multi-tenant
    tenant_id: str
    owner: OwnerInfo
    visibility: Visibility = Visibility.PRIVATE
    lifecycle_status: AgentLifecycle = AgentLifecycle.DRAFT

    # A2A Agent Card fields
    url: str | None = None
    skills: list[AgentSkill] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    auth_schemes: list[dict[str, Any]] = Field(default_factory=list)

    # APIM extensions
    phase_affinity: list[str] = Field(default_factory=list)
    routing_rules: list[RoutingRule] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)

    # Runtime config
    model_id: str | None = None
    max_concurrency: int = 1
    timeout_seconds: int = 600
    retry_policy: dict[str, Any] = Field(
        default_factory=lambda: {"max_retries": 3, "backoff": "exponential"}
    )

    # Governance
    sunset_date: datetime | None = None  # For deprecated agents

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"


# ── Version Snapshot ──────────────────────────────────────


class AgentVersion(BaseModel):
    """Immutable snapshot of an agent at a specific version."""

    agent_id: str
    tenant_id: str
    version: str
    snapshot: dict[str, Any]  # Full AgentRecord serialized
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"


# ── Health Status ─────────────────────────────────────────


class HealthStatus(BaseModel):
    """Agent health tracking."""

    agent_id: str
    tenant_id: str
    state: HealthState = HealthState.UNKNOWN
    last_seen: datetime | None = None
    consecutive_failures: int = 0
    error_message: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Audit Entry ───────────────────────────────────────────


class AuditEntry(BaseModel):
    """Immutable audit log entry."""

    agent_id: str
    tenant_id: str
    action: str  # registered, updated, lifecycle_changed, policy_updated, etc.
    actor: str  # Who performed the action
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = Field(default_factory=dict)  # before/after diff, reason, etc.

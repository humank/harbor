"""Agent data models — aligned with A2A Agent Card schema + APIM + governance extensions.

Harbor is a registry, not a deployment tool. Agents are deployed by their operators
using their own tooling. They register here with metadata for discovery and governance.
"""

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


class CloudProvider(str, Enum):
    """Cloud provider where the agent runs."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ON_PREM = "on-prem"
    OTHER = "other"


# ── Tenant & Owner ────────────────────────────────────────


class TenantInfo(BaseModel):
    """Tenant context — cloud-agnostic.

    tenant_id is the canonical identifier:
    - AWS: Account ID (123456789012)
    - Azure: Subscription ID (uuid)
    - GCP: Project ID (my-project-123)
    - On-prem: org-assigned identifier
    """

    tenant_id: str
    provider: CloudProvider = CloudProvider.AWS
    org_id: str = ""
    ou_id: str = ""
    project_id: str = ""
    environment: str = "dev"  # dev | staging | prod


class OwnerInfo(BaseModel):
    """Agent owner metadata."""

    owner_id: str  # User or service principal
    team: str = ""
    org_id: str = ""


# ── Where the agent lives & how to reach it ───────────────


class RuntimeOrigin(BaseModel):
    """Where the agent is deployed. Filled by the operator, not Harbor."""

    provider: CloudProvider = CloudProvider.AWS
    runtime: str = ""  # "bedrock-agentcore" | "azure-ai-agent" | "vertex-ai" | "custom"
    region: str = ""  # "us-east-1" | "eastus" | "us-central1"
    account_id: str = ""  # provider-specific account/project/subscription
    resource_id: str = ""  # ARN, Azure resource URI, GCP resource name


class EndpointInfo(BaseModel):
    """How to call this agent. The operator provides this after deployment."""

    url: str
    protocol: str = "http"  # "http" | "grpc" | "a2a" | "mcp"
    auth_type: str = "none"  # "none" | "api_key" | "oauth2" | "iam_role" | "managed_identity"
    auth_config: dict[str, str] = Field(default_factory=dict)
    health_check_path: str = "/health"


# ── What the agent can do (A2A-compatible) ────────────────


class AgentSkill(BaseModel):
    """A2A-compatible skill descriptor."""

    id: str
    name: str
    description: str
    input_modes: list[str] = Field(default_factory=lambda: ["text"])
    output_modes: list[str] = Field(default_factory=lambda: ["text"])
    tags: list[str] = Field(default_factory=list)


# ── What the agent needs ──────────────────────────────────


class DependencyInfo(BaseModel):
    """Declared dependencies — what this agent needs to function."""

    required_agents: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_mcp_servers: list[str] = Field(default_factory=list)
    external_apis: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)  # "claude-sonnet-4-20250514", "gpt-4o"


# ── Compliance & trust (for governance review) ────────────


class ComplianceInfo(BaseModel):
    """Compliance metadata. Reviewers use this to approve/reject."""

    data_residency: list[str] = Field(default_factory=list)  # ["us", "eu", "ap"]
    certifications: list[str] = Field(default_factory=list)  # ["soc2", "hipaa", "gdpr"]
    data_classification: str = "internal"  # "public" | "internal" | "confidential" | "restricted"
    pii_handling: bool = False
    model_card_url: str = ""
    responsible_ai_review: bool = False


# ── Routing ───────────────────────────────────────────────


class RoutingRule(BaseModel):
    """Defines when this agent should be selected during discovery."""

    phase: str | None = None
    capability: str | None = None
    priority: int = 0
    condition: str | None = None


# ── Core Agent Record ─────────────────────────────────────


class AgentRecord(BaseModel):
    """Core agent metadata — the 'passport' an operator submits to Harbor.

    Required at registration: agent_id, name, tenant_id, owner, runtime.
    Everything else has sensible defaults for a low onboarding barrier.
    """

    # ── Identity (required) ───────────────────────────────
    agent_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"

    # ── Multi-tenant (required) ───────────────────────────
    tenant_id: str
    owner: OwnerInfo
    visibility: Visibility = Visibility.PRIVATE
    lifecycle_status: AgentLifecycle = AgentLifecycle.DRAFT

    # ── Origin & connectivity (operator-provided) ─────────
    runtime: RuntimeOrigin = Field(default_factory=RuntimeOrigin)
    endpoint: EndpointInfo | None = None

    # ── Capabilities (A2A Agent Card fields) ──────────────
    skills: list[AgentSkill] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    auth_schemes: list[dict[str, Any]] = Field(default_factory=list)

    # ── Dependencies & compliance ─────────────────────────
    dependencies: DependencyInfo = Field(default_factory=DependencyInfo)
    compliance: ComplianceInfo = Field(default_factory=ComplianceInfo)

    # ── APIM extensions ───────────────────────────────────
    phase_affinity: list[str] = Field(default_factory=list)
    routing_rules: list[RoutingRule] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)

    # ── Runtime config (operator-declared) ────────────────
    model_id: str | None = None
    max_concurrency: int = 1
    timeout_seconds: int = 600
    retry_policy: dict[str, Any] = Field(
        default_factory=lambda: {"max_retries": 3, "backoff": "exponential"}
    )

    # ── Governance ────────────────────────────────────────
    sunset_date: datetime | None = None

    # ── Timestamps (Harbor-managed) ───────────────────────
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"


# ── Version Snapshot ──────────────────────────────────────


class AgentVersion(BaseModel):
    """Immutable snapshot of an agent at a specific version."""

    agent_id: str
    tenant_id: str
    version: str
    snapshot: dict[str, Any]
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
    action: str
    actor: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = Field(default_factory=dict)

"""Agent data models — aligned with A2A Agent Card schema + APIM extensions."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"


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
    condition: str | None = None  # CEL expression for advanced routing


class AgentRecord(BaseModel):
    """
    Core agent metadata — the 'API definition' in APIM terms.

    Combines A2A Agent Card fields (name, description, skills, url, auth)
    with platform management fields (status, version, routing, runtime config).
    """

    # Identity
    agent_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    status: AgentStatus = AgentStatus.ACTIVE

    # A2A Agent Card fields
    url: str | None = None  # AgentCore runtime endpoint
    skills: list[AgentSkill] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    auth_schemes: list[dict[str, Any]] = Field(default_factory=list)

    # APIM extensions — platform management
    phase_affinity: list[str] = Field(default_factory=list)
    routing_rules: list[RoutingRule] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)

    # Runtime config — user-tunable
    model_id: str | None = None
    max_concurrency: int = 1
    timeout_seconds: int = 600
    retry_policy: dict[str, Any] = Field(
        default_factory=lambda: {"max_retries": 3, "backoff": "exponential"}
    )

    # Audit
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"

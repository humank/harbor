"""Registry service — agent lifecycle governance."""

from datetime import datetime, timezone

import structlog

from harbor.events.emitter import EventEmitter
from harbor.exceptions import (
    AgentNotFoundError,
    DuplicateAgentError,
    InvalidLifecycleTransitionError,
)
from harbor.models.agent import AgentLifecycle, AgentRecord, AgentVersion, AuditEntry
from harbor.store.agent_store import AgentStore
from harbor.store.audit_store import AuditStore
from harbor.store.version_store import VersionStore

logger = structlog.get_logger(__name__)

TRANSITIONS: dict[AgentLifecycle, set[AgentLifecycle]] = {
    AgentLifecycle.DRAFT: {AgentLifecycle.SUBMITTED},
    AgentLifecycle.SUBMITTED: {AgentLifecycle.IN_REVIEW, AgentLifecycle.DRAFT},
    AgentLifecycle.IN_REVIEW: {AgentLifecycle.APPROVED, AgentLifecycle.DRAFT},
    AgentLifecycle.APPROVED: {AgentLifecycle.PUBLISHED, AgentLifecycle.DRAFT},
    AgentLifecycle.PUBLISHED: {AgentLifecycle.SUSPENDED, AgentLifecycle.DEPRECATED},
    AgentLifecycle.SUSPENDED: {AgentLifecycle.PUBLISHED, AgentLifecycle.DEPRECATED},
    AgentLifecycle.DEPRECATED: {AgentLifecycle.RETIRED, AgentLifecycle.PUBLISHED},
    AgentLifecycle.RETIRED: set(),
}


class RegistryService:
    """Agent registration and lifecycle management."""

    def __init__(
        self,
        agent_store: AgentStore,
        audit_store: AuditStore,
        version_store: VersionStore,
        events: EventEmitter,
    ) -> None:
        self.agent_store = agent_store
        self.audit_store = audit_store
        self.version_store = version_store
        self.events = events

    def register(self, record: AgentRecord) -> AgentRecord:
        """Register a new agent (always starts as draft)."""
        existing = self.agent_store.get_agent(record.tenant_id, record.agent_id)
        if existing:
            raise DuplicateAgentError(record.agent_id)
        record.lifecycle_status = AgentLifecycle.DRAFT
        self.agent_store.put_agent(record)
        self._audit(record, "registered", actor=record.created_by)
        logger.info("agent_registered", agent_id=record.agent_id, tenant_id=record.tenant_id)
        return record

    def get(self, tenant_id: str, agent_id: str) -> AgentRecord:
        """Get agent or raise."""
        record = self.agent_store.get_agent(tenant_id, agent_id)
        if not record:
            raise AgentNotFoundError(agent_id)
        return record

    def update_config(
        self, tenant_id: str, agent_id: str, updates: dict[str, object]
    ) -> AgentRecord:
        """Update mutable agent fields (not lifecycle)."""
        record = self.get(tenant_id, agent_id)
        updates.pop("lifecycle_status", None)
        merged = record.model_copy(update=updates)
        self.agent_store.put_agent(merged)
        self._audit(merged, "config_updated", actor="system")
        return merged

    def deregister(self, tenant_id: str, agent_id: str, actor: str = "system") -> None:
        """Delete an agent."""
        record = self.get(tenant_id, agent_id)
        self.agent_store.delete_agent(tenant_id, agent_id)
        self._audit(record, "deregistered", actor=actor)

    # ── Lifecycle transitions ─────────────────────────────

    def transition(
        self,
        tenant_id: str,
        agent_id: str,
        target: AgentLifecycle,
        actor: str = "system",
        reason: str = "",
        sunset_date: datetime | None = None,
    ) -> AgentRecord:
        """Transition agent to a new lifecycle state."""
        record = self.get(tenant_id, agent_id)
        current = record.lifecycle_status

        if target not in TRANSITIONS.get(current, set()):
            raise InvalidLifecycleTransitionError(current.value, target.value)

        updates: dict[str, object] = {"lifecycle_status": target}
        if target == AgentLifecycle.DEPRECATED and sunset_date:
            updates["sunset_date"] = sunset_date

        merged = record.model_copy(update=updates)
        self.agent_store.put_agent(merged)
        self._audit(
            merged, "lifecycle_changed", actor=actor,
            details={"from": current.value, "to": target.value, "reason": reason},
        )
        logger.info(
            "lifecycle_changed", agent_id=agent_id, tenant_id=tenant_id,
            from_state=current.value, to_state=target.value,
        )
        self.events.lifecycle_changed(tenant_id, agent_id, current.value, target.value, actor)
        return merged

    def approve(
        self, tenant_id: str, agent_id: str, actor: str = "system", reason: str = ""
    ) -> AgentRecord:
        """Approve agent (in_review → approved)."""
        return self.transition(tenant_id, agent_id, AgentLifecycle.APPROVED, actor, reason)

    def reject(
        self, tenant_id: str, agent_id: str, actor: str = "system", reason: str = ""
    ) -> AgentRecord:
        """Reject agent (in_review → draft)."""
        return self.transition(tenant_id, agent_id, AgentLifecycle.DRAFT, actor, reason)

    # ── Version management ────────────────────────────────

    def create_version(self, tenant_id: str, agent_id: str, actor: str = "system") -> AgentVersion:
        """Snapshot current agent state as a new version."""
        record = self.get(tenant_id, agent_id)
        version = AgentVersion(
            agent_id=agent_id, tenant_id=tenant_id, version=record.version,
            snapshot=record.model_dump(mode="json"), created_by=actor,
        )
        self.version_store.put_version(version)
        self._audit(record, "version_created", actor=actor, details={"version": record.version})
        return version

    def list_versions(self, tenant_id: str, agent_id: str) -> list[AgentVersion]:
        """List all version snapshots."""
        return self.version_store.list_versions(tenant_id, agent_id)

    def list_agents(
        self, tenant_id: str, lifecycle: AgentLifecycle | None = None,
        limit: int = 50, cursor: str | None = None,
    ) -> tuple[list[AgentRecord], str | None]:
        """List agents for a tenant."""
        return self.agent_store.list_by_tenant(tenant_id, lifecycle, limit, cursor)

    # ── Internal ──────────────────────────────────────────

    def _audit(
        self, record: AgentRecord, action: str, actor: str,
        details: dict[str, object] | None = None,
    ) -> None:
        entry = AuditEntry(
            agent_id=record.agent_id, tenant_id=record.tenant_id,
            action=action, actor=actor, timestamp=datetime.now(timezone.utc),
            details=details or {},
        )
        self.audit_store.put_audit(entry)

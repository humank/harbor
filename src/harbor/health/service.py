"""Health monitoring service."""

from datetime import datetime, timezone

import structlog

from harbor.models.agent import HealthState, HealthStatus
from harbor.store.dynamo import AgentStore

logger = structlog.get_logger(__name__)

STALE_THRESHOLD_SECONDS = 300  # 5 minutes


class HealthService:
    """Agent health tracking and heartbeat processing."""

    def __init__(self, store: AgentStore) -> None:
        self.store = store

    def heartbeat(self, tenant_id: str, agent_id: str) -> HealthStatus:
        """Record a heartbeat from an agent."""
        now = datetime.now(timezone.utc)
        health = HealthStatus(
            agent_id=agent_id,
            tenant_id=tenant_id,
            state=HealthState.HEALTHY,
            last_seen=now,
            consecutive_failures=0,
            updated_at=now,
        )
        self.store.put_health(health)
        logger.info("heartbeat_received", agent_id=agent_id, tenant_id=tenant_id)
        return health

    def report_failure(
        self, tenant_id: str, agent_id: str, error_message: str = ""
    ) -> HealthStatus:
        """Record a failure for an agent."""
        existing = self.store.get_health(tenant_id, agent_id)
        failures = (existing.consecutive_failures + 1) if existing else 1
        now = datetime.now(timezone.utc)
        health = HealthStatus(
            agent_id=agent_id,
            tenant_id=tenant_id,
            state=HealthState.UNHEALTHY,
            last_seen=existing.last_seen if existing else None,
            consecutive_failures=failures,
            error_message=error_message,
            updated_at=now,
        )
        self.store.put_health(health)
        logger.warning("agent_failure", agent_id=agent_id, failures=failures)
        return health

    def get_status(self, tenant_id: str, agent_id: str) -> HealthStatus:
        """Get current health status, checking for staleness."""
        health = self.store.get_health(tenant_id, agent_id)
        if not health:
            return HealthStatus(agent_id=agent_id, tenant_id=tenant_id, state=HealthState.UNKNOWN)
        # Check staleness
        if health.last_seen:
            elapsed = (datetime.now(timezone.utc) - health.last_seen).total_seconds()
            if elapsed > STALE_THRESHOLD_SECONDS and health.state == HealthState.HEALTHY:
                health.state = HealthState.UNHEALTHY
                health.error_message = "stale — no heartbeat"
                self.store.put_health(health)
        return health

    def summary(self, tenant_id: str) -> dict[str, int]:
        """Get health summary for a tenant. Scans agents and checks health."""
        agents, _ = self.store.list_by_tenant(tenant_id, limit=1000)
        counts = {"total": 0, "healthy": 0, "unhealthy": 0, "unknown": 0}
        for agent in agents:
            counts["total"] += 1
            health = self.store.get_health(tenant_id, agent.agent_id)
            state = health.state.value if health else "unknown"
            counts[state] = counts.get(state, 0) + 1
        return counts

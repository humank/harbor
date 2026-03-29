"""Health store — agent health status persistence."""

from harbor.models.agent import HealthStatus
from harbor.store.base import BaseStore


class HealthStore(BaseStore):
    """Read/write agent health status."""

    def put_health(self, health: HealthStatus) -> None:
        """Update agent health status."""
        self.table.put_item(
            Item={
                "pk": self._agent_pk(health.tenant_id, health.agent_id),
                "sk": "HEALTH",
                **health.model_dump(mode="json"),
            }
        )

    def get_health(self, tenant_id: str, agent_id: str) -> HealthStatus | None:
        """Get agent health status."""
        resp = self.table.get_item(Key={"pk": self._agent_pk(tenant_id, agent_id), "sk": "HEALTH"})
        item = resp.get("Item")
        return HealthStatus(**item) if item else None

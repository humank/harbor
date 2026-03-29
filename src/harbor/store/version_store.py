"""Version store — immutable agent version snapshots."""

from harbor.models.agent import AgentVersion
from harbor.store.base import BaseStore


class VersionStore(BaseStore):
    """Read/write agent version snapshots."""

    def put_version(self, version: AgentVersion) -> None:
        """Store an immutable version snapshot."""
        self.table.put_item(
            Item={
                "pk": self._agent_pk(version.tenant_id, version.agent_id),
                "sk": f"VER#{version.version}",
                **version.model_dump(mode="json"),
            }
        )

    def list_versions(self, tenant_id: str, agent_id: str) -> list[AgentVersion]:
        """List all versions for an agent."""
        resp = self.table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={
                ":pk": self._agent_pk(tenant_id, agent_id),
                ":prefix": "VER#",
            },
        )
        return [AgentVersion(**item) for item in resp.get("Items", [])]

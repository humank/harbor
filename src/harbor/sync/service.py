"""A2A Agent Card sync service."""

from typing import Any

import structlog

from harbor.models.agent import AgentRecord, AgentSkill, EndpointInfo, OwnerInfo
from harbor.store.agent_store import AgentStore

logger = structlog.get_logger(__name__)


class SyncService:
    """Import and sync agents from A2A Agent Card endpoints."""

    def __init__(self, store: AgentStore) -> None:
        self.store = store

    async def import_from_url(self, url: str, tenant_id: str, owner: OwnerInfo) -> AgentRecord:
        """Fetch an A2A Agent Card from a URL and create/update the agent."""
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            card_url = url.rstrip("/") + "/.well-known/agent-card.json"
            resp = await client.get(card_url)
            resp.raise_for_status()
            card: dict[str, Any] = resp.json()

        return self._map_card_to_record(card, tenant_id, owner, url)

    def _map_card_to_record(
        self,
        card: dict[str, Any],
        tenant_id: str,
        owner: OwnerInfo,
        url: str,
    ) -> AgentRecord:
        """Map A2A Agent Card JSON to AgentRecord and store it."""
        raw_skills: list[dict[str, Any]] = card.get("skills") or []
        skills = [
            AgentSkill(
                id=s.get("id", s.get("name", "")),
                name=s.get("name", ""),
                description=s.get("description", ""),
                tags=s.get("tags", []),
            )
            for s in raw_skills
        ]
        capabilities = [s.id for s in skills]

        record = AgentRecord(
            agent_id=str(card.get("name", "unknown")).lower().replace(" ", "-"),
            name=str(card.get("name", "Unknown Agent")),
            description=str(card.get("description", "")),
            version=str(card.get("version", "1.0.0")),
            tenant_id=tenant_id,
            owner=owner,
            endpoint=EndpointInfo(url=url, protocol="a2a"),
            skills=skills,
            capabilities=capabilities,
        )
        self.store.put_agent(record)
        logger.info("a2a_imported", agent_id=record.agent_id, url=url)
        return record

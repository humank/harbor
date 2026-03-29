"""Harbor API client — discover agents and check policies.

This is the ONLY place that talks to Harbor API.
Agents use this to find each other at runtime, not hardcoded URLs.
"""

import os
import time

import httpx

from config import AGENT_URLS

HARBOR_URL = os.getenv("HARBOR_URL", "http://localhost:8100/api/v1")
HARBOR_TENANT = os.getenv("HARBOR_TENANT", "demo-tenant")


class HarborClient:
    """Harbor API client with discovery caching and policy enforcement."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=HARBOR_URL, timeout=10,
            headers={"X-Tenant-Id": HARBOR_TENANT},
        )
        # Cache: capability → (url, expire_time)
        self._cache: dict[str, tuple[str, float]] = {}
        self._cache_ttl = 60  # seconds

    async def discover(self, capability: str) -> str | None:
        """Discover an agent by capability via Harbor.

        Flow:
          1. Check local cache (TTL-based)
          2. Call Harbor GET /discover/capability/{cap}
          3. Harbor returns only PUBLISHED agents
          4. Fallback to static URL if Harbor is unreachable
        """
        # 1. Cache hit
        cached = self._cache.get(capability)
        if cached and cached[1] > time.time():
            return cached[0]

        # 2. Ask Harbor
        url = await self._discover_from_harbor(capability)
        if url:
            self._cache[capability] = (url, time.time() + self._cache_ttl)
            return url

        # 3. Fallback to static config
        fallback = AGENT_URLS.get(self._capability_to_agent_key(capability))
        if fallback:
            return fallback
        return None

    async def check_policy(self, from_agent: str, to_agent: str) -> bool:
        """Check if from_agent is allowed to call to_agent via Harbor policy.

        Returns True if allowed, False if denied.
        Falls back to allow if Harbor is unreachable (demo mode).
        """
        try:
            resp = await self._http.post(
                "/policies/evaluate",
                json={"from_agent": from_agent, "to_agent": to_agent},
            )
            if resp.status_code == 200:
                return resp.json().get("allowed", True)
        except httpx.ConnectError:
            pass
        return True

    async def get_all_agent_status(self) -> list[dict]:
        """Get all registered agents from Harbor."""
        try:
            resp = await self._http.get("/agents")
            if resp.status_code == 200:
                return resp.json().get("items", [])
        except httpx.ConnectError:
            pass
        return []

    def invalidate_cache(self, capability: str | None = None) -> None:
        """Invalidate discovery cache. Called when Harbor notifies of changes."""
        if capability:
            self._cache.pop(capability, None)
        else:
            self._cache.clear()

    async def _discover_from_harbor(self, capability: str) -> str | None:
        try:
            resp = await self._http.get(f"/discover/capability/{capability}")
            if resp.status_code == 200:
                data = resp.json()
                agents = data.get("items") or data.get("agents", [])
                if agents:
                    agent = agents[0]
                    ep = agent.get("endpoint") or {}
                    return ep.get("url")
        except httpx.ConnectError:
            pass
        return None

    @staticmethod
    def _capability_to_agent_key(capability: str) -> str:
        """Map capability name to AGENT_URLS key for fallback."""
        mapping = {
            "product_search": "product_catalog",
            "product_comparison": "product_catalog",
            "risk_assessment": "underwriting_risk",
            "risk_scoring": "underwriting_risk",
            "premium_calculation": "premium_calculator",
            "quote_generation": "premium_calculator",
            "kyc_check": "compliance_check",
            "regulatory_compliance": "compliance_check",
            "term_explanation": "explanation",
            "faq": "explanation",
        }
        return mapping.get(capability, capability)

    async def close(self) -> None:
        await self._http.aclose()


# Singleton instance
harbor = HarborClient()

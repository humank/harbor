"""API route tests using httpx TestClient with moto DynamoDB."""

import pytest
from httpx import ASGITransport, AsyncClient
from moto import mock_aws

from harbor.api.deps import Services
from harbor.api.routes import create_app
from harbor.store.agent_store import AgentStore
from harbor.store.audit_store import AuditStore
from harbor.store.health_store import HealthStore
from harbor.store.policy_store import PolicyStore
from harbor.store.version_store import VersionStore
from tests.unit.conftest import TABLE_NAME, _create_table


@pytest.fixture
def app():
    with mock_aws():
        _create_table(TABLE_NAME)
        kwargs = {"table_name": TABLE_NAME, "region": "us-east-1"}
        svc = Services(
            agent_store=AgentStore(**kwargs),
            audit_store=AuditStore(**kwargs),
            health_store=HealthStore(**kwargs),
            policy_store=PolicyStore(**kwargs),
            version_store=VersionStore(**kwargs),
        )
        yield create_app(svc)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


AGENT_BODY = {
    "agent_id": "test-agent",
    "name": "Test Agent",
    "tenant_id": "dev-tenant-000000000000",
    "owner": {"owner_id": "u1", "team": "eng", "org_id": "org1"},
    "capabilities": ["nlp"],
    "phase_affinity": ["discovery"],
}


@pytest.mark.anyio
async def test_register_agent(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/agents", json=AGENT_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "test-agent"
    assert data["lifecycle_status"] == "draft"


@pytest.mark.anyio
async def test_list_agents(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


@pytest.mark.anyio
async def test_get_agent(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.get("/api/v1/agents/test-agent")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Agent"


@pytest.mark.anyio
async def test_get_agent_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/agents/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_agent(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.patch("/api/v1/agents/test-agent", json={"description": "updated"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "updated"


@pytest.mark.anyio
async def test_delete_agent(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.delete("/api/v1/agents/test-agent")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == "test-agent"
    resp2 = await client.get("/api/v1/agents/test-agent")
    assert resp2.status_code == 404


@pytest.mark.anyio
async def test_delete_not_found(client: AsyncClient) -> None:
    resp = await client.delete("/api/v1/agents/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_lifecycle_transition(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.put("/api/v1/agents/test-agent/lifecycle?target=submitted")
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "submitted"


@pytest.mark.anyio
async def test_lifecycle_invalid(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.put("/api/v1/agents/test-agent/lifecycle?target=published")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_heartbeat(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.put("/api/v1/agents/test-agent/health")
    assert resp.status_code == 200
    assert resp.json()["state"] == "healthy"


@pytest.mark.anyio
async def test_health_summary(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health/summary")
    assert resp.status_code == 200
    assert "total" in resp.json()


@pytest.mark.anyio
async def test_audit_log(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.get("/api/v1/agents/test-agent/audit")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.anyio
async def test_tenant_audit(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.get("/api/v1/audit")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_discover_capability(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/discover/capability/nlp")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_discover_resolve(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/discover/resolve?capability=nlp")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_register_duplicate(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.post("/api/v1/agents", json=AGENT_BODY)
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_health_check(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_create_version(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    resp = await client.post("/api/v1/agents/test-agent/versions")
    assert resp.status_code == 200
    assert resp.json()["version"] == "1.0.0"


@pytest.mark.anyio
async def test_list_versions(client: AsyncClient) -> None:
    await client.post("/api/v1/agents", json=AGENT_BODY)
    await client.post("/api/v1/agents/test-agent/versions")
    resp = await client.get("/api/v1/agents/test-agent/versions")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

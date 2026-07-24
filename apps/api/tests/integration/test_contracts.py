"""Integration tests for contract endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app():
    from app.main import app
    return app


async def get_token(client):
    r = await client.post("/api/v1/auth/dev-token")
    return r.json()["access_token"]


async def test_list_contracts(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.get("/api/v1/contracts/",
            headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "contracts" in data
    assert "total" in data
    assert isinstance(data["contracts"], list)


async def test_list_contracts_pagination(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.get("/api/v1/contracts/?page=1&page_size=5",
            headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["page"] == 1
    assert data["page_size"] == 5


async def test_list_contracts_unauthorized(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/contracts/")
    assert r.status_code == 401


async def test_get_contract_not_found(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.get(
            "/api/v1/contracts/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"}
        )
    assert r.status_code == 404

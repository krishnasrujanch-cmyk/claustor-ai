"""Integration tests for analytics endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app():
    from app.main import app
    return app


async def get_token(client):
    r = await client.post("/api/v1/auth/dev-token")
    return r.json()["access_token"]


async def test_overview(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.get("/api/v1/analytics/overview",
            headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "contracts" in data
    assert "risk" in data
    assert "value" in data


async def test_risk_heatmap(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.get("/api/v1/analytics/risk-heatmap",
            headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "matrix" in data
    assert "clause_types" in data


async def test_export_csv(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.get("/api/v1/analytics/export?format=csv",
            headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


async def test_export_json(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.get("/api/v1/analytics/export?format=json",
            headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)

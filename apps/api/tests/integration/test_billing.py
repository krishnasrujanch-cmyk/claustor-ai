import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
def app():
    from app.main import app
    return app

async def get_token(client):
    r = await client.post("/api/v1/auth/dev-token")
    return r.json()["access_token"]

async def test_get_plans_public(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/billing/plans")
    assert r.status_code == 200
    plan_ids = [p["id"] for p in r.json()["plans"]]
    assert "free" in plan_ids
    assert "starter" in plan_ids

async def test_get_usage_authenticated(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.get("/api/v1/billing/usage", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "plan" in r.json()

async def test_subscribe_invalid_plan(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.post("/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan": "invalid_plan"})
    assert r.status_code == 400

async def test_subscribe_free_plan_rejected(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await get_token(c)
        r = await c.post("/api/v1/billing/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan": "free"})
    assert r.status_code == 400

import pytest
from httpx import ASGITransport, AsyncClient

from common.db import models as db
from master_orchestrator import app as orchestrator_app
from master_orchestrator.governor import governor

TEST_API_KEY = "test-orchestrator-key"
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


@pytest.fixture(autouse=True)
def _reset_governor():
    """The governor is a module-level singleton — clear it between tests
    so one test's acquired slots don't leak into the next."""
    governor._active.clear()
    yield
    governor._active.clear()


@pytest.fixture
async def app_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_KEY", TEST_API_KEY)
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    monkeypatch.setattr(orchestrator_app, "DB_PATH", db_path)
    return db_path


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=orchestrator_app.app), base_url="http://test", headers=AUTH_HEADERS)


async def test_missing_api_key_is_rejected(app_db):
    async with AsyncClient(transport=ASGITransport(app=orchestrator_app.app), base_url="http://test") as client:
        resp = await client.get("/orchestrator/health")
    assert resp.status_code == 401


async def test_acquire_and_release_slot_roundtrip(app_db):
    governor.max_slots = 5
    async with await _client() as client:
        acquire_resp = await client.post("/orchestrator/slots/acquire", json={"channel_id": "channel-001"})
        assert acquire_resp.status_code == 200
        acquire_data = acquire_resp.json()
        assert acquire_data["granted"] is True
        slot_id = acquire_data["slot_id"]

        release_resp = await client.post("/orchestrator/slots/release", json={"slot_id": slot_id})
        assert release_resp.status_code == 200
        assert release_resp.json()["released"] is True


async def test_acquire_denied_when_slots_full(app_db):
    governor.max_slots = 1
    async with await _client() as client:
        first = await client.post("/orchestrator/slots/acquire", json={"channel_id": "channel-001"})
        assert first.json()["granted"] is True

        second = await client.post("/orchestrator/slots/acquire", json={"channel_id": "channel-002"})
        assert second.json()["granted"] is False
        assert second.json()["slot_id"] is None


async def test_release_unknown_slot_reports_not_released(app_db):
    async with await _client() as client:
        resp = await client.post("/orchestrator/slots/release", json={"slot_id": "does-not-exist"})
    assert resp.json()["released"] is False


async def test_orchestrator_health_reflects_live_governor_state(app_db):
    governor.max_slots = 3
    async with await _client() as client:
        await client.post("/orchestrator/slots/acquire", json={"channel_id": "channel-001"})
        resp = await client.get("/orchestrator/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["active_slots"] == 1
    assert data["max_slots"] == 3
    assert data["active_channels"] == ["channel-001"]

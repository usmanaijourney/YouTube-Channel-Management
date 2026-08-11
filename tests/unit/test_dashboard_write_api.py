import pytest
from httpx import ASGITransport, AsyncClient

from common.db import models as db
from dashboard.api import app as dashboard_app

TEST_API_KEY = "test-write-key"
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


@pytest.fixture
async def seeded_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_KEY", TEST_API_KEY)
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    monkeypatch.setattr(dashboard_app, "DB_PATH", db_path)

    async with db.connect(db_path) as conn:
        await db.upsert_channel(conn, "channel-001", "Test", "testing", "active",
                                 {"videos_per_day": 1})
        await db.upsert_schedule_config(conn, "channel-001", enabled=True, preferred_hours_utc=[9])
        await db.create_task(conn, "task_abc", "channel-001", "TOPIC_EVALUATION")
        await db.request_approval(conn, "task_abc", "channel-001", "topic", {"title": "A topic"})
    return db_path


async def _client(headers: dict[str, str] = AUTH_HEADERS) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=dashboard_app.app), base_url="http://test",
                       headers=headers)


async def test_write_endpoints_require_the_api_key(seeded_db):
    async with await _client(headers={}) as client:
        resp = await client.post("/api/approvals/task_abc/topic", json={"decision": "approved"})
    assert resp.status_code == 401


async def test_pending_approvals_are_listed(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/approvals", params={"status": "pending"})
    assert resp.status_code == 200
    approvals = resp.json()
    assert len(approvals) == 1
    assert approvals[0]["stage"] == "topic"
    assert approvals[0]["payload"] == {"title": "A topic"}


async def test_approving_a_gate_records_the_decision_and_an_audit_entry(seeded_db):
    async with await _client() as client:
        resp = await client.post("/api/approvals/task_abc/topic",
                                  json={"decision": "approved", "note": "good angle"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        logs = (await client.get("/api/audit-logs")).json()

    assert logs[0]["action"] == "approval.approved"
    assert logs[0]["resource_id"] == "task_abc"
    assert logs[0]["details"]["note"] == "good angle"


async def test_deciding_twice_conflicts(seeded_db):
    async with await _client() as client:
        assert (await client.post("/api/approvals/task_abc/topic",
                                   json={"decision": "approved"})).status_code == 200
        second = await client.post("/api/approvals/task_abc/topic", json={"decision": "rejected"})

    assert second.status_code == 409
    assert "already approved" in second.json()["detail"]


async def test_unknown_gate_is_404(seeded_db):
    async with await _client() as client:
        resp = await client.post("/api/approvals/task_abc/script", json={"decision": "approved"})
    assert resp.status_code == 404


async def test_invalid_decision_is_rejected(seeded_db):
    async with await _client() as client:
        resp = await client.post("/api/approvals/task_abc/topic", json={"decision": "maybe"})
    assert resp.status_code == 422


async def test_pausing_and_resuming_a_schedule(seeded_db):
    async with await _client() as client:
        resp = await client.post("/api/channels/channel-001/schedule", json={"enabled": False})
        assert resp.status_code == 200

        schedules = (await client.get("/api/schedules")).json()
        assert schedules[0]["enabled"] is False
        # A paused schedule must not advertise a next run, or the dashboard
        # would show a time that nothing is going to act on.
        assert schedules[0]["next_run_estimate"] is None

        assert (await client.post("/api/channels/channel-001/schedule",
                                   json={"enabled": True})).status_code == 200
        assert (await client.get("/api/schedules")).json()[0]["enabled"] is True

        actions = [log["action"] for log in (await client.get("/api/audit-logs")).json()]

    assert actions == ["schedule.resumed", "schedule.paused"]


async def test_pausing_an_unknown_channel_is_404(seeded_db):
    async with await _client() as client:
        resp = await client.post("/api/channels/nope/schedule", json={"enabled": False})
    assert resp.status_code == 404

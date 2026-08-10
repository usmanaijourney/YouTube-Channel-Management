import pytest
from httpx import ASGITransport, AsyncClient

from common.db import models as db
from dashboard.api import app as dashboard_app

TEST_API_KEY = "test-dashboard-key"
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


@pytest.fixture
async def seeded_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_KEY", TEST_API_KEY)

    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    monkeypatch.setattr(dashboard_app, "DB_PATH", db_path)

    async with db.connect(db_path) as conn:
        await db.upsert_channel(conn, "channel-001", "Test Channel", "testing", "active",
                                 {"videos_per_day": 2})

        await db.create_task(conn, "task_abc", "channel-001", "CREATED")
        await db.update_task_state(conn, "task_abc", "TOPIC_RESEARCH", agent_id="topic_generator-1")
        await db.update_task_state(conn, "task_abc", "CLOSED", agent_id="whatsapp_notifier")

        await db.upsert_agent_status(conn, "script_writer-channel-001", "channel-001",
                                      "script_writer", "idle", success=True)

        await db.insert_video(conn, "video_1", "task_abc", "channel-001", "yt_1",
                               "https://youtube.com/watch?v=yt_1", "Test Video", "uploaded")
        # No paid provider is wired yet, so nothing in the real pipeline writes to
        # cost_ledger — inserted directly here just to exercise the read/aggregation path.
        await conn.execute(
            "INSERT INTO cost_ledger (channel_id, task_id, provider, cost_usd) VALUES (?, ?, ?, ?)",
            ("channel-001", "task_abc", "llm", 0.05),
        )
        await conn.commit()
        await db.insert_system_event(conn, "channel-001", "task_failed", "critical",
                                      {"task_id": "task_xyz", "stage": "UPLOAD", "reason": "boom"})

        await db.upsert_schedule_config(conn, "channel-001", enabled=True, preferred_hours_utc=[9, 16])
        await db.mark_schedule_result(conn, "channel-001", "completed")

    return db_path


async def _client(headers: dict[str, str] = AUTH_HEADERS) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=dashboard_app.app), base_url="http://test", headers=headers)


async def test_missing_api_key_is_rejected(seeded_db):
    async with await _client(headers={}) as client:
        resp = await client.get("/api/system/health")
    assert resp.status_code == 401


async def test_wrong_api_key_is_rejected(seeded_db):
    async with await _client(headers={"X-API-Key": "not-the-right-key"}) as client:
        resp = await client.get("/api/system/health")
    assert resp.status_code == 401


async def test_system_health(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/system/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_channels"] == 1
    assert data["active_channels"] == 1
    assert data["tasks_completed"] == 1
    assert data["open_critical_alerts"] == 1


async def test_list_channels(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/channels")
    assert resp.status_code == 200
    channels = resp.json()
    assert len(channels) == 1
    assert channels[0]["channel_id"] == "channel-001"
    assert channels[0]["videos_uploaded"] == 1
    assert channels[0]["cost_total"] == pytest.approx(0.05)


async def test_channel_with_zero_tasks_reports_zero_not_null(seeded_db):
    """Regression test: SQLite's SUM(CASE ...) returns NULL, not 0, when a
    channel has no rows in `tasks` at all — must be COALESCE'd in the query."""
    async with db.connect(seeded_db) as conn:
        await db.upsert_channel(conn, "channel-brand-new", "Brand New Channel", "testing", "active",
                                 {"videos_per_day": 1})

    async with await _client() as client:
        resp = await client.get("/api/channels/channel-brand-new")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_task_count"] == 0
    assert data["tasks_completed"] == 0
    assert data["tasks_failed"] == 0
    assert data["videos_produced"] == 0
    assert data["videos_uploaded"] == 0


async def test_channel_detail(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/channels/channel-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel_id"] == "channel-001"
    assert len(data["agents"]) == 1
    assert data["agents"][0]["agent_type"] == "script_writer"
    assert len(data["recent_tasks"]) == 1


async def test_channel_detail_404(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/channels/does-not-exist")
    assert resp.status_code == 404


async def test_agent_detail(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/channels/channel-001/agents/script_writer")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_type"] == "script_writer"
    assert len(data["instances"]) == 1
    assert data["instances"][0]["status"] == "idle"


async def test_agent_detail_404(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/channels/channel-001/agents/nonexistent_agent")
    assert resp.status_code == 404


async def test_task_detail(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/channels/channel-001/tasks/task_abc")
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "task_abc"
    assert data["state"] == "CLOSED"
    assert len(data["events"]) == 2
    assert data["events"][-1]["to_state"] == "CLOSED"


async def test_task_detail_404(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/channels/channel-001/tasks/does-not-exist")
    assert resp.status_code == 404


async def test_alerts_unfiltered(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "critical"
    assert alerts[0]["payload"]["stage"] == "UPLOAD"


async def test_alerts_filtered_by_severity(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/alerts", params={"severity": "warning"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_schedules(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/schedules")
    assert resp.status_code == 200
    schedules = resp.json()
    assert len(schedules) == 1
    assert schedules[0]["channel_id"] == "channel-001"
    assert schedules[0]["enabled"] is True
    assert schedules[0]["preferred_hours_utc"] == [9, 16]
    assert schedules[0]["last_run_status"] == "completed"
    assert schedules[0]["next_run_estimate"] is not None


async def test_schedules_disabled_channel_has_no_next_run_estimate(seeded_db):
    async with db.connect(seeded_db) as conn:
        await db.upsert_schedule_config(conn, "channel-001", enabled=False, preferred_hours_utc=[9, 16])

    async with await _client() as client:
        resp = await client.get("/api/schedules")
    schedules = resp.json()
    assert schedules[0]["enabled"] is False
    assert schedules[0]["next_run_estimate"] is None


async def test_orchestrator_reports_honest_null_status_before_any_cycle_runs(seeded_db):
    async with await _client() as client:
        resp = await client.get("/api/orchestrator")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] is None
    # The seeded "task_failed" event isn't an orchestrator-sourced event type.
    assert data["recent_events"] == []


async def test_orchestrator_reports_real_status_and_its_own_alert_types(seeded_db):
    async with db.connect(seeded_db) as conn:
        await db.upsert_orchestrator_status(
            conn, status="online", started_at="2026-08-10T00:00:00+00:00",
            managed_channels=1, active_slots=0, max_slots=5, cycles_run=3,
        )
        await db.insert_system_event(
            conn, "channel-001", "repeated_task_failures", "critical",
            {"tasks_failed": 3, "threshold": 3},
        )

    async with await _client() as client:
        resp = await client.get("/api/orchestrator")
    data = resp.json()
    assert data["status"]["cycles_run"] == 3
    assert data["status"]["managed_channels"] == 1
    assert len(data["recent_events"]) == 1
    assert data["recent_events"][0]["event_type"] == "repeated_task_failures"


async def test_integrations_reports_healthy_error_and_mocked(seeded_db, monkeypatch):
    from dashboard.api import health_checks

    async def _ok():
        return None

    async def _fail():
        raise RuntimeError("dependency unreachable")

    monkeypatch.setattr(health_checks, "CHECKS", {"ffmpeg": _ok, "youtube_api": _fail})
    monkeypatch.setattr(health_checks, "MOCKED_SERVICES", ["whatsapp_api"])

    async with await _client() as client:
        resp = await client.get("/api/integrations")
    assert resp.status_code == 200
    by_name = {r["service_name"]: r for r in resp.json()}
    assert by_name["database"]["status"] == "healthy"
    assert by_name["ffmpeg"]["status"] == "healthy"
    assert by_name["youtube_api"]["status"] == "error"
    assert by_name["whatsapp_api"]["status"] == "mocked"

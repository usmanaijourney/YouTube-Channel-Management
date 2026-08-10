from common.db import models as db
from dashboard.api import queries
from master_orchestrator.health_aggregator import check_channel_health, run_health_cycle


async def _seed_channel_with_failures(conn, channel_id: str, failure_count: int) -> None:
    await db.upsert_channel(conn, channel_id, f"Channel {channel_id}", "testing", "active", {"videos_per_day": 1})
    for i in range(failure_count):
        task_id = f"{channel_id}-task-{i}"
        await db.create_task(conn, task_id, channel_id, "CREATED")
        await db.update_task_state(conn, task_id, "FAILED")


async def test_repeated_failures_triggers_critical_alert(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    async with db.connect(db_path) as conn:
        await _seed_channel_with_failures(conn, "channel-001", failure_count=3)
        channels = await queries.list_channels(conn)

        emitted = await check_channel_health(conn, channels[0], schedule=None)

        assert emitted == ["repeated_task_failures"]
        alerts = await queries.list_alerts(conn)
        assert alerts[0]["event_type"] == "repeated_task_failures"
        assert alerts[0]["severity"] == "critical"


async def test_below_threshold_does_not_trigger_alert(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    async with db.connect(db_path) as conn:
        await _seed_channel_with_failures(conn, "channel-001", failure_count=2)
        channels = await queries.list_channels(conn)

        emitted = await check_channel_health(conn, channels[0], schedule=None)

        assert emitted == []


async def test_stale_never_run_schedule_triggers_unresponsive_warning(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    async with db.connect(db_path) as conn:
        await db.upsert_channel(conn, "channel-001", "Test", "testing", "active", {"videos_per_day": 1})
        await db.upsert_schedule_config(conn, "channel-001", enabled=True, preferred_hours_utc=[9])
        channels = await queries.list_channels(conn)
        schedules = {s["channel_id"]: s for s in await db.list_schedules(conn)}

        emitted = await check_channel_health(conn, channels[0], schedules["channel-001"])

        assert emitted == ["channel_unresponsive"]


async def test_recently_run_schedule_does_not_trigger_unresponsive_warning(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    async with db.connect(db_path) as conn:
        await db.upsert_channel(conn, "channel-001", "Test", "testing", "active", {"videos_per_day": 1})
        await db.upsert_schedule_config(conn, "channel-001", enabled=True, preferred_hours_utc=[9])
        await db.mark_schedule_result(conn, "channel-001", "completed")
        channels = await queries.list_channels(conn)
        schedules = {s["channel_id"]: s for s in await db.list_schedules(conn)}

        emitted = await check_channel_health(conn, channels[0], schedules["channel-001"])

        assert emitted == []


async def test_disabled_schedule_never_triggers_unresponsive_warning(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    async with db.connect(db_path) as conn:
        await db.upsert_channel(conn, "channel-001", "Test", "testing", "active", {"videos_per_day": 1})
        await db.upsert_schedule_config(conn, "channel-001", enabled=False, preferred_hours_utc=[9])
        channels = await queries.list_channels(conn)
        schedules = {s["channel_id"]: s for s in await db.list_schedules(conn)}

        emitted = await check_channel_health(conn, channels[0], schedules["channel-001"])

        assert emitted == []


async def test_duplicate_alert_is_deduped_within_window(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    async with db.connect(db_path) as conn:
        await _seed_channel_with_failures(conn, "channel-001", failure_count=3)
        channels = await queries.list_channels(conn)

        first = await check_channel_health(conn, channels[0], schedule=None)
        second = await check_channel_health(conn, channels[0], schedule=None)

        assert first == ["repeated_task_failures"]
        assert second == []  # deduped, not emitted again
        alerts = await queries.list_alerts(conn)
        assert len(alerts) == 1


async def test_run_health_cycle_aggregates_across_all_channels(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    async with db.connect(db_path) as conn:
        await _seed_channel_with_failures(conn, "channel-001", failure_count=3)
        await _seed_channel_with_failures(conn, "channel-002", failure_count=0)

        result = await run_health_cycle(conn)

        assert result["channels_checked"] == 2
        assert result["alerts_emitted"] == 1

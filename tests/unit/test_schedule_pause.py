import pytest

from common.db import models as db


@pytest.fixture
async def conn(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    async with db.connect(db_path) as connection:
        await db.upsert_channel(connection, "channel-001", "Test", "testing", "active", {})
        yield connection


async def test_rerunning_the_config_does_not_undo_a_pause(conn):
    """The config file says the channel is active; the operator paused it in the
    dashboard. A later run.py invocation re-applies the config, and must not
    quietly re-enable what a human deliberately turned off."""
    await db.upsert_schedule_config(conn, "channel-001", enabled=True, preferred_hours_utc=[9])
    await db.set_schedule_enabled(conn, "channel-001", False)

    await db.upsert_schedule_config(conn, "channel-001", enabled=True, preferred_hours_utc=[9, 16])

    schedule = (await db.list_schedules(conn))[0]
    assert schedule["enabled"] is False
    # Everything else the config owns should still update.
    assert schedule["preferred_hours_utc"] == [9, 16]


async def test_first_write_honours_the_config(conn):
    await db.upsert_schedule_config(conn, "channel-001", enabled=False, preferred_hours_utc=[9])
    assert (await db.list_schedules(conn))[0]["enabled"] is False


async def test_toggling_an_unknown_channel_reports_failure(conn):
    assert await db.set_schedule_enabled(conn, "channel-999", False) is False

import asyncio

import pytest

from channel_manager.remote_approval import ApprovalTimeout, db_approval_callback
from common.db import models as db


@pytest.fixture
async def conn(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)
    async with db.connect(db_path) as connection:
        await db.upsert_channel(connection, "channel-001", "Test", "testing", "active", {})
        await db.create_task(connection, "task_abc", "channel-001", "CREATED")
        yield connection


async def test_gate_opens_as_pending_and_blocks(conn):
    callback = db_approval_callback(conn, "channel-001", poll_seconds=0)
    task = asyncio.create_task(callback("task_abc", "topic", {"title": "A topic"}))

    # Give the callback a moment to write its row, then confirm it is still waiting.
    await asyncio.sleep(0.05)
    approval = await db.get_approval(conn, "task_abc", "topic")
    assert approval["status"] == "pending"
    assert approval["payload"] == {"title": "A topic"}
    assert not task.done()

    await db.decide_approval(conn, "task_abc", "topic", "approved", decided_by="operator")
    assert await task is True


async def test_rejection_returns_false(conn):
    callback = db_approval_callback(conn, "channel-001", poll_seconds=0)
    task = asyncio.create_task(callback("task_abc", "script", {"hook": "hi"}))
    await asyncio.sleep(0.05)

    await db.decide_approval(conn, "task_abc", "script", "rejected", decided_by="operator",
                             note="off-brand")
    assert await task is False
    assert (await db.get_approval(conn, "task_abc", "script"))["note"] == "off-brand"


async def test_timeout_expires_the_gate(conn):
    callback = db_approval_callback(conn, "channel-001", poll_seconds=0, timeout_seconds=0)
    with pytest.raises(ApprovalTimeout):
        await callback("task_abc", "pre_upload", {"title": "T"})

    # Expiring it in the table matters: the gate must not still read as 'pending'
    # to an operator who opens the dashboard after the run has already given up.
    assert (await db.get_approval(conn, "task_abc", "pre_upload"))["status"] == "expired"


async def test_second_decision_is_refused(conn):
    await db.request_approval(conn, "task_abc", "channel-001", "topic", {})
    assert await db.decide_approval(conn, "task_abc", "topic", "approved", decided_by="operator")
    assert not await db.decide_approval(conn, "task_abc", "topic", "rejected", decided_by="operator")
    assert (await db.get_approval(conn, "task_abc", "topic"))["status"] == "approved"


async def test_reasking_a_gate_clears_the_old_decision(conn):
    await db.request_approval(conn, "task_abc", "channel-001", "topic", {"v": 1})
    await db.decide_approval(conn, "task_abc", "topic", "rejected", decided_by="operator")

    await db.request_approval(conn, "task_abc", "channel-001", "topic", {"v": 2})
    approval = await db.get_approval(conn, "task_abc", "topic")
    assert approval["status"] == "pending"
    assert approval["decided_at"] is None
    assert approval["payload"] == {"v": 2}

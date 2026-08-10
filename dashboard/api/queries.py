"""Read-only rollup queries backing the dashboard API (doc §14).

Direct SQL against the live tables — no materialized views yet, since at
single-channel MVP scale a direct query is fast enough. Revisit (materialized
views refreshed on an interval, per §14) once channel count actually makes
these queries slow.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import aiosqlite


def _row(row: aiosqlite.Row | None) -> Optional[dict[str, Any]]:
    return dict(row) if row is not None else None


async def system_health(conn: aiosqlite.Connection) -> dict[str, Any]:
    channel_row = _row(await (await conn.execute(
        """
        SELECT
            COUNT(*) AS total_channels,
            COALESCE(SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END), 0) AS active_channels,
            COALESCE(SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END), 0) AS channels_with_problems,
            COALESCE(SUM(CASE WHEN status = 'paused' THEN 1 ELSE 0 END), 0) AS paused_channels
        FROM channels
        """
    )).fetchone()) or {}

    task_row = _row(await (await conn.execute(
        """
        SELECT
            COUNT(*) AS total_tasks,
            COALESCE(SUM(CASE WHEN state = 'CLOSED' THEN 1 ELSE 0 END), 0) AS tasks_completed,
            COALESCE(SUM(CASE WHEN state = 'FAILED' THEN 1 ELSE 0 END), 0) AS tasks_failed,
            COALESCE(SUM(CASE WHEN state NOT IN ('CLOSED', 'FAILED') THEN 1 ELSE 0 END), 0) AS tasks_in_progress
        FROM tasks
        """
    )).fetchone()) or {}

    cost_row = _row(await (await conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) AS cost_total FROM cost_ledger"
    )).fetchone()) or {}

    alert_row = _row(await (await conn.execute(
        "SELECT COUNT(*) AS open_critical_alerts FROM system_events WHERE severity = 'critical'"
    )).fetchone()) or {}

    return {**channel_row, **task_row, **cost_row, **alert_row}


async def _channel_rollup(conn: aiosqlite.Connection, channel_id: str) -> dict[str, Any]:
    task_row = _row(await (await conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN state NOT IN ('CLOSED', 'FAILED') THEN 1 ELSE 0 END), 0) AS current_task_count,
            COALESCE(SUM(CASE WHEN state = 'CLOSED' THEN 1 ELSE 0 END), 0) AS tasks_completed,
            COALESCE(SUM(CASE WHEN state = 'FAILED' THEN 1 ELSE 0 END), 0) AS tasks_failed
        FROM tasks WHERE channel_id = ?
        """,
        (channel_id,),
    )).fetchone()) or {}

    video_row = _row(await (await conn.execute(
        """
        SELECT
            COUNT(*) AS videos_produced,
            COALESCE(SUM(CASE WHEN status = 'uploaded' THEN 1 ELSE 0 END), 0) AS videos_uploaded
        FROM videos WHERE channel_id = ?
        """,
        (channel_id,),
    )).fetchone()) or {}

    cost_row = _row(await (await conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) AS cost_total FROM cost_ledger WHERE channel_id = ?",
        (channel_id,),
    )).fetchone()) or {}

    return {**task_row, **video_row, **cost_row}


async def list_channels(conn: aiosqlite.Connection) -> list[dict[str, Any]]:
    rows = await (await conn.execute(
        "SELECT channel_id, name, niche, status, created_at, schedule_json FROM channels ORDER BY name"
    )).fetchall()

    channels = []
    for row in rows:
        channel = dict(row)
        channel["schedule"] = json.loads(channel.pop("schedule_json") or "{}")
        channel.update(await _channel_rollup(conn, channel["channel_id"]))
        channels.append(channel)
    return channels


async def get_channel(conn: aiosqlite.Connection, channel_id: str) -> Optional[dict[str, Any]]:
    row = _row(await (await conn.execute(
        "SELECT * FROM channels WHERE channel_id = ?", (channel_id,)
    )).fetchone())
    if row is None:
        return None

    channel = row
    channel["schedule"] = json.loads(channel.pop("schedule_json") or "{}")
    channel.update(await _channel_rollup(conn, channel_id))

    agent_rows = await (await conn.execute(
        "SELECT * FROM agents WHERE channel_id = ? ORDER BY agent_id", (channel_id,)
    )).fetchall()
    channel["agents"] = [dict(r) for r in agent_rows]

    task_rows = await (await conn.execute(
        """
        SELECT task_id, state, topic, created_at, updated_at FROM tasks
        WHERE channel_id = ? ORDER BY created_at DESC LIMIT 20
        """,
        (channel_id,),
    )).fetchall()
    channel["recent_tasks"] = [dict(r) for r in task_rows]

    return channel


async def get_agent_detail(conn: aiosqlite.Connection, channel_id: str,
                            agent_type: str) -> Optional[dict[str, Any]]:
    instance_rows = await (await conn.execute(
        "SELECT * FROM agents WHERE channel_id = ? AND agent_type = ? ORDER BY agent_id",
        (channel_id, agent_type),
    )).fetchall()
    if not instance_rows:
        return None

    instances = [dict(r) for r in instance_rows]
    agent_ids = [i["agent_id"] for i in instances]
    placeholders = ",".join("?" for _ in agent_ids)

    event_rows = await (await conn.execute(
        f"""
        SELECT te.* FROM task_events te
        JOIN tasks t ON t.task_id = te.task_id
        WHERE t.channel_id = ? AND te.agent_id IN ({placeholders})
        ORDER BY te.id DESC LIMIT 20
        """,
        (channel_id, *agent_ids),
    )).fetchall()

    recent_events = []
    for r in event_rows:
        event = dict(r)
        event["payload"] = json.loads(event["payload"]) if event["payload"] else None
        event["error"] = json.loads(event["error"]) if event["error"] else None
        recent_events.append(event)

    return {"channel_id": channel_id, "agent_type": agent_type, "instances": instances,
            "recent_events": recent_events}


async def get_task_detail(conn: aiosqlite.Connection, channel_id: str,
                           task_id: str) -> Optional[dict[str, Any]]:
    row = _row(await (await conn.execute(
        "SELECT * FROM tasks WHERE task_id = ? AND channel_id = ?", (task_id, channel_id)
    )).fetchone())
    if row is None:
        return None

    task = row
    task["metadata"] = json.loads(task.pop("metadata") or "{}")

    event_rows = await (await conn.execute(
        "SELECT * FROM task_events WHERE task_id = ? ORDER BY id ASC", (task_id,)
    )).fetchall()

    events = []
    for r in event_rows:
        event = dict(r)
        event["payload"] = json.loads(event["payload"]) if event["payload"] else None
        event["error"] = json.loads(event["error"]) if event["error"] else None
        events.append(event)
    task["events"] = events

    return task


async def list_alerts(conn: aiosqlite.Connection, severity: Optional[str] = None) -> list[dict[str, Any]]:
    if severity:
        rows = await (await conn.execute(
            "SELECT * FROM system_events WHERE severity = ? ORDER BY id DESC LIMIT 100", (severity,)
        )).fetchall()
    else:
        rows = await (await conn.execute(
            "SELECT * FROM system_events ORDER BY id DESC LIMIT 100"
        )).fetchall()

    alerts = []
    for r in rows:
        alert = dict(r)
        alert["payload"] = json.loads(alert["payload"]) if alert["payload"] else None
        alerts.append(alert)
    return alerts


_ORCHESTRATOR_EVENT_TYPES = ("repeated_task_failures", "channel_unresponsive")


async def get_orchestrator(conn: aiosqlite.Connection) -> dict[str, Any]:
    """Backs the Orchestrator page — honestly reports status=None if the
    Master Orchestrator service has never run a health-aggregator cycle."""
    status = _row(await (await conn.execute(
        "SELECT * FROM orchestrator_status WHERE id = 1"
    )).fetchone())

    placeholders = ",".join("?" for _ in _ORCHESTRATOR_EVENT_TYPES)
    event_rows = await (await conn.execute(
        f"SELECT * FROM system_events WHERE event_type IN ({placeholders}) ORDER BY id DESC LIMIT 20",
        _ORCHESTRATOR_EVENT_TYPES,
    )).fetchall()

    recent_events = []
    for r in event_rows:
        event = dict(r)
        event["payload"] = json.loads(event["payload"]) if event["payload"] else None
        recent_events.append(event)

    return {"status": status, "recent_events": recent_events}

"""Health Aggregator (doc §19's monitoring_loop) — a periodic pass over every
channel's real state, emitting deduped alerts for genuine problem conditions.
No LLM involved here — per doc §1 risk #7, the orchestrator is mostly a
boring control-plane loop, not a reasoning agent.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import aiosqlite

from common.db import models as db
from dashboard.api import queries

FAILURE_THRESHOLD = 3
STALE_SCHEDULE_HOURS = 48
DEDUP_WINDOW_MINUTES = 60


async def _recent_duplicate_exists(conn: aiosqlite.Connection, channel_id: str, event_type: str) -> bool:
    cursor = await conn.execute(
        """
        SELECT 1 FROM system_events
        WHERE channel_id = ? AND event_type = ?
          AND created_at >= datetime('now', ?)
        LIMIT 1
        """,
        (channel_id, event_type, f"-{DEDUP_WINDOW_MINUTES} minutes"),
    )
    return await cursor.fetchone() is not None


def _is_stale(last_run_at_str: str) -> bool:
    last_run = datetime.fromisoformat(last_run_at_str.replace(" ", "T")).replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_run > timedelta(hours=STALE_SCHEDULE_HOURS)


async def check_channel_health(conn: aiosqlite.Connection, channel: dict[str, Any],
                                schedule: Optional[dict[str, Any]]) -> list[str]:
    """Runs the real checks for one channel; returns the event_types emitted this cycle."""
    emitted: list[str] = []
    channel_id = channel["channel_id"]

    if channel["tasks_failed"] >= FAILURE_THRESHOLD:
        if not await _recent_duplicate_exists(conn, channel_id, "repeated_task_failures"):
            await db.insert_system_event(
                conn, channel_id, "repeated_task_failures", "critical",
                {"tasks_failed": channel["tasks_failed"], "threshold": FAILURE_THRESHOLD},
            )
            emitted.append("repeated_task_failures")

    if schedule and schedule["enabled"]:
        last_run_at = schedule["last_run_at"]
        stale = last_run_at is None or _is_stale(last_run_at)
        if stale and not await _recent_duplicate_exists(conn, channel_id, "channel_unresponsive"):
            await db.insert_system_event(
                conn, channel_id, "channel_unresponsive", "warning",
                {"last_run_at": last_run_at, "threshold_hours": STALE_SCHEDULE_HOURS},
            )
            emitted.append("channel_unresponsive")

    return emitted


async def run_health_cycle(conn: aiosqlite.Connection) -> dict[str, Any]:
    """One full pass over every channel — the body of doc §19's monitoring_loop."""
    channels = await queries.list_channels(conn)
    schedules = {s["channel_id"]: s for s in await db.list_schedules(conn)}

    total_alerts = 0
    for channel in channels:
        emitted = await check_channel_health(conn, channel, schedules.get(channel["channel_id"]))
        total_alerts += len(emitted)

    return {"channels_checked": len(channels), "alerts_emitted": total_alerts}

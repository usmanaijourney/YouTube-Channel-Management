from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import aiosqlite

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_MIGRATION_FILES = [
    "0001_initial.sql",
    "0002_dashboard_foundation.sql",
    "0003_orchestrator.sql",
    "0004_approvals.sql",
]

# `DB_PATH` lets a deployment point the SQLite file at a mounted volume
# (e.g. /data/youtube_orchestration.db on Railway) instead of the repo-relative
# default, which would live on an ephemeral container filesystem.
DEFAULT_DB_PATH = os.environ.get("DB_PATH", "youtube_orchestration.db")


@asynccontextmanager
async def connect(db_path: str) -> AsyncIterator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    try:
        # WAL + a busy timeout because the dashboard API and the Master
        # Orchestrator are separate processes writing the same file (they share
        # a volume in deployment); without these, a health-check write landing
        # during an orchestrator cycle can fail outright with "database is locked".
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA busy_timeout = 5000")
        await conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    finally:
        await conn.close()


async def init_db(db_path: str) -> None:
    async with connect(db_path) as conn:
        for filename in _MIGRATION_FILES:
            await conn.executescript((_MIGRATIONS_DIR / filename).read_text())
        await conn.commit()


async def upsert_channel(conn: aiosqlite.Connection, channel_id: str, name: str, niche: str,
                          status: str, schedule: dict[str, Any]) -> None:
    await conn.execute(
        """
        INSERT INTO channels (channel_id, name, niche, status, schedule_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            name=excluded.name, niche=excluded.niche, status=excluded.status,
            schedule_json=excluded.schedule_json
        """,
        (channel_id, name, niche, status, json.dumps(schedule)),
    )
    await conn.commit()


async def create_task(conn: aiosqlite.Connection, task_id: str, channel_id: str,
                       state: str, metadata: Optional[dict[str, Any]] = None) -> None:
    await conn.execute(
        "INSERT INTO tasks (task_id, channel_id, state, metadata) VALUES (?, ?, ?, ?)",
        (task_id, channel_id, state, json.dumps(metadata or {})),
    )
    await conn.commit()


async def update_task_state(conn: aiosqlite.Connection, task_id: str, to_state: str,
                             agent_id: Optional[str] = None,
                             payload: Optional[dict[str, Any]] = None,
                             error: Optional[dict[str, Any]] = None) -> None:
    row = await (await conn.execute("SELECT state FROM tasks WHERE task_id = ?", (task_id,))).fetchone()
    from_state = row["state"] if row else None

    await conn.execute(
        "UPDATE tasks SET state = ?, updated_at = datetime('now') WHERE task_id = ?",
        (to_state, task_id),
    )
    await conn.execute(
        """
        INSERT INTO task_events (task_id, from_state, to_state, agent_id, payload, error)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (task_id, from_state, to_state, agent_id,
         json.dumps(payload) if payload is not None else None,
         json.dumps(error) if error is not None else None),
    )
    await conn.commit()


async def get_task_events(conn: aiosqlite.Connection, task_id: str) -> list[dict[str, Any]]:
    cursor = await conn.execute(
        "SELECT * FROM task_events WHERE task_id = ? ORDER BY id ASC", (task_id,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def upsert_agent_status(conn: aiosqlite.Connection, agent_id: str, channel_id: str,
                               agent_type: str, status: str,
                               success: bool | None = None) -> None:
    now_expr = "datetime('now')"
    if success is True:
        await conn.execute(
            f"""
            INSERT INTO agents (agent_id, channel_id, agent_type, status, last_heartbeat, last_success, failure_count)
            VALUES (?, ?, ?, ?, {now_expr}, {now_expr}, 0)
            ON CONFLICT(agent_id) DO UPDATE SET
                status=excluded.status, last_heartbeat={now_expr}, last_success={now_expr}
            """,
            (agent_id, channel_id, agent_type, status),
        )
    elif success is False:
        await conn.execute(
            f"""
            INSERT INTO agents (agent_id, channel_id, agent_type, status, last_heartbeat, last_failure, failure_count)
            VALUES (?, ?, ?, ?, {now_expr}, {now_expr}, 1)
            ON CONFLICT(agent_id) DO UPDATE SET
                status=excluded.status, last_heartbeat={now_expr}, last_failure={now_expr},
                failure_count=failure_count + 1
            """,
            (agent_id, channel_id, agent_type, status),
        )
    else:
        await conn.execute(
            f"""
            INSERT INTO agents (agent_id, channel_id, agent_type, status, last_heartbeat)
            VALUES (?, ?, ?, ?, {now_expr})
            ON CONFLICT(agent_id) DO UPDATE SET
                status=excluded.status, last_heartbeat={now_expr}
            """,
            (agent_id, channel_id, agent_type, status),
        )
    await conn.commit()


async def insert_video(conn: aiosqlite.Connection, video_id: str, task_id: str, channel_id: str,
                        youtube_video_id: str, youtube_url: str, title: str, status: str) -> None:
    await conn.execute(
        """
        INSERT INTO videos (video_id, task_id, channel_id, youtube_video_id, youtube_url, title, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (video_id, task_id, channel_id, youtube_video_id, youtube_url, title, status),
    )
    await conn.commit()


async def insert_system_event(conn: aiosqlite.Connection, channel_id: Optional[str], event_type: str,
                                severity: str, payload: Optional[dict[str, Any]] = None) -> None:
    await conn.execute(
        "INSERT INTO system_events (channel_id, event_type, severity, payload) VALUES (?, ?, ?, ?)",
        (channel_id, event_type, severity, json.dumps(payload) if payload is not None else None),
    )
    await conn.commit()


async def record_health_check(conn: aiosqlite.Connection, service_name: str, status: str,
                               response_time_ms: Optional[int] = None, error: Optional[str] = None) -> None:
    """status: 'healthy' | 'error' | 'mocked'. error_count accumulates across calls (a running total,
    not reset on the next success) so it reflects overall reliability, not just the latest check."""
    now_expr = "datetime('now')"
    if status == "healthy":
        await conn.execute(
            f"""
            INSERT INTO system_health (service_name, status, last_check_at, last_success_at, response_time_ms, error_count, last_error)
            VALUES (?, ?, {now_expr}, {now_expr}, ?, 0, NULL)
            ON CONFLICT(service_name) DO UPDATE SET
                status=excluded.status, last_check_at={now_expr}, last_success_at={now_expr},
                response_time_ms=excluded.response_time_ms
            """,
            (service_name, status, response_time_ms),
        )
    elif status == "error":
        await conn.execute(
            f"""
            INSERT INTO system_health (service_name, status, last_check_at, response_time_ms, error_count, last_error)
            VALUES (?, ?, {now_expr}, ?, 1, ?)
            ON CONFLICT(service_name) DO UPDATE SET
                status=excluded.status, last_check_at={now_expr}, response_time_ms=excluded.response_time_ms,
                error_count=error_count + 1, last_error=excluded.last_error
            """,
            (service_name, status, response_time_ms, error),
        )
    else:
        await conn.execute(
            f"""
            INSERT INTO system_health (service_name, status, last_check_at, response_time_ms)
            VALUES (?, ?, {now_expr}, ?)
            ON CONFLICT(service_name) DO UPDATE SET
                status=excluded.status, last_check_at={now_expr}, response_time_ms=excluded.response_time_ms
            """,
            (service_name, status, response_time_ms),
        )
    await conn.commit()


async def list_health(conn: aiosqlite.Connection) -> list[dict[str, Any]]:
    rows = await (await conn.execute("SELECT * FROM system_health ORDER BY service_name")).fetchall()
    return [dict(r) for r in rows]


async def upsert_schedule_config(conn: aiosqlite.Connection, channel_id: str, enabled: bool,
                                  preferred_hours_utc: list[int]) -> None:
    """`enabled` is the initial value only. Once the row exists the operator owns
    that flag via the dashboard, so re-running with the config file must not
    silently undo a pause."""
    await conn.execute(
        """
        INSERT INTO schedules (channel_id, enabled, preferred_hours_utc, last_run_status)
        VALUES (?, ?, ?, 'idle')
        ON CONFLICT(channel_id) DO UPDATE SET
            preferred_hours_utc=excluded.preferred_hours_utc
        """,
        (channel_id, 1 if enabled else 0, json.dumps(preferred_hours_utc)),
    )
    await conn.commit()


async def mark_schedule_running(conn: aiosqlite.Connection, channel_id: str) -> None:
    await conn.execute("UPDATE schedules SET last_run_status = 'running' WHERE channel_id = ?", (channel_id,))
    await conn.commit()


async def mark_schedule_result(conn: aiosqlite.Connection, channel_id: str, status: str) -> None:
    await conn.execute(
        "UPDATE schedules SET last_run_status = ?, last_run_at = datetime('now') WHERE channel_id = ?",
        (status, channel_id),
    )
    await conn.commit()


async def list_schedules(conn: aiosqlite.Connection) -> list[dict[str, Any]]:
    rows = await (await conn.execute("SELECT * FROM schedules ORDER BY channel_id")).fetchall()
    schedules = []
    for r in rows:
        schedule = dict(r)
        schedule["enabled"] = bool(schedule["enabled"])
        schedule["preferred_hours_utc"] = (
            json.loads(schedule["preferred_hours_utc"]) if schedule["preferred_hours_utc"] else []
        )
        schedules.append(schedule)
    return schedules


async def upsert_orchestrator_status(conn: aiosqlite.Connection, status: str, started_at: Optional[str],
                                      managed_channels: int, active_slots: int, max_slots: int,
                                      cycles_run: int) -> None:
    await conn.execute(
        """
        INSERT INTO orchestrator_status
            (id, status, started_at, last_cycle_at, managed_channels, active_slots, max_slots, cycles_run)
        VALUES (1, ?, ?, datetime('now'), ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status, started_at=excluded.started_at, last_cycle_at=datetime('now'),
            managed_channels=excluded.managed_channels, active_slots=excluded.active_slots,
            max_slots=excluded.max_slots, cycles_run=excluded.cycles_run
        """,
        (status, started_at, managed_channels, active_slots, max_slots, cycles_run),
    )
    await conn.commit()


async def get_orchestrator_status(conn: aiosqlite.Connection) -> Optional[dict[str, Any]]:
    row = await (await conn.execute("SELECT * FROM orchestrator_status WHERE id = 1")).fetchone()
    return dict(row) if row else None


def _approval_row(row: aiosqlite.Row) -> dict[str, Any]:
    approval = dict(row)
    approval["payload"] = json.loads(approval.pop("payload_json"))
    return approval


async def request_approval(conn: aiosqlite.Connection, task_id: str, channel_id: str,
                            stage: str, payload: dict[str, Any]) -> None:
    """Opens a gate. Re-asking the same gate replaces the previous request, so a
    task re-run after a rejection isn't blocked by its own stale decision."""
    await conn.execute(
        """
        INSERT INTO approvals (task_id, channel_id, stage, status, payload_json)
        VALUES (?, ?, ?, 'pending', ?)
        ON CONFLICT(task_id, stage) DO UPDATE SET
            status='pending', payload_json=excluded.payload_json,
            requested_at=datetime('now'), decided_at=NULL, decided_by=NULL, note=NULL
        """,
        (task_id, channel_id, stage, json.dumps(payload, default=str)),
    )
    await conn.commit()


async def get_approval(conn: aiosqlite.Connection, task_id: str, stage: str) -> Optional[dict[str, Any]]:
    row = await (await conn.execute(
        "SELECT * FROM approvals WHERE task_id = ? AND stage = ?", (task_id, stage)
    )).fetchone()
    return _approval_row(row) if row else None


async def list_approvals(conn: aiosqlite.Connection, status: Optional[str] = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM approvals"
    params: tuple[Any, ...] = ()
    if status:
        sql += " WHERE status = ?"
        params = (status,)
    sql += " ORDER BY requested_at DESC"
    rows = await (await conn.execute(sql, params)).fetchall()
    return [_approval_row(row) for row in rows]


async def decide_approval(conn: aiosqlite.Connection, task_id: str, stage: str, status: str,
                           decided_by: str, note: Optional[str] = None) -> bool:
    """Returns False if the gate was already decided, so a late second click
    can't overturn a decision the pipeline has already acted on."""
    cursor = await conn.execute(
        """
        UPDATE approvals
           SET status = ?, decided_at = datetime('now'), decided_by = ?, note = ?
         WHERE task_id = ? AND stage = ? AND status = 'pending'
        """,
        (status, decided_by, note, task_id, stage),
    )
    await conn.commit()
    return cursor.rowcount > 0


async def insert_audit_log(conn: aiosqlite.Connection, actor: str, action: str,
                            resource_type: str, resource_id: Optional[str],
                            details: Optional[dict[str, Any]] = None) -> None:
    await conn.execute(
        """
        INSERT INTO audit_logs (actor, action, resource_type, resource_id, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (actor, action, resource_type, resource_id,
         json.dumps(details, default=str) if details is not None else None),
    )
    await conn.commit()


async def list_audit_logs(conn: aiosqlite.Connection, limit: int = 100) -> list[dict[str, Any]]:
    rows = await (await conn.execute(
        "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)
    )).fetchall()
    logs = []
    for row in rows:
        log = dict(row)
        log["details"] = json.loads(log["details"]) if log["details"] else None
        logs.append(log)
    return logs


async def set_schedule_enabled(conn: aiosqlite.Connection, channel_id: str, enabled: bool) -> bool:
    cursor = await conn.execute(
        "UPDATE schedules SET enabled = ? WHERE channel_id = ?", (1 if enabled else 0, channel_id)
    )
    await conn.commit()
    return cursor.rowcount > 0

"""Dashboard read-only rollup API (doc §14).

Run with: uvicorn dashboard.api.app:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from common.db import models as db
from common.db.models import DEFAULT_DB_PATH, connect
from common.scheduling import compute_next_run_utc
from dashboard.api import health_checks, queries
from dashboard.api.auth import require_api_key

# Module-level so tests can monkeypatch it to point at a seeded temp DB.
DB_PATH = DEFAULT_DB_PATH


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Apply migrations on boot.

    Locally the DB always exists because `run.py` created it, but a fresh
    deployment starts with an empty volume and nothing else would create the
    schema — every read endpoint would fail on a missing table. The migrations
    are `CREATE ... IF NOT EXISTS`, so this is a no-op on an existing DB.
    """
    await db.init_db(DB_PATH)
    yield


app = FastAPI(
    title="YouTube Orchestration Dashboard API",
    dependencies=[Depends(require_api_key)],
    lifespan=lifespan,
)


@app.get("/api/system/health")
async def system_health():
    async with connect(DB_PATH) as conn:
        return await queries.system_health(conn)


@app.get("/api/channels")
async def list_channels():
    async with connect(DB_PATH) as conn:
        return await queries.list_channels(conn)


@app.get("/api/channels/{channel_id}")
async def channel_detail(channel_id: str):
    async with connect(DB_PATH) as conn:
        channel = await queries.get_channel(conn, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail=f"channel '{channel_id}' not found")
    return channel


@app.get("/api/channels/{channel_id}/agents/{agent_type}")
async def agent_detail(channel_id: str, agent_type: str):
    async with connect(DB_PATH) as conn:
        agent = await queries.get_agent_detail(conn, channel_id, agent_type)
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"agent type '{agent_type}' not found for channel '{channel_id}'"
        )
    return agent


@app.get("/api/channels/{channel_id}/tasks/{task_id}")
async def task_detail(channel_id: str, task_id: str):
    async with connect(DB_PATH) as conn:
        task = await queries.get_task_detail(conn, channel_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task '{task_id}' not found for channel '{channel_id}'")
    return task


@app.get("/api/alerts")
async def alerts(severity: Optional[str] = Query(default=None)):
    async with connect(DB_PATH) as conn:
        return await queries.list_alerts(conn, severity)


@app.get("/api/integrations")
async def integrations():
    async with connect(DB_PATH) as conn:
        return await health_checks.run_all_checks(conn)


@app.get("/api/schedules")
async def schedules():
    async with connect(DB_PATH) as conn:
        rows = await db.list_schedules(conn)

    for row in rows:
        row["next_run_estimate"] = (
            compute_next_run_utc(row["preferred_hours_utc"]).isoformat()
            if row["enabled"] and row["preferred_hours_utc"]
            else None
        )
    return rows


@app.get("/api/orchestrator")
async def orchestrator():
    async with connect(DB_PATH) as conn:
        return await queries.get_orchestrator(conn)


# --- Write endpoints ---------------------------------------------------------
# Single-operator system with one shared API key, so there is no user identity
# to record; "operator" is the honest actor name rather than a fabricated one.
ACTOR = "operator"


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    note: Optional[str] = None


class ScheduleToggle(BaseModel):
    enabled: bool


@app.get("/api/approvals")
async def list_approvals(status: Optional[str] = Query(default=None)):
    async with connect(DB_PATH) as conn:
        return await db.list_approvals(conn, status)


@app.post("/api/approvals/{task_id}/{stage}")
async def decide_approval(task_id: str, stage: str, body: ApprovalDecision):
    async with connect(DB_PATH) as conn:
        approval = await db.get_approval(conn, task_id, stage)
        if approval is None:
            raise HTTPException(status_code=404, detail=f"no '{stage}' gate for task '{task_id}'")

        decided = await db.decide_approval(conn, task_id, stage, body.decision,
                                            decided_by=ACTOR, note=body.note)
        if not decided:
            # Already decided, or expired out from under the operator. 409 rather
            # than a silent no-op, so the UI can say what actually happened.
            raise HTTPException(
                status_code=409,
                detail=f"the '{stage}' gate for '{task_id}' is already {approval['status']}",
            )

        await db.insert_audit_log(conn, ACTOR, f"approval.{body.decision}", "task", task_id,
                                   {"stage": stage, "note": body.note})
        return await db.get_approval(conn, task_id, stage)


@app.post("/api/channels/{channel_id}/schedule")
async def set_schedule(channel_id: str, body: ScheduleToggle):
    async with connect(DB_PATH) as conn:
        updated = await db.set_schedule_enabled(conn, channel_id, body.enabled)
        if not updated:
            raise HTTPException(status_code=404, detail=f"no schedule for channel '{channel_id}'")

        await db.insert_audit_log(conn, ACTOR, "schedule.resumed" if body.enabled else "schedule.paused",
                                   "channel", channel_id)
        return {"channel_id": channel_id, "enabled": body.enabled}


@app.get("/api/audit-logs")
async def audit_logs(limit: int = Query(default=100, ge=1, le=500)):
    async with connect(DB_PATH) as conn:
        return await db.list_audit_logs(conn, limit)

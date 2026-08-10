"""Dashboard read-only rollup API (doc §14).

Run with: uvicorn dashboard.api.app:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query

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

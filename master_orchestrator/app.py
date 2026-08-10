"""Master Orchestrator control-plane service (doc §19).

Mostly non-LLM per doc §1 risk #7 — a scheduler/aggregator/alerting service.
Talks to Channel Managers via direct HTTP RPC (doc §5's sanctioned alternative
to gRPC) rather than a message bus, since neither exists in this system yet.

Run with: uvicorn master_orchestrator.app:app --port 8100
"""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from common.db import models as db
from common.db.models import DEFAULT_DB_PATH, connect
from dashboard.api.auth import require_api_key
from master_orchestrator.governor import governor
from master_orchestrator.health_aggregator import run_health_cycle

logger = logging.getLogger("master_orchestrator")

DB_PATH = DEFAULT_DB_PATH
CYCLE_INTERVAL_SECONDS = 30

_started_at = datetime.now(timezone.utc).isoformat()
_cycles_run = 0


async def _monitoring_loop() -> None:
    """doc §19's monitoring_loop — runs for the lifetime of the service.

    Each cycle is isolated in its own try/except: one bad cycle (a transient
    DB hiccup, a bug in a new check) must not silently kill background
    monitoring for the rest of the process's life — that failure mode is
    far worse than one skipped cycle, and would otherwise be invisible since
    nothing else observes this task's exceptions.
    """
    global _cycles_run
    while True:
        try:
            async with connect(DB_PATH) as conn:
                result = await run_health_cycle(conn)
                _cycles_run += 1
                await db.upsert_orchestrator_status(
                    conn, status="online", started_at=_started_at,
                    managed_channels=result["channels_checked"],
                    active_slots=governor.active_count, max_slots=governor.max_slots,
                    cycles_run=_cycles_run,
                )
        except Exception:
            logger.exception("health-aggregator cycle failed")
        await asyncio.sleep(CYCLE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # A fresh deployment boots against an empty volume; without this the very
    # first monitoring cycle fails on missing tables. No-op on an existing DB.
    await db.init_db(DB_PATH)
    task = asyncio.create_task(_monitoring_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="Master Orchestrator",
    dependencies=[Depends(require_api_key)],
    lifespan=lifespan,
)


class SlotRequest(BaseModel):
    channel_id: str


class SlotRelease(BaseModel):
    slot_id: str


@app.get("/orchestrator/health")
async def orchestrator_health():
    async with connect(DB_PATH) as conn:
        status = await db.get_orchestrator_status(conn)
    return {
        "status": "online",
        "started_at": _started_at,
        "uptime_seconds": time.time() - datetime.fromisoformat(_started_at).timestamp(),
        "cycles_run": _cycles_run,
        "active_slots": governor.active_count,
        "max_slots": governor.max_slots,
        "active_channels": governor.active_channels(),
        "last_cycle": status,
    }


@app.post("/orchestrator/slots/acquire")
async def acquire_slot(request: SlotRequest):
    slot_id = await governor.acquire_slot(request.channel_id)
    return {"granted": slot_id is not None, "slot_id": slot_id}


@app.post("/orchestrator/slots/release")
async def release_slot(request: SlotRelease):
    released = await governor.release_slot(request.slot_id)
    return {"released": released}

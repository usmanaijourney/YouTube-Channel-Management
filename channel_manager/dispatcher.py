"""Invokes stateless agent functions with retry/backoff and heartbeat bookkeeping (doc §9, §10)."""
from __future__ import annotations

import asyncio
import importlib
from typing import Any

import aiosqlite

from common.db import models as db
from common.errors import PermanentError, TransientError
from common.message_schema import AgentResult, ErrorInfo, ErrorType, MessageType, Status, TaskEnvelope

AGENT_MODULES = {
    "topic_generator": "agents.topic_generator",
    "script_writer": "agents.script_writer",
    "voice_over": "agents.voice_over",
    "video_planner": "agents.video_planner",
    "video_renderer": "agents.video_renderer",
    "youtube_uploader": "agents.youtube_uploader",
    "whatsapp_notifier": "agents.whatsapp_notifier",
}

MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 0.2


async def run_agent(conn: aiosqlite.Connection, agent_type: str, channel_id: str, task_id: str,
                     payload: dict[str, Any], agent_suffix: str = "") -> AgentResult:
    agent_id = f"{agent_type}{agent_suffix}-{channel_id}"
    module = importlib.import_module(AGENT_MODULES[agent_type])

    envelope = TaskEnvelope(
        task_id=task_id,
        channel_id=channel_id,
        agent_id=agent_id,
        message_type=MessageType.TASK_STARTED,
        status=Status.IN_PROGRESS,
        idempotency_key=f"{task_id}-{agent_type}{agent_suffix}",
        payload=payload,
    )

    await db.upsert_agent_status(conn, agent_id, channel_id, agent_type, "busy")

    attempt = 0
    while True:
        try:
            result = await module.run(envelope)
            await db.upsert_agent_status(
                conn, agent_id, channel_id, agent_type, "idle",
                success=(result.status == Status.SUCCESS),
            )
            return result
        except TransientError as e:
            attempt += 1
            envelope.retry_count = attempt
            if attempt > MAX_RETRIES:
                await db.upsert_agent_status(conn, agent_id, channel_id, agent_type, "degraded", success=False)
                return AgentResult(
                    status=Status.FAILED,
                    error=ErrorInfo(type=ErrorType.TRANSIENT, message=f"exceeded {MAX_RETRIES} retries: {e}"),
                )
            await asyncio.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))
        except PermanentError as e:
            await db.upsert_agent_status(conn, agent_id, channel_id, agent_type, "idle", success=False)
            return AgentResult(status=Status.FAILED, error=ErrorInfo(type=ErrorType.PERMANENT, message=str(e)))

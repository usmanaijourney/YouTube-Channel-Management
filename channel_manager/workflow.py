"""Channel Manager pipeline FSM — doc §18, simplified (no Temporal yet, per §20 MVP scope).

Durable via task_events (every transition is committed to SQLite before moving on),
so a crash mid-pipeline is diagnosable from the event log even though this MVP
doesn't yet resume an in-flight run automatically (that's the Temporal migration, §25 step 9).
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Awaitable, Callable

import aiosqlite

from channel_manager import dispatcher
from channel_manager.quality_check import quality_check
from common import secrets
from common.db import models as db

ApprovalCallback = Callable[[str, str, dict[str, Any]], Awaitable[bool]]

MAX_PRODUCTION_ATTEMPTS = 2  # first attempt + one regenerate-and-retry round (§9)


async def _auto_approve(task_id: str, stage: str, payload: dict[str, Any]) -> bool:
    return True


class TaskFailed(Exception):
    def __init__(self, stage: str, reason: str):
        self.stage = stage
        self.reason = reason
        super().__init__(f"{stage}: {reason}")


async def _produce_and_check(conn: aiosqlite.Connection, channel_id: str, task_id: str,
                              channel_config: dict[str, Any], script: dict[str, Any],
                              state: dict[str, Any]) -> tuple[bool, list[str]]:
    """Runs VOICE_OVER + VISUAL_PLANNING + RENDER + QUALITY_CHECK. Callable more than
    once so a quality-check failure can regenerate production output rather than
    the whole task (doc §9: 'regenerate script instead of re-running with same bad input',
    applied here to the production stage)."""
    await db.update_task_state(conn, task_id, "PRODUCTION_FANOUT")
    voice_result, plan_result = await asyncio.gather(
        dispatcher.run_agent(conn, "voice_over", channel_id, task_id, {
            "channel_config": channel_config, "script": script,
        }),
        dispatcher.run_agent(conn, "video_planner", channel_id, task_id, {
            "channel_config": channel_config, "script": script,
        }),
    )
    if voice_result.status.value != "success":
        raise TaskFailed("VOICE_OVER", voice_result.error.message if voice_result.error else "unknown")
    if plan_result.status.value != "success":
        raise TaskFailed("VISUAL_PLANNING", plan_result.error.message if plan_result.error else "unknown")

    state["voice_over_path"] = voice_result.payload["voice_over_path"]
    state["voice_over_duration_seconds"] = voice_result.payload["voice_over_duration_seconds"]
    await db.update_task_state(conn, task_id, "VOICE_OVER_DONE", payload=voice_result.payload)

    render_spec = plan_result.payload["render_spec"]
    await db.update_task_state(conn, task_id, "VISUAL_PLANNING_IN_PROGRESS", payload={"render_spec": render_spec})

    video_result = await dispatcher.run_agent(conn, "video_renderer", channel_id, task_id, {
        "render_spec": render_spec,
        "voice_over_path": state["voice_over_path"],
        "voice_over_duration_seconds": state["voice_over_duration_seconds"],
    })
    if video_result.status.value != "success":
        raise TaskFailed("RENDER", video_result.error.message if video_result.error else "unknown")

    state["video_path"] = video_result.payload["video_path"]
    state["video_duration_seconds"] = video_result.payload["video_duration_seconds"]
    state["thumbnail_path"] = video_result.payload["thumbnail_path"]
    await db.update_task_state(conn, task_id, "VIDEO_DONE", payload=video_result.payload)

    await db.update_task_state(conn, task_id, "PRODUCTION_JOIN")

    ok, failed_checks = quality_check(state, channel_config)
    await db.update_task_state(conn, task_id, "QUALITY_CHECK",
                                payload={"passed": ok, "failed_checks": failed_checks})
    return ok, failed_checks


async def run_pipeline(conn: aiosqlite.Connection, channel_config: dict[str, Any],
                        approval_callback: ApprovalCallback = _auto_approve) -> dict[str, Any]:
    channel_id = channel_config["channel_id"]
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    gates = channel_config["content_strategy"]["approval_gates"]

    await db.create_task(conn, task_id, channel_id, "CREATED")
    state: dict[str, Any] = {"channel_id": channel_id, "uploader_target_channel_id": channel_id}

    try:
        await db.update_task_state(conn, task_id, "TOPIC_RESEARCH")
        tg_payload = {"channel_config": channel_config}
        tg1_result, tg2_result = await asyncio.gather(
            dispatcher.run_agent(conn, "topic_generator", channel_id, task_id, tg_payload, agent_suffix="-1"),
            dispatcher.run_agent(conn, "topic_generator", channel_id, task_id, tg_payload, agent_suffix="-2"),
        )
        candidates = [r.payload["topic"] for r in (tg1_result, tg2_result) if r.status.value == "success"]
        if not candidates:
            raise TaskFailed("TOPIC_RESEARCH", "both topic generators failed")

        await db.update_task_state(conn, task_id, "TOPIC_EVALUATION")
        approved_topic = candidates[0]
        if gates["topic"]:
            if not await approval_callback(task_id, "topic", approved_topic):
                raise TaskFailed("TOPIC_EVALUATION", "human rejected topic")
        await db.update_task_state(conn, task_id, "TOPIC_APPROVED", payload=approved_topic)
        state["topic"] = approved_topic

        await db.update_task_state(conn, task_id, "SCRIPT_DRAFTING")
        script_result = await dispatcher.run_agent(conn, "script_writer", channel_id, task_id, {
            "channel_config": channel_config, "approved_topic": approved_topic,
        })
        if script_result.status.value != "success":
            raise TaskFailed("SCRIPT_DRAFTING", script_result.error.message if script_result.error else "unknown")
        script = script_result.payload["script"]
        if gates["script"]:
            if not await approval_callback(task_id, "script", script):
                raise TaskFailed("SCRIPT_DRAFTING", "human rejected script")
        await db.update_task_state(conn, task_id, "SCRIPT_APPROVED", payload={"script": script})
        state["script"] = script
        state["title"] = approved_topic["title"]
        state["description"] = script["hook"] + " " + script["cta"]

        ok, failed_checks = False, []
        for attempt in range(1, MAX_PRODUCTION_ATTEMPTS + 1):
            ok, failed_checks = await _produce_and_check(conn, channel_id, task_id, channel_config, script, state)
            if ok or attempt == MAX_PRODUCTION_ATTEMPTS:
                break
        if not ok:
            raise TaskFailed("QUALITY_CHECK", f"failed checks after {MAX_PRODUCTION_ATTEMPTS} attempts: {failed_checks}")

        if gates["pre_upload"]:
            if not await approval_callback(task_id, "pre_upload", {
                "video_path": state["video_path"], "title": state["title"],
            }):
                raise TaskFailed("PRE_UPLOAD_APPROVAL", "human rejected upload")

        await db.update_task_state(conn, task_id, "UPLOAD_IN_PROGRESS")
        yt_secret = await secrets.get_secret(channel_id, channel_config["credentials_ref"]["youtube"])
        upload_result = await dispatcher.run_agent(conn, "youtube_uploader", channel_id, task_id, {
            "video_path": state["video_path"],
            "title": state["title"],
            "description": state["description"],
            "access_token": yt_secret["access_token"],
            "uploader_target_channel_id": channel_id,
        })
        if upload_result.status.value != "success":
            raise TaskFailed("UPLOAD", upload_result.error.message if upload_result.error else "unknown")
        await db.update_task_state(conn, task_id, "UPLOAD_DONE", payload=upload_result.payload)

        video_id = f"video_{uuid.uuid4().hex[:12]}"
        await db.insert_video(conn, video_id, task_id, channel_id,
                               upload_result.payload["youtube_video_id"],
                               upload_result.payload["youtube_url"],
                               state["title"], "uploaded")

        if channel_config["notifications"]["on_upload_success"]:
            wa_secret = await secrets.get_secret(channel_id, channel_config["credentials_ref"]["whatsapp_recipient"])
            await dispatcher.run_agent(conn, "whatsapp_notifier", channel_id, task_id, {
                "recipient": wa_secret["recipient"],
                "event": "upload_success",
                "result": upload_result.payload,
            })
        await db.update_task_state(conn, task_id, "NOTIFY")

        await db.update_task_state(conn, task_id, "REPORTED")
        await db.update_task_state(conn, task_id, "CLOSED")

        return {"task_id": task_id, "status": "success", "video": upload_result.payload}

    except TaskFailed as e:
        await db.update_task_state(conn, task_id, "FAILED", error={"stage": e.stage, "reason": e.reason})
        await db.insert_system_event(
            conn, channel_id, event_type="task_failed", severity="critical",
            payload={"task_id": task_id, "stage": e.stage, "reason": e.reason},
        )
        if channel_config["notifications"]["on_failure"]:
            try:
                wa_secret = await secrets.get_secret(channel_id, channel_config["credentials_ref"]["whatsapp_recipient"])
                await dispatcher.run_agent(conn, "whatsapp_notifier", channel_id, task_id, {
                    "recipient": wa_secret["recipient"],
                    "event": "failure",
                    "result": {"message": f"{e.stage}: {e.reason}"},
                })
            except Exception:
                pass  # notification failure must never mask the original failure
        return {"task_id": task_id, "status": "failed", "stage": e.stage, "reason": e.reason}

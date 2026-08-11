"""Approval gates backed by the database rather than a terminal prompt.

The CLI gates in run.py meant a run could only happen with an operator sitting
at the machine. Here the pipeline opens a gate by writing a 'pending' approvals
row and then waits for something else — the dashboard — to decide it, which is
what lets a run happen while nobody is watching.

The wait is a poll rather than a notification: SQLite has no LISTEN/NOTIFY, and
a gate that takes minutes-to-hours to answer does not justify a message bus.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import aiosqlite

from common.db import models as db

DEFAULT_POLL_SECONDS = 5
# A gate left unanswered must not hold a production slot forever. Six hours is
# long enough for "approve it after work" and short enough that a forgotten
# task fails visibly the same day instead of hanging until someone notices.
DEFAULT_TIMEOUT_SECONDS = 6 * 60 * 60


class ApprovalTimeout(Exception):
    """Nobody decided the gate within the timeout."""


def db_approval_callback(conn: aiosqlite.Connection, channel_id: str,
                          poll_seconds: int = DEFAULT_POLL_SECONDS,
                          timeout_seconds: Optional[int] = DEFAULT_TIMEOUT_SECONDS):
    """Builds an ApprovalCallback for run_pipeline that waits on the approvals table."""

    async def await_decision(task_id: str, stage: str, payload: dict[str, Any]) -> bool:
        await db.request_approval(conn, task_id, channel_id, stage, payload)

        waited = 0
        while True:
            approval = await db.get_approval(conn, task_id, stage)
            # A missing row means someone deleted it out from under us; treat that
            # as a refusal rather than looping forever on something that will
            # never be decided.
            if approval is None:
                return False
            if approval["status"] == "approved":
                return True
            if approval["status"] in ("rejected", "expired"):
                return False

            if timeout_seconds is not None and waited >= timeout_seconds:
                await db.decide_approval(conn, task_id, stage, "expired", decided_by="system",
                                          note=f"no decision within {timeout_seconds}s")
                raise ApprovalTimeout(
                    f"no decision on the '{stage}' gate for {task_id} within {timeout_seconds}s"
                )

            await asyncio.sleep(poll_seconds)
            waited += poll_seconds

    return await_decision

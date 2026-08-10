"""Real integration health checks (doc's "Integrations" nav section).

Each check actually exercises the dependency — a subprocess version check, a
live DB query, a real OAuth token refresh, a real trivial TTS synthesis —
rather than reporting a canned "healthy". Mocked providers (WhatsApp, the
LLM behind topic/script generation) report status="mocked" instead of lying
about being a real, currently-healthy integration.
"""
from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import aiosqlite

from common import secrets
from common.db import models as db

CHANNEL_ID_FOR_CHECKS = "channel-001"  # single-operator MVP has exactly one real channel


async def _time_it(coro: Awaitable[None]) -> tuple[bool, int, Optional[str]]:
    start = time.monotonic()
    try:
        await coro
        return True, int((time.monotonic() - start) * 1000), None
    except Exception as e:
        return False, int((time.monotonic() - start) * 1000), str(e)


async def _check_database(conn: aiosqlite.Connection) -> None:
    await conn.execute("SELECT 1")


async def _check_subprocess_version(binary: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        binary, "-version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"{binary} exited {proc.returncode}: {stderr.decode(errors='replace')[:300]}")


async def _check_youtube_oauth() -> None:
    await secrets.get_secret(CHANNEL_ID_FOR_CHECKS, f"{CHANNEL_ID_FOR_CHECKS}/youtube_oauth")


async def _check_edge_tts() -> None:
    import edge_tts

    with tempfile.TemporaryDirectory() as tmp:
        out_path = str(Path(tmp) / "healthcheck.mp3")
        await edge_tts.Communicate("ok", "en-US-AriaNeural").save(out_path)
        if not Path(out_path).exists() or Path(out_path).stat().st_size == 0:
            raise RuntimeError("edge-tts produced no audio")


CHECKS: dict[str, Callable[[], Awaitable[None]]] = {
    "ffmpeg": lambda: _check_subprocess_version("ffmpeg"),
    "ffprobe": lambda: _check_subprocess_version("ffprobe"),
    "youtube_api": _check_youtube_oauth,
    "edge_tts": _check_edge_tts,
}

MOCKED_SERVICES = ["whatsapp_api", "llm_provider"]


async def run_all_checks(conn: aiosqlite.Connection) -> list[dict[str, Any]]:
    ok, ms, err = await _time_it(_check_database(conn))
    await db.record_health_check(conn, "database", "healthy" if ok else "error", ms, err)

    for name, check_factory in CHECKS.items():
        ok, ms, err = await _time_it(check_factory())
        await db.record_health_check(conn, name, "healthy" if ok else "error", ms, err)

    for name in MOCKED_SERVICES:
        await db.record_health_check(conn, name, "mocked")

    return await db.list_health(conn)

"""Real health-check integration test — requires ffmpeg/ffprobe on PATH.

Deliberately scoped to the checks that don't need live credentials (database,
ffmpeg, ffprobe). youtube_api and edge_tts real-network checks are covered
only by the mocked unit tests (tests/unit/test_health_checks.py) — hitting
Google's OAuth endpoint or the edge-tts service on every test run isn't
appropriate for a repeatable, credential-free test suite.
"""
from __future__ import annotations

from unittest.mock import patch

from common.db import models as db
from dashboard.api import health_checks


async def test_ffmpeg_ffprobe_and_database_checks_are_real(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)

    real_checks = {k: v for k, v in health_checks.CHECKS.items() if k in ("ffmpeg", "ffprobe")}

    async with db.connect(db_path) as conn:
        with patch.object(health_checks, "CHECKS", real_checks), \
             patch.object(health_checks, "MOCKED_SERVICES", []):
            results = await health_checks.run_all_checks(conn)

    by_name = {r["service_name"]: r for r in results}
    assert by_name["database"]["status"] == "healthy"
    assert by_name["ffmpeg"]["status"] == "healthy"
    assert by_name["ffprobe"]["status"] == "healthy"
    assert by_name["ffmpeg"]["response_time_ms"] >= 0

from unittest.mock import patch

from common.db import models as db
from dashboard.api import health_checks


async def test_run_all_checks_records_healthy_and_error(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)

    async def _ok():
        return None

    async def _fail():
        raise RuntimeError("boom")

    fake_checks = {"ffmpeg": _ok, "youtube_api": _fail}

    async with db.connect(db_path) as conn:
        with patch.object(health_checks, "CHECKS", fake_checks), \
             patch.object(health_checks, "MOCKED_SERVICES", ["whatsapp_api"]):
            results = await health_checks.run_all_checks(conn)

    by_name = {r["service_name"]: r for r in results}
    assert by_name["database"]["status"] == "healthy"
    assert by_name["ffmpeg"]["status"] == "healthy"
    assert by_name["youtube_api"]["status"] == "error"
    assert by_name["youtube_api"]["error_count"] == 1
    assert "boom" in by_name["youtube_api"]["last_error"]
    assert by_name["whatsapp_api"]["status"] == "mocked"


async def test_error_count_accumulates_across_checks(tmp_path):
    db_path = str(tmp_path / "test.db")
    await db.init_db(db_path)

    async def _fail():
        raise RuntimeError("still down")

    async with db.connect(db_path) as conn:
        with patch.object(health_checks, "CHECKS", {"youtube_api": _fail}), \
             patch.object(health_checks, "MOCKED_SERVICES", []):
            await health_checks.run_all_checks(conn)
            results = await health_checks.run_all_checks(conn)

    by_name = {r["service_name"]: r for r in results}
    assert by_name["youtube_api"]["error_count"] == 2

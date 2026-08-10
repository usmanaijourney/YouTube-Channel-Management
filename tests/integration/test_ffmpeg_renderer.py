"""Integration test for the real FFmpeg renderer — requires ffmpeg/ffprobe on PATH.

Deliberately not part of tests/unit: it shells out to a real external binary
and takes real (if brief) encode time, per doc §23's unit vs integration split.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from common.providers.renderer import render_video

RENDER_SPEC = {
    "shots": [
        {"type": "stock", "query": "phone settings", "duration_s": 1},
        {"type": "text_overlay", "text": "Try this today", "duration_s": 1},
    ],
    "template": "clean-tech-v2",
}


async def _ffprobe_duration(path: str) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return float(json.loads(stdout)["format"]["duration"])


async def test_render_video_produces_a_real_playable_mp4(tmp_path):
    out_path = str(tmp_path / "video.mp4")

    result = await render_video(RENDER_SPEC, voice_over_path="vo.txt",
                                 voice_over_duration_s=1.5, out_path=out_path)

    assert result["duration_seconds"] >= 2.0  # sum of shot durations, not clipped by the shorter VO track
    video_file = tmp_path / "video.mp4"
    thumb_file = tmp_path / "video.jpg"
    assert video_file.exists() and video_file.stat().st_size > 1000
    assert thumb_file.exists() and thumb_file.stat().st_size > 100

    probed_duration = await _ffprobe_duration(str(video_file))
    assert probed_duration == pytest.approx(result["duration_seconds"], abs=0.3)

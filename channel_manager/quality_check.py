"""Deterministic (non-LLM, fast) quality gate — doc §12, run before UPLOAD_IN_PROGRESS."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _audio_is_valid(path: str) -> bool:
    return bool(path) and Path(path).exists() and Path(path).stat().st_size > 0


def _video_is_valid(path: str) -> bool:
    return bool(path) and Path(path).exists() and Path(path).stat().st_size > 0


def _video_duration_ok(duration_seconds: float, video_length_minutes: list[int]) -> bool:
    # Mock content is far shorter than a real script's target length, so only
    # the upper bound is enforced here — a real render must additionally clear
    # the configured minimum (video_length_minutes[0] * 60).
    max_seconds = video_length_minutes[1] * 60
    return 0 < duration_seconds <= max_seconds


def _av_sync_ok(video_duration_seconds: float, voice_over_duration_seconds: float) -> bool:
    return video_duration_seconds >= voice_over_duration_seconds - 0.5


def quality_check(state: dict[str, Any], channel_config: dict[str, Any]) -> tuple[bool, list[str]]:
    script = state.get("script") or {}
    checks = {
        "script_present": bool(script.get("hook", "").strip()),
        "voice_over_valid": _audio_is_valid(state.get("voice_over_path", "")),
        "video_valid": _video_is_valid(state.get("video_path", "")),
        "video_duration_ok": _video_duration_ok(
            state.get("video_duration_seconds", 0),
            channel_config["content_strategy"]["video_length_minutes"],
        ),
        "thumbnail_present": bool(state.get("thumbnail_path")),
        "av_sync_ok": _av_sync_ok(
            state.get("video_duration_seconds", 0),
            state.get("voice_over_duration_seconds", 0),
        ),
        "metadata_complete": bool(state.get("title")) and bool(state.get("description")),
        "no_cross_post": state.get("channel_id") == state.get("uploader_target_channel_id"),
    }
    failed = [name for name, ok in checks.items() if not ok]
    return len(failed) == 0, failed

from pathlib import Path

from channel_manager.quality_check import quality_check


def _valid_state(tmp_path: Path) -> dict:
    voice_path = tmp_path / "vo.txt"
    voice_path.write_text("audio")
    video_path = tmp_path / "video.txt"
    video_path.write_text("video")
    return {
        "channel_id": "channel-001",
        "uploader_target_channel_id": "channel-001",
        "script": {"hook": "hook", "sections": [{"heading": "a", "body": "b"}], "cta": "cta"},
        "voice_over_path": str(voice_path),
        "voice_over_duration_seconds": 10.0,
        "video_path": str(video_path),
        "video_duration_seconds": 12.0,
        "thumbnail_path": "thumb.txt",
        "title": "Title",
        "description": "Description",
    }


def test_quality_check_passes_when_all_checks_ok(channel_config, tmp_path):
    ok, failed = quality_check(_valid_state(tmp_path), channel_config)
    assert ok is True
    assert failed == []


def test_quality_check_fails_on_cross_post(channel_config, tmp_path):
    state = _valid_state(tmp_path)
    state["uploader_target_channel_id"] = "channel-999"
    ok, failed = quality_check(state, channel_config)
    assert ok is False
    assert "no_cross_post" in failed


def test_quality_check_fails_on_missing_video_file(channel_config, tmp_path):
    state = _valid_state(tmp_path)
    state["video_path"] = str(tmp_path / "does_not_exist.txt")
    ok, failed = quality_check(state, channel_config)
    assert ok is False
    assert "video_valid" in failed


def test_quality_check_fails_on_av_desync(channel_config, tmp_path):
    state = _valid_state(tmp_path)
    state["video_duration_seconds"] = 2.0
    state["voice_over_duration_seconds"] = 10.0
    ok, failed = quality_check(state, channel_config)
    assert ok is False
    assert "av_sync_ok" in failed


def test_quality_check_fails_when_video_exceeds_max_duration(channel_config, tmp_path):
    state = _valid_state(tmp_path)
    state["video_duration_seconds"] = 999.0
    state["voice_over_duration_seconds"] = 10.0
    ok, failed = quality_check(state, channel_config)
    assert ok is False
    assert "video_duration_ok" in failed

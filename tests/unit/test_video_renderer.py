from unittest.mock import AsyncMock, patch

import pytest

from agents import video_renderer
from common.errors import TransientError
from tests.unit.conftest import make_envelope

RENDER_SPEC = {"shots": [{"type": "stock", "query": "phone", "duration_s": 4}], "template": "clean-tech-v2"}


async def test_video_renderer_success(channel_config, tmp_path, monkeypatch):
    # The real renderer shells out to ffmpeg (see tests/integration for that
    # coverage) — unit tests stay fast/offline by mocking it, per doc §23.
    monkeypatch.chdir(tmp_path)
    envelope = make_envelope("video_renderer", {
        "render_spec": RENDER_SPEC, "voice_over_path": "vo.txt", "voice_over_duration_seconds": 3.0,
    })
    fake_result = {"video_path": "video.mp4", "duration_seconds": 4.0, "thumbnail_path": "video.jpg"}
    with patch("agents.video_renderer.render_video", AsyncMock(return_value=fake_result)):
        result = await video_renderer.run(envelope)
    assert result.status.value == "success"
    assert result.payload["video_path"]
    assert result.payload["thumbnail_path"]
    assert result.payload["video_duration_seconds"] > 0


async def test_video_renderer_transient_error_propagates(channel_config):
    envelope = make_envelope("video_renderer", {
        "render_spec": RENDER_SPEC, "voice_over_path": "vo.txt", "voice_over_duration_seconds": 3.0,
    })
    with patch("agents.video_renderer.render_video", AsyncMock(side_effect=TransientError("renderer down"))):
        with pytest.raises(TransientError):
            await video_renderer.run(envelope)


async def test_video_renderer_zero_duration_is_permanent_failure(channel_config):
    envelope = make_envelope("video_renderer", {
        "render_spec": RENDER_SPEC, "voice_over_path": "vo.txt", "voice_over_duration_seconds": 3.0,
    })
    with patch("agents.video_renderer.render_video",
               AsyncMock(return_value={"video_path": "x", "duration_seconds": 0, "thumbnail_path": "t"})):
        result = await video_renderer.run(envelope)
    assert result.status.value == "failed"
    assert result.error.type.value == "permanent"

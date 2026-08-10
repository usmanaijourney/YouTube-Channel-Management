from unittest.mock import AsyncMock, patch

import pytest

from agents import youtube_uploader
from common.errors import TransientError
from tests.unit.conftest import make_envelope

BASE_PAYLOAD = {
    "video_path": "video.txt",
    "title": "Title",
    "description": "Description",
    "access_token": "mock-token",
    "uploader_target_channel_id": "channel-001",
}


async def test_youtube_uploader_success(channel_config):
    envelope = make_envelope("youtube_uploader", BASE_PAYLOAD)
    fake_response = {
        "youtube_video_id": "yt_fake123",
        "youtube_url": "https://youtube.com/watch?v=yt_fake123",
        "title": "Title",
    }
    with patch("agents.youtube_uploader.upload_video", AsyncMock(return_value=fake_response)):
        result = await youtube_uploader.run(envelope)
    assert result.status.value == "success"
    assert result.payload["youtube_url"]


async def test_youtube_uploader_blocks_cross_post(channel_config):
    payload = {**BASE_PAYLOAD, "uploader_target_channel_id": "channel-999"}
    envelope = make_envelope("youtube_uploader", payload)
    result = await youtube_uploader.run(envelope)
    assert result.status.value == "failed"
    assert result.error.type.value == "permanent"
    assert "cross-post" in result.error.message


async def test_youtube_uploader_transient_error_propagates(channel_config):
    envelope = make_envelope("youtube_uploader", BASE_PAYLOAD)
    with patch("agents.youtube_uploader.upload_video", AsyncMock(side_effect=TransientError("rate limited"))):
        with pytest.raises(TransientError):
            await youtube_uploader.run(envelope)

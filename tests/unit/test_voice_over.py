from unittest.mock import AsyncMock, patch

import pytest

from agents import voice_over
from common.errors import TransientError
from tests.unit.conftest import make_envelope

SCRIPT = {
    "hook": "Did you know this?",
    "sections": [{"heading": "The Problem", "body": "Most people never check this."}],
    "cta": "Subscribe for more.",
}


async def test_voice_over_success(channel_config, tmp_path, monkeypatch):
    # Real synthesize_speech shells out to Microsoft's edge-tts service —
    # mocked here per doc §23 (unit tests stay offline).
    monkeypatch.chdir(tmp_path)
    envelope = make_envelope("voice_over", {"channel_config": channel_config, "script": SCRIPT})
    fake_result = {"audio_path": "voice_over.mp3", "duration_seconds": 5.2}
    with patch("agents.voice_over.synthesize_speech", AsyncMock(return_value=fake_result)):
        result = await voice_over.run(envelope)
    assert result.status.value == "success"
    assert result.payload["voice_over_path"]
    assert result.payload["voice_over_duration_seconds"] > 0


async def test_voice_over_tts_transient_failure_propagates(channel_config):
    envelope = make_envelope("voice_over", {"channel_config": channel_config, "script": SCRIPT})
    with patch("agents.voice_over.synthesize_speech", AsyncMock(side_effect=TransientError("tts down"))):
        with pytest.raises(TransientError):
            await voice_over.run(envelope)


async def test_voice_over_zero_duration_is_permanent_failure(channel_config):
    envelope = make_envelope("voice_over", {"channel_config": channel_config, "script": SCRIPT})
    with patch("agents.voice_over.synthesize_speech",
               AsyncMock(return_value={"audio_path": "x", "duration_seconds": 0})):
        result = await voice_over.run(envelope)
    assert result.status.value == "failed"
    assert result.error.type.value == "permanent"

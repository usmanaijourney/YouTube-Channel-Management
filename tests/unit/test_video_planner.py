from unittest.mock import AsyncMock, patch

import pytest

from agents import video_planner
from common.errors import TransientError
from tests.unit.conftest import make_envelope

SCRIPT = {
    "hook": "Did you know this?",
    "sections": [{"heading": "The Problem", "body": "Most people never check this."}],
    "cta": "Subscribe for more.",
}


async def test_video_planner_success(channel_config):
    envelope = make_envelope("video_planner", {"channel_config": channel_config, "script": SCRIPT})
    result = await video_planner.run(envelope)
    assert result.status.value == "success"
    assert result.payload["render_spec"]["shots"]


async def test_video_planner_empty_shots_is_permanent_failure(channel_config):
    envelope = make_envelope("video_planner", {"channel_config": channel_config, "script": SCRIPT})
    with patch("agents.video_planner.call_llm", AsyncMock(return_value={"shots": [], "template": "x"})):
        result = await video_planner.run(envelope)
    assert result.status.value == "failed"
    assert result.error.type.value == "permanent"


async def test_video_planner_transient_error_propagates(channel_config):
    envelope = make_envelope("video_planner", {"channel_config": channel_config, "script": SCRIPT})
    with patch("agents.video_planner.call_llm", AsyncMock(side_effect=TransientError("boom"))):
        with pytest.raises(TransientError):
            await video_planner.run(envelope)

from unittest.mock import AsyncMock, patch

import pytest

from agents import script_writer
from common.errors import TransientError
from tests.unit.conftest import make_envelope

TOPIC = {"title": "5 Hidden Settings", "research_notes": "notes"}


async def test_script_writer_success(channel_config):
    envelope = make_envelope("script_writer", {"channel_config": channel_config, "approved_topic": TOPIC})
    result = await script_writer.run(envelope)
    assert result.status.value == "success"
    assert result.payload["script"]["hook"]
    assert result.payload["script"]["sections"]
    assert result.payload["script"]["cta"]


@pytest.mark.parametrize("malformed", [
    {"hook": "", "sections": [{"heading": "a", "body": "b"}], "cta": "cta"},
    {"hook": "hook", "sections": [], "cta": "cta"},
    {"hook": "hook", "sections": [{"heading": "a", "body": "b"}], "cta": ""},
])
async def test_script_writer_rejects_malformed_output(channel_config, malformed):
    envelope = make_envelope("script_writer", {"channel_config": channel_config, "approved_topic": TOPIC})
    with patch("agents.script_writer.call_llm", AsyncMock(return_value=malformed)):
        result = await script_writer.run(envelope)
    assert result.status.value == "failed"
    assert result.error.type.value == "permanent"


async def test_script_writer_transient_error_propagates(channel_config):
    envelope = make_envelope("script_writer", {"channel_config": channel_config, "approved_topic": TOPIC})
    with patch("agents.script_writer.call_llm", AsyncMock(side_effect=TransientError("boom"))):
        with pytest.raises(TransientError):
            await script_writer.run(envelope)

from unittest.mock import AsyncMock, patch

import pytest

from agents import topic_generator
from common.errors import TransientError
from tests.unit.conftest import make_envelope


async def test_topic_generator_success(channel_config):
    envelope = make_envelope("topic_generator-1", {"channel_config": channel_config})
    result = await topic_generator.run(envelope)
    assert result.status.value == "success"
    assert result.payload["topic"]["title"]


async def test_topic_generator_malformed_output_is_permanent_failure(channel_config):
    envelope = make_envelope("topic_generator-1", {"channel_config": channel_config})
    with patch("agents.topic_generator.call_llm", AsyncMock(return_value={"title": "   "})):
        result = await topic_generator.run(envelope)
    assert result.status.value == "failed"
    assert result.error.type.value == "permanent"


async def test_topic_generator_transient_error_propagates(channel_config):
    envelope = make_envelope("topic_generator-1", {"channel_config": channel_config})
    with patch("agents.topic_generator.call_llm", AsyncMock(side_effect=TransientError("boom"))):
        with pytest.raises(TransientError):
            await topic_generator.run(envelope)

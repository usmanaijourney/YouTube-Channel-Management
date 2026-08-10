from unittest.mock import AsyncMock, patch

import pytest

from agents import whatsapp_notifier
from common.errors import TransientError
from tests.unit.conftest import make_envelope


async def test_whatsapp_notifier_success(channel_config):
    envelope = make_envelope("whatsapp_notifier", {
        "recipient": "+1000", "event": "upload_success",
        "result": {"youtube_url": "https://youtube.com/watch?v=x"},
    })
    result = await whatsapp_notifier.run(envelope)
    assert result.status.value == "success"
    assert result.payload["delivered"] is True


async def test_whatsapp_notifier_transient_error_propagates(channel_config):
    envelope = make_envelope("whatsapp_notifier", {
        "recipient": "+1000", "event": "upload_success", "result": {},
    })
    with patch("agents.whatsapp_notifier.send_message", AsyncMock(side_effect=TransientError("wa down"))):
        with pytest.raises(TransientError):
            await whatsapp_notifier.run(envelope)

"""Mocked WhatsApp Business Platform client (doc §13)."""
from __future__ import annotations

import asyncio
from typing import Any

from common.errors import TransientError


async def send_message(recipient: str, message: str, *,
                        simulate_failure: bool = False) -> dict[str, Any]:
    await asyncio.sleep(0)

    if simulate_failure:
        raise TransientError("mock WhatsApp API: simulated transient failure")

    return {"delivered": True, "recipient": recipient}

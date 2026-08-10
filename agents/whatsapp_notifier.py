"""WhatsApp Notifier agent."""
from __future__ import annotations

from common.errors import TransientError
from common.message_schema import AgentResult, Status, TaskEnvelope
from common.providers.whatsapp import send_message


async def run(envelope: TaskEnvelope) -> AgentResult:
    recipient = envelope.payload["recipient"]
    event = envelope.payload["event"]
    result = envelope.payload.get("result", {})

    if event == "upload_success":
        message = f"Video uploaded: {result.get('youtube_url', '')}"
    else:
        message = f"Task {envelope.task_id} failed: {result.get('message', 'unknown error')}"

    try:
        delivery = await send_message(recipient, message)
        return AgentResult(status=Status.SUCCESS, payload=delivery)
    except TransientError:
        raise

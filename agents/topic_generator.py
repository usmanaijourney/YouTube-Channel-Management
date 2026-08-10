"""Topic Generator agent (doc §17 pattern) — stateless, invoked twice per task (TG1 ∥ TG2)."""
from __future__ import annotations

from common.errors import TransientError, ValidationError
from common.message_schema import AgentResult, ErrorInfo, ErrorType, Status, TaskEnvelope
from common.providers.llm import call_llm

SYSTEM_PROMPT_TEMPLATE = """You are a Topic Generator for the YouTube channel "{channel_name}".
Niche: {niche}. Audience: {audience}. Tone: {tone}.
Propose one video topic not already covered in the channel's topic history.
Return structured JSON: {{"title": "...", "research_notes": "..."}}
"""


def _validate_topic(topic: dict) -> None:
    if not topic.get("title", "").strip():
        raise ValidationError("topic_generator: empty title")


async def run(envelope: TaskEnvelope) -> AgentResult:
    channel = envelope.payload["channel_config"]

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        channel_name=channel["name"],
        niche=channel["niche"],
        audience=channel["content_strategy"]["target_audience"],
        tone=channel["content_strategy"]["tone"],
    )

    try:
        topic = await call_llm(system_prompt)
        _validate_topic(topic)
        return AgentResult(status=Status.SUCCESS, payload={"topic": topic})
    except TransientError:
        raise
    except ValidationError as e:
        return AgentResult(
            status=Status.FAILED,
            error=ErrorInfo(type=ErrorType.PERMANENT, message=str(e)),
        )

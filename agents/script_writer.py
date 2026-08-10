"""Script Writer agent — adapted from doc §17's worked example."""
from __future__ import annotations

from common.errors import TransientError, ValidationError
from common.message_schema import AgentResult, ErrorInfo, ErrorType, Status, TaskEnvelope
from common.providers.llm import call_llm

SYSTEM_PROMPT_TEMPLATE = """You are the Script Writer for the YouTube channel "{channel_name}".
Tone: {tone}. Audience: {audience}. Target length: {length_min}-{length_max} minutes.
Follow the channel's brand voice exactly. Do not mention you are an AI.
Return structured JSON: {{"hook": "...", "sections": [...], "cta": "..."}}
"""


def validate_script_schema(script: dict) -> None:
    if not script.get("hook", "").strip():
        raise ValidationError("script_writer: missing hook")
    if not script.get("sections"):
        raise ValidationError("script_writer: no sections")
    if not script.get("cta", "").strip():
        raise ValidationError("script_writer: missing cta")


async def run(envelope: TaskEnvelope) -> AgentResult:
    channel = envelope.payload["channel_config"]
    topic = envelope.payload["approved_topic"]

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        channel_name=channel["name"],
        tone=channel["content_strategy"]["tone"],
        audience=channel["content_strategy"]["target_audience"],
        length_min=channel["content_strategy"]["video_length_minutes"][0],
        length_max=channel["content_strategy"]["video_length_minutes"][1],
    )

    try:
        script = await call_llm(system_prompt, user_prompt=topic["title"] + "\n" + topic["research_notes"])
        validate_script_schema(script)
        return AgentResult(status=Status.SUCCESS, payload={"script": script})
    except TransientError:
        raise
    except ValidationError as e:
        return AgentResult(
            status=Status.FAILED,
            error=ErrorInfo(type=ErrorType.PERMANENT, message=str(e)),
        )

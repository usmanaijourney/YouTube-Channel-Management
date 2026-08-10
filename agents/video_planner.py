"""Video Planner agent — LLM: decides shots/assets, produces a render spec (doc §1 risk #4).

This is the "creative decision" half of the Video Maker; agents/video_renderer.py
is the deterministic "execution" half that actually assembles the video.
"""
from __future__ import annotations

from common.errors import TransientError, ValidationError
from common.message_schema import AgentResult, ErrorInfo, ErrorType, Status, TaskEnvelope
from common.providers.llm import call_llm

SYSTEM_PROMPT_TEMPLATE = """You are the Video Planner for the YouTube channel "{channel_name}".
Visual template: {template}. Asset source: {asset_source}.
Given the script, produce a shot list (visual plan) as a render spec.
Return structured JSON: {{"shots": [...], "template": "..."}}
"""


def _validate_render_spec(spec: dict) -> None:
    if not spec.get("shots"):
        raise ValidationError("video_planner: render spec has no shots")


async def run(envelope: TaskEnvelope) -> AgentResult:
    channel = envelope.payload["channel_config"]
    script = envelope.payload["script"]

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        channel_name=channel["name"],
        template=channel["visual_style"]["template"],
        asset_source=channel["visual_style"]["asset_source"],
    )
    script_text = script["hook"] + " " + " ".join(s["body"] for s in script["sections"])

    try:
        render_spec = await call_llm(system_prompt, user_prompt=script_text)
        _validate_render_spec(render_spec)
        return AgentResult(status=Status.SUCCESS, payload={"render_spec": render_spec})
    except TransientError:
        raise
    except ValidationError as e:
        return AgentResult(
            status=Status.FAILED,
            error=ErrorInfo(type=ErrorType.PERMANENT, message=str(e)),
        )

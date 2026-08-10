"""Voice Over agent — LLM call for SSML/pacing, then a TTS provider call (doc §3 component table)."""
from __future__ import annotations

from common.errors import PermanentError, TransientError, ValidationError
from common.message_schema import AgentResult, ErrorInfo, ErrorType, Status, TaskEnvelope
from common.providers.llm import call_llm
from common.providers.tts import synthesize_speech

SYSTEM_PROMPT = "You are preparing voice-over SSML and pacing notes for a script."


def _script_to_text(script: dict) -> str:
    parts = [script["hook"]]
    for section in script["sections"]:
        parts.append(f"{section['heading']}. {section['body']}")
    parts.append(script["cta"])
    return " ".join(parts)


async def run(envelope: TaskEnvelope) -> AgentResult:
    channel = envelope.payload["channel_config"]
    script = envelope.payload["script"]
    task_id = envelope.task_id

    text = _script_to_text(script)

    try:
        pacing = await call_llm(SYSTEM_PROMPT, user_prompt=text)
        out_path = f"output/{envelope.channel_id}/{task_id}/voice_over.mp3"
        result = await synthesize_speech(
            text=text,
            voice_id=channel["voice"]["voice_id"],
            pace=pacing.get("pace", channel["voice"]["pace"]),
            out_path=out_path,
        )
        if result["duration_seconds"] <= 0:
            raise ValidationError("voice_over: synthesized audio has zero duration")
        return AgentResult(status=Status.SUCCESS, payload={
            "voice_over_path": result["audio_path"],
            "voice_over_duration_seconds": result["duration_seconds"],
        })
    except TransientError:
        raise
    except PermanentError as e:
        return AgentResult(
            status=Status.FAILED,
            error=ErrorInfo(type=ErrorType.PERMANENT, message=str(e)),
        )

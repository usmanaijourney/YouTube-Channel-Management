"""Video Renderer — deterministic worker, no LLM (doc §1 risk #2/#4)."""
from __future__ import annotations

from common.errors import PermanentError, TransientError, ValidationError
from common.message_schema import AgentResult, ErrorInfo, ErrorType, Status, TaskEnvelope
from common.providers.renderer import render_video


async def run(envelope: TaskEnvelope) -> AgentResult:
    render_spec = envelope.payload["render_spec"]
    voice_over_path = envelope.payload["voice_over_path"]
    voice_over_duration_seconds = envelope.payload["voice_over_duration_seconds"]
    task_id = envelope.task_id

    out_path = f"output/{envelope.channel_id}/{task_id}/video.mp4"

    try:
        result = await render_video(render_spec, voice_over_path, voice_over_duration_seconds, out_path)
        if result["duration_seconds"] <= 0:
            raise ValidationError("video_renderer: rendered video has zero duration")
        return AgentResult(status=Status.SUCCESS, payload={
            "video_path": result["video_path"],
            "video_duration_seconds": result["duration_seconds"],
            "thumbnail_path": result["thumbnail_path"],
        })
    except TransientError:
        raise
    except PermanentError as e:
        return AgentResult(
            status=Status.FAILED,
            error=ErrorInfo(type=ErrorType.PERMANENT, message=str(e)),
        )

"""YouTube Uploader agent — scoped credentials, no LLM sees the token (doc §8)."""
from __future__ import annotations

from common.errors import PermanentError, TransientError
from common.message_schema import AgentResult, ErrorInfo, ErrorType, Status, TaskEnvelope
from common.providers.youtube import upload_video


async def run(envelope: TaskEnvelope) -> AgentResult:
    video_path = envelope.payload["video_path"]
    title = envelope.payload["title"]
    description = envelope.payload["description"]
    access_token = envelope.payload["access_token"]

    # Anti-cross-post guard: this agent only ever uploads to the channel that
    # owns this task — enforced again in the deterministic quality gate (§12).
    target_channel_id = envelope.payload["uploader_target_channel_id"]
    if target_channel_id != envelope.channel_id:
        return AgentResult(
            status=Status.FAILED,
            error=ErrorInfo(
                type=ErrorType.PERMANENT,
                message=f"cross-post blocked: task channel={envelope.channel_id} target={target_channel_id}",
            ),
        )

    try:
        result = await upload_video(video_path, title, description, access_token)
        return AgentResult(status=Status.SUCCESS, payload=result)
    except TransientError:
        raise
    except PermanentError as e:
        return AgentResult(
            status=Status.FAILED,
            error=ErrorInfo(type=ErrorType.PERMANENT, message=str(e)),
        )

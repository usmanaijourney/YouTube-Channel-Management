import pytest

from common.message_schema import MessageType, Status, TaskEnvelope

SAMPLE_CHANNEL_CONFIG = {
    "channel_id": "channel-001",
    "name": "TechExplained Daily",
    "niche": "consumer tech explainers",
    "status": "active",
    "schedule": {"videos_per_day": 2, "preferred_hours_utc": [9, 16]},
    "content_strategy": {
        "target_audience": "18-34, tech-curious, non-expert",
        "tone": "energetic, clear, slightly humorous",
        "video_length_minutes": [6, 9],
        "approval_gates": {"topic": False, "script": False, "pre_upload": False},
    },
    "voice": {"provider": "elevenlabs", "voice_id": "voice_ref_xyz", "pace": "medium"},
    "visual_style": {
        "template": "clean-tech-v2",
        "brand_colors": ["#0B0B0F", "#38BDF8"],
        "asset_source": "stock_then_generated",
    },
    "credentials_ref": {
        "youtube": "channel-001/youtube_oauth",
        "whatsapp_recipient": "channel-001/whatsapp_notify_target",
    },
    "notifications": {
        "on_upload_success": True, "on_failure": True,
        "daily_summary": False, "weekly_summary": False,
    },
}


@pytest.fixture
def channel_config():
    return SAMPLE_CHANNEL_CONFIG


def make_envelope(agent_id: str, payload: dict, task_id: str = "task_test") -> TaskEnvelope:
    return TaskEnvelope(
        task_id=task_id,
        channel_id="channel-001",
        agent_id=agent_id,
        message_type=MessageType.TASK_STARTED,
        status=Status.IN_PROGRESS,
        idempotency_key=f"{task_id}-{agent_id}",
        payload=payload,
    )

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ApprovalGates(BaseModel):
    topic: bool = False
    script: bool = False
    pre_upload: bool = False


class ContentStrategy(BaseModel):
    target_audience: str
    tone: str
    video_length_minutes: list[int]
    approval_gates: ApprovalGates


class Schedule(BaseModel):
    videos_per_day: int
    preferred_hours_utc: list[int]


class Voice(BaseModel):
    provider: str
    voice_id: str
    pace: str = "medium"


class VisualStyle(BaseModel):
    template: str
    brand_colors: list[str]
    asset_source: str = "stock_then_generated"


class CredentialsRef(BaseModel):
    youtube: str
    whatsapp_recipient: str


class Notifications(BaseModel):
    on_upload_success: bool = True
    on_failure: bool = True
    daily_summary: bool = False
    weekly_summary: bool = False


class ChannelConfig(BaseModel):
    channel_id: str
    name: str
    niche: str
    status: str
    schedule: Schedule
    content_strategy: ContentStrategy
    voice: Voice
    visual_style: VisualStyle
    credentials_ref: CredentialsRef
    notifications: Notifications


def load_channel_config(path: str | Path) -> ChannelConfig:
    data = yaml.safe_load(Path(path).read_text())
    return ChannelConfig.model_validate(data)

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    HEARTBEAT = "HEARTBEAT"


class Status(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


class ErrorType(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class ErrorInfo(BaseModel):
    type: ErrorType
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class TaskEnvelope(BaseModel):
    """Canonical message envelope, per architecture doc §5."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    channel_id: str
    agent_id: str
    message_type: MessageType
    status: Status
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    error: Optional[ErrorInfo] = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class AgentResult(BaseModel):
    """What an agent function returns to the Channel Manager dispatcher."""

    status: Status
    payload: dict[str, Any] = Field(default_factory=dict)
    error: Optional[ErrorInfo] = None

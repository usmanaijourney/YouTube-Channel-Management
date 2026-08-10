"""Global resource governor (doc §11).

Issues production slots to Channel Managers so many channels can't all fire
at once and stampede shared capacity (YouTube API, TTS, render workers) — a
lightweight token-bucket check, not a per-task approval workflow. Channel
Managers ask for a slot; if none is free they back off and retry later
rather than blocking indefinitely ("Channel Managers queue locally").
"""
from __future__ import annotations

import time
import uuid
from asyncio import Lock
from typing import Optional


class Governor:
    def __init__(self, max_slots: int = 5) -> None:
        self.max_slots = max_slots
        self._active: dict[str, tuple[str, float]] = {}  # slot_id -> (channel_id, acquired_at_monotonic)
        self._lock = Lock()

    async def acquire_slot(self, channel_id: str) -> Optional[str]:
        """Returns a slot_id if granted, else None (caller should back off and retry)."""
        async with self._lock:
            if len(self._active) >= self.max_slots:
                return None
            slot_id = f"slot_{uuid.uuid4().hex[:12]}"
            self._active[slot_id] = (channel_id, time.monotonic())
            return slot_id

    async def release_slot(self, slot_id: str) -> bool:
        async with self._lock:
            return self._active.pop(slot_id, None) is not None

    @property
    def active_count(self) -> int:
        return len(self._active)

    def active_channels(self) -> list[str]:
        return [channel_id for channel_id, _ in self._active.values()]


# Module-level singleton — the orchestrator is a single process (§13: "Always-on, single instance").
governor = Governor()

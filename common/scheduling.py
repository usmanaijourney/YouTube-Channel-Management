"""Pure scheduling math — no scheduler daemon yet, just "when would this next run"
computed from a channel's configured preferred hours. Used by the dashboard to
show a real next-run estimate even though nothing currently triggers runs automatically.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def compute_next_run_utc(preferred_hours_utc: list[int], now: datetime | None = None) -> datetime:
    if not preferred_hours_utc:
        raise ValueError("preferred_hours_utc must be non-empty")

    now = now or datetime.now(timezone.utc)
    today_candidates = sorted(h for h in preferred_hours_utc if h > now.hour or (h == now.hour and now.minute == 0 and now.second == 0))
    if today_candidates:
        hour = today_candidates[0]
        return now.replace(hour=hour, minute=0, second=0, microsecond=0)

    hour = min(preferred_hours_utc)
    return (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)

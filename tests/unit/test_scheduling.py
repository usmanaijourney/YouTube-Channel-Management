from datetime import datetime, timezone

import pytest

from common.scheduling import compute_next_run_utc


def test_next_run_later_today():
    now = datetime(2026, 8, 10, 7, 30, tzinfo=timezone.utc)
    result = compute_next_run_utc([9, 16], now=now)
    assert result == datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc)


def test_next_run_rolls_to_tomorrow_when_all_hours_passed():
    now = datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc)
    result = compute_next_run_utc([9, 16], now=now)
    assert result == datetime(2026, 8, 11, 9, 0, tzinfo=timezone.utc)


def test_next_run_picks_earliest_remaining_hour_today():
    now = datetime(2026, 8, 10, 10, 0, 1, tzinfo=timezone.utc)
    result = compute_next_run_utc([9, 12, 18], now=now)
    assert result == datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def test_empty_hours_raises():
    with pytest.raises(ValueError):
        compute_next_run_utc([])

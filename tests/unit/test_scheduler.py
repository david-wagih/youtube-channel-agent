"""Tests for utils/scheduler.py."""

import pytest

from yt_agent.exceptions import ConfigurationError
from yt_agent.utils.scheduler import calculate_next_publish_time, format_publish_time


def test_invalid_day_raises():
    with pytest.raises(ValueError, match="Invalid day"):
        calculate_next_publish_time(target_day="funday", target_time="19:00", timezone="UTC")


def test_malformed_time_raises_configuration_error():
    with pytest.raises(ConfigurationError, match="Invalid time format"):
        calculate_next_publish_time(target_day="saturday", target_time="not-a-time", timezone="UTC")


def test_time_missing_colon_raises():
    with pytest.raises(ConfigurationError, match="Invalid time format"):
        calculate_next_publish_time(target_day="saturday", target_time="1900", timezone="UTC")


def test_time_out_of_range_raises():
    with pytest.raises(ConfigurationError, match="Time out of range"):
        calculate_next_publish_time(target_day="saturday", target_time="25:00", timezone="UTC")


def test_valid_schedule_returns_saturday():
    result = calculate_next_publish_time(target_day="saturday", target_time="19:00", timezone="UTC")
    assert result.weekday() == 5  # Saturday
    assert result.hour == 19
    assert result.minute == 0


def test_valid_schedule_all_weekdays():
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(days):
        result = calculate_next_publish_time(target_day=day, target_time="10:00", timezone="UTC")
        assert result.weekday() == i, f"Expected weekday {i} for {day}"


def test_result_is_timezone_aware():
    result = calculate_next_publish_time(target_day="saturday", target_time="19:00", timezone="UTC")
    assert result.tzinfo is not None


def test_format_publish_time_contains_day():
    import pytz
    from datetime import datetime

    # March 14 2026 is a Saturday
    dt = datetime(2026, 3, 14, 19, 0, 0, tzinfo=pytz.UTC)
    result = format_publish_time(dt)
    assert "Saturday" in result


def test_scheduled_time_is_in_future():
    from datetime import datetime, timezone

    result = calculate_next_publish_time(target_day="saturday", target_time="19:00", timezone="UTC")
    assert result > datetime.now(timezone.utc)

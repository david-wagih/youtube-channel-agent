"""Scheduling utilities."""

from datetime import datetime, timedelta

import pytz

from ..config import settings

WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def calculate_next_publish_time(
    target_day: str | None = None,
    target_time: str | None = None,
    timezone: str | None = None,
) -> datetime:
    """Calculate the next publish datetime.

    Args:
        target_day: Day of week (e.g., "Saturday"). Defaults to settings.
        target_time: Time in HH:MM format (e.g., "19:00"). Defaults to settings.
        timezone: Timezone name (e.g., "Africa/Cairo"). Defaults to settings.

    Returns:
        datetime object for the next publish time (timezone-aware).
    """
    target_day = (target_day or settings.default_schedule_day).lower()
    target_time = target_time or settings.default_schedule_time
    timezone = timezone or settings.default_timezone

    # Parse time
    hour, minute = map(int, target_time.split(":"))

    # Get target weekday
    target_weekday = WEEKDAY_MAP.get(target_day)
    if target_weekday is None:
        raise ValueError(f"Invalid day: {target_day}. Use: {', '.join(WEEKDAY_MAP.keys())}")

    # Get current time in target timezone
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    # Calculate days until target day
    days_ahead = target_weekday - now.weekday()
    if days_ahead < 0:  # Target day already happened this week
        days_ahead += 7
    elif days_ahead == 0:  # Today is the target day
        # Check if target time has passed
        target_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= target_today:
            days_ahead = 7  # Schedule for next week

    # Calculate target datetime
    target_date = now + timedelta(days=days_ahead)
    target_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return target_datetime


def format_publish_time(dt: datetime) -> str:
    """Format a datetime for display.

    Args:
        dt: The datetime to format.

    Returns:
        Human-readable string like "Saturday, Jan 25 at 7:00 PM".
    """
    return dt.strftime("%A, %b %d at %I:%M %p %Z")

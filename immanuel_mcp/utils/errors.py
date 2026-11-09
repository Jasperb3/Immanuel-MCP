"""Error handling functions"""

import re
import zoneinfo
from datetime import datetime
from typing import Any, Dict

from immanuel.const import chart as chart_const

from .coordinates import parse_coordinate
from .datetimes import parse_datetime_value

VALID_ASPECT_PRIORITIES = ("tight", "moderate", "loose", "all")


def validate_aspect_priority(aspect_priority: str) -> None:
    """Reject an unknown tier instead of quietly treating it as 'tight'."""
    if aspect_priority not in VALID_ASPECT_PRIORITIES:
        raise ValueError(
            f"Unknown aspect_priority '{aspect_priority}'. Valid values: "
            f"{', '.join(VALID_ASPECT_PRIORITIES)}")


def validate_time_status(time_status) -> int:
    """
    The immanuel TIME_* constant for a time_status argument.

    Accepts "known", "approximate" or "unknown" (any case; None means known)
    or the constants 1/2/3, so any value a response echoes is a valid input.
    """
    if time_status is None:
        return chart_const.TIME_KNOWN
    names = {"known": chart_const.TIME_KNOWN, "approximate": chart_const.TIME_APPROXIMATE,
             "unknown": chart_const.TIME_UNKNOWN}
    if isinstance(time_status, str) and time_status.strip().lower() in names:
        return names[time_status.strip().lower()]
    if not isinstance(time_status, bool) and str(time_status).strip() in ("1", "2", "3"):
        return int(str(time_status).strip())
    raise ValueError(
        f"Unknown time_status '{time_status}'. Valid values: known, approximate, "
        f"unknown (approximate: cast at the given time without houses or angles; "
        f"unknown: cast for local noon without them).")


def validate_progression_date(birth_date_time: str, progression_date_time: str) -> None:
    """Secondary progressions run forward from birth."""
    if parse_datetime_value(progression_date_time) < parse_datetime_value(birth_date_time):
        raise ValueError(
            f"progression_date_time {progression_date_time} is before the birth "
            f"date_time {birth_date_time}. Progressions run forward from birth, "
            f"so the progression date must be on or after it.")


def _timezone_error(e: Exception) -> tuple:
    """(message, suggestion) for a zone that could not be loaded. A name
    that is not in the database is a typo, not a missing tzdata; tzdata is
    suggested only when no zone database is installed at all."""
    match = re.search(r"key (.+?)'?$", str(e))
    key = match.group(1) if match else str(e)
    if zoneinfo.available_timezones():
        return (f"Unknown IANA timezone '{key}'.",
                "Use an IANA Region/City name, e.g. 'Europe/London' or 'America/New_York'.")
    return (f"Timezone '{key}' could not be loaded: no IANA time zone database is "
            f"installed. Try installing tzdata: pip install tzdata",
            "Install timezone data: pip install tzdata")


def validate_inputs(date_time: str, latitude: str, longitude: str) -> None:
    """
    Validate input parameters before processing.

    Args:
        date_time: Date and time string
        latitude: Latitude string
        longitude: Longitude string

    Raises:
        ValueError: If any input is invalid
    """
    # Validate datetime format
    try:
        # Try parsing with various formats
        if 'T' in date_time:
            datetime.fromisoformat(date_time.replace('T', ' '))
        else:
            datetime.fromisoformat(date_time)
    except ValueError as e:
        raise ValueError(f"Invalid datetime format: {date_time}. Use ISO format: YYYY-MM-DD HH:MM:SS")

    # Validate coordinates (this also validates ranges)
    parse_coordinate(latitude, is_latitude=True)
    parse_coordinate(longitude, is_latitude=False)


def get_error_suggestion(error_type: str, message: str) -> str:
    """
    Provide helpful suggestions based on error type.

    Args:
        error_type: The type of error that occurred
        message: The error message

    Returns:
        Helpful suggestion string
    """
    if "ValueError" in error_type and "coordinate" in message.lower():
        return "Use formats like: 51.38, 51n23, or 51°23'0\""
    elif "ValueError" in error_type and "datetime" in message.lower():
        return "Use ISO format: 1984-01-11 18:45:00"
    else:
        return "Check the Immanuel documentation for more details"


def handle_chart_error(e: Exception) -> Dict[str, Any]:
    """
    Enhanced error response with more helpful information.

    Args:
        e: The exception that occurred

    Returns:
        Structured error response dictionary
    """
    error_type = type(e).__name__
    suggestion = get_error_suggestion(error_type, str(e))

    # Provide more specific error messages
    if isinstance(e, zoneinfo.ZoneInfoNotFoundError):
        message, suggestion = _timezone_error(e)
    elif "Invalid coordinate" in str(e):
        message = str(e)
    elif "Invalid datetime" in str(e):
        message = str(e)
    else:
        message = str(e)

    return {
        "status": "error",
        "error": True,  # kept for backward compatibility alongside "status"
        "message": message,
        "type": error_type,
        "suggestion": suggestion
    }

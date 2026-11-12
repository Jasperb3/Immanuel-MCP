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


def validate_inputs(date_time: str, latitude: str, longitude: str, timezone: str = None) -> None:
    """
    Validate input parameters before processing, reporting every bad one.

    Checking one at a time hid later mistakes: a bad timezone only showed
    once the coordinates were fixed.

    Args:
        date_time: Date and time string
        latitude: Latitude string
        longitude: Longitude string
        timezone: Optional IANA timezone name

    Raises:
        ValueError: naming every invalid input. A bad timezone on its own
            re-raises the zoneinfo error, as before.
    """
    problems = []
    try:
        datetime.fromisoformat(date_time.replace('T', ' ') if 'T' in date_time else date_time)
    except ValueError as e:
        if str(e).startswith("Invalid isoformat"):
            problems.append(f"Invalid datetime format: {date_time}. Use ISO format: YYYY-MM-DD HH:MM:SS")
        else:
            # The format is fine but the date or time doesn't exist (Feb 30).
            problems.append(f"Invalid datetime {date_time}: {e}.")

    for value, is_latitude in ((latitude, True), (longitude, False)):
        try:
            parse_coordinate(value, is_latitude=is_latitude)
        except ValueError as e:
            problems.append(str(e))

    timezone_error = None
    if timezone:
        try:
            zoneinfo.ZoneInfo(timezone)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError) as e:
            timezone_error = e
            problems.append(f"Unknown IANA timezone '{timezone}'.")

    if timezone_error is not None and len(problems) == 1:
        raise timezone_error
    if problems:
        raise ValueError(" ".join(problems))


class PolarHouseError(ValueError):
    """A house system the Swiss Ephemeris returns unusable cusps for here."""


POLAR_HOUSE_SUGGESTION = "Use house_system='PORPHYRIUS', 'EQUAL' or 'WHOLE_SIGN' for this chart."


class PoleError(ValueError):
    """Houses and angles cast at exactly 90 degrees north or south."""


POLE_SUGGESTION = (
    "Pass time_status='unknown' for a chart without houses and angles, "
    "or a latitude just off the pole such as 89.99.")


def reject_pole(latitude: float, time_status: int = chart_const.TIME_KNOWN) -> None:
    """At exactly 90 degrees north or south the horizon is the celestial
    equator, so the Ascendant and the house cusps are undefined. The Swiss
    Ephemeris returns 0 Aries (or a point tied to the Sun) with no error,
    which made spurious exact aspects. Only a known time casts houses."""
    if isinstance(latitude, str):
        latitude = parse_coordinate(latitude, is_latitude=True)
    if time_status == chart_const.TIME_KNOWN and abs(latitude) >= 90:
        raise PoleError(
            f"Houses and angles can't be cast at latitude {latitude:g}: at the "
            f"pole the horizon is the celestial equator, so the Ascendant, the "
            f"MC and every house cusp are undefined.")


def get_error_suggestion(error_type: str, message: str) -> str:
    """
    Provide helpful suggestions based on error type.

    Args:
        error_type: The type of error that occurred
        message: The error message

    Returns:
        Helpful suggestion string
    """
    if "ValueError" not in error_type:
        return "Check the Immanuel documentation for more details"
    lowered = message.lower()
    parts = []
    if "out of range for month" in lowered or " must be in " in lowered:
        parts.append("Check that the date and time exist (e.g. February has 28 or 29 days).")
    elif "datetime" in lowered:
        parts.append("Use ISO format: 1984-01-11 18:45:00")
    if any(word in lowered for word in ("coordinate", "latitude", "longitude")):
        parts.append("Use formats like: 51.38, 51n23, or 51°23'0\"")
    if "timezone" in lowered:
        parts.append("Use an IANA Region/City name, e.g. 'Europe/London' or 'America/New_York'.")
    return " ".join(parts) or "Check the Immanuel documentation for more details"


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
    elif isinstance(e, PolarHouseError):
        message, suggestion = str(e), POLAR_HOUSE_SUGGESTION
    elif isinstance(e, PoleError):
        message, suggestion = str(e), POLE_SUGGESTION
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

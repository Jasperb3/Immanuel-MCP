"""Error handling functions"""

from datetime import datetime
from typing import Any, Dict
from .coordinates import parse_coordinate


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
    if "ZoneInfoNotFoundError" in error_type:
        return "Install timezone data: pip install tzdata"
    elif "ValueError" in error_type and "coordinate" in message.lower():
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

    # Provide more specific error messages
    if "No time zone found" in str(e):
        message = (f"Timezone error: {str(e)}. "
                  f"Try installing tzdata: pip install tzdata")
    elif "Invalid coordinate" in str(e):
        message = str(e)
    elif "Invalid datetime" in str(e):
        message = str(e)
    else:
        message = str(e)

    return {
        "error": True,
        "message": message,
        "type": error_type,
        "suggestion": get_error_suggestion(error_type, str(e))
    }

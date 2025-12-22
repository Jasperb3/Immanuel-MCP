#!/usr/bin/env python3
"""
Enhanced MCP Server for Immanuel Python Astrology Library

This server exposes the core chart generation and configuration functionalities
of the immanuel astrology library as MCP tools with improved error handling,
input validation, and additional helper functions.
"""

import json
import sys
import logging
import re
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import immanuel
from immanuel import charts
from immanuel.const import chart as chart_const
from immanuel.const import calc as calc_const
from immanuel.const import data as data_const
from immanuel.classes.serialize import ToJSON
from immanuel.tools import convert
from mcp.server.fastmcp import FastMCP
from compact_serializer import CompactJSONSerializer

# Configure logging to file only (CRITICAL: logging to stdout/stderr breaks stdio transport)
# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'immanuel_server.log')

# Configure file-only logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import lifecycle events detection system (after logger is configured)
try:
    from immanuel_mcp.lifecycle import (
        detect_lifecycle_events,
        detect_progressed_moon_return,
        format_lifecycle_event_feed
    )
    LIFECYCLE_AVAILABLE = True
    logger.info("Lifecycle events module loaded successfully")
except ImportError as e:
    logger.warning(f"Lifecycle events module not available: {e}")
    LIFECYCLE_AVAILABLE = False

# Suppress any third-party library logging that might go to stdout/stderr
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# Initialize the MCP server
mcp = FastMCP("immanuel-astrology-server")


# ============================================================================
# Celestial Body Mapping (for optimized responses)
# ============================================================================

CELESTIAL_BODIES = {
    # Angles
    3000001: "Asc",
    3000002: "Desc",
    3000003: "MC",
    3000004: "IC",

    # Planets
    4000001: "Sun",
    4000002: "Moon",
    4000003: "Mercury",
    4000004: "Venus",
    4000006: "Mars",
    4000007: "Jupiter",
    4000008: "Saturn",
    4000009: "Uranus",
    4000010: "Neptune",
    4000011: "Pluto",

    # Minor bodies
    5000001: "Chiron",

    # Points
    6000003: "North Node",
    6000004: "South Node",
    6000005: "Vertex",
    6000007: "Lilith",
    6000010: "Part of Fortune"
}


# ============================================================================
# Response Optimization Helpers
# ============================================================================

def format_position(sign_longitude: Dict[str, Any], sign_name: str) -> str:
    """
    Create a compact position string from sign longitude and sign name.

    Args:
        sign_longitude: Sign longitude dict with 'formatted' field
        sign_name: Name of the zodiac sign

    Returns:
        Compact position string like "28°51' Sagittarius"
    """
    # Extract just degrees and minutes from formatted string (e.g., "28°51'07"" -> "28°51'")
    formatted = sign_longitude.get('formatted', '')
    # Remove seconds portion if present
    if '"' in formatted:
        parts = formatted.split('"')[0]  # Get everything before the seconds marker
        # Reconstruct without seconds
        formatted = parts.strip() + "'"

    return f"{formatted} {sign_name}"


def format_declination(declination: Dict[str, Any]) -> str:
    """
    Create a compact declination string.

    Args:
        declination: Declination dict with 'formatted' field

    Returns:
        Compact declination string like "-23°26'"
    """
    formatted = declination.get('formatted', '')
    # Remove seconds if present
    if '"' in formatted:
        parts = formatted.split('"')[0]
        formatted = parts.strip() + "'"
    return formatted


def extract_primary_dignity(dignities: Dict[str, Any]) -> Optional[str]:
    """
    Extract primary dignity as a simple string.

    Args:
        dignities: Dignities dict from immanuel

    Returns:
        Dignity string like "Ruler", "Exalted", "Detriment", "Fall", or combination
    """
    if not dignities:
        return None

    parts = []

    # Check for primary dignities in order of strength
    if dignities.get('ruler'):
        parts.append('Ruler')
    if dignities.get('exalted'):
        parts.append('Exalted')
    if dignities.get('detriment'):
        parts.append('Detriment')
    if dignities.get('fall'):
        parts.append('Fall')

    # Check for secondary dignities
    if dignities.get('triplicity_ruler'):
        parts.append('Triplicity Ruler')
    if dignities.get('term_ruler'):
        parts.append('Term Ruler')
    if dignities.get('face_ruler'):
        parts.append('Face Ruler')

    if dignities.get('peregrine'):
        parts.append('Peregrine')

    return ', '.join(parts) if parts else None


def build_optimized_transit_positions(transit_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build optimized transit positions using planet names as keys.

    Args:
        transit_data: Full transit chart data from ToJSON serializer

    Returns:
        Optimized dict with planet names as keys
    """
    optimized = {}

    for obj_key, obj_data in transit_data.get('objects', {}).items():
        if not isinstance(obj_data, dict):
            continue

        index = obj_data.get('index')
        if index not in CELESTIAL_BODIES:
            continue  # Skip objects not in our mapping

        name = CELESTIAL_BODIES[index]

        # Build optimized object
        optimized[name] = {
            'position': format_position(
                obj_data.get('sign_longitude', {}),
                obj_data.get('sign', {}).get('name', '')
            ),
            'declination': format_declination(obj_data.get('declination', {})),
            'retrograde': obj_data.get('movement', {}).get('retrograde', False),
            'out_of_bounds': obj_data.get('out_of_bounds', False),
            'house': obj_data.get('house', {}).get('number')
        }

    return optimized


def build_dignities_section(transit_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Build a separate dignities section with planet names as keys.

    Args:
        transit_data: Full transit chart data from ToJSON serializer

    Returns:
        Dict mapping planet names to dignity strings
    """
    dignities = {}

    for obj_key, obj_data in transit_data.get('objects', {}).items():
        if not isinstance(obj_data, dict):
            continue

        index = obj_data.get('index')
        if index not in CELESTIAL_BODIES:
            continue

        name = CELESTIAL_BODIES[index]
        dignity_str = extract_primary_dignity(obj_data.get('dignities', {}))

        if dignity_str:
            dignities[name] = dignity_str

    return dignities


def build_optimized_aspects(aspects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build optimized aspect list with planet names and simplified structure.

    Args:
        aspects: List of aspect dicts from the endpoint

    Returns:
        Optimized aspect list
    """
    optimized = []

    for aspect in aspects:
        if not isinstance(aspect, dict):
            continue

        # Get planet names from active/passive or object1/object2
        active_name = aspect.get('object1')
        passive_name = aspect.get('object2')

        if not active_name or not passive_name:
            # Fallback to numeric lookup if names not present
            active_id = aspect.get('active')
            passive_id = aspect.get('passive')
            active_name = CELESTIAL_BODIES.get(active_id, f"Unknown({active_id})")
            passive_name = CELESTIAL_BODIES.get(passive_id, f"Unknown({passive_id})")

        # Get movement as simple string
        movement = aspect.get('movement', {})
        if isinstance(movement, dict):
            movement_str = movement.get('formatted', 'Unknown')
        else:
            movement_str = str(movement)

        # Build optimized aspect
        optimized_aspect = {
            'planets': f"{active_name} → {passive_name}",
            'type': aspect.get('type'),
            'orb': round(abs(aspect.get('orb', 0)), 2),
            'movement': movement_str,
            'priority': classify_aspect_priority(aspect)
        }

        # Add interpretation if present
        if 'interpretation' in aspect:
            optimized_aspect['interpretation'] = aspect['interpretation']

        # Add keywords if present
        if 'keywords' in aspect:
            optimized_aspect['keywords'] = aspect['keywords']

        # Add nature if present
        if 'nature' in aspect:
            optimized_aspect['nature'] = aspect['nature']

        optimized.append(optimized_aspect)

    return optimized


def parse_coordinate(coord: str, is_latitude: bool = True) -> float:
    """
    Parse coordinate strings in various formats.
    
    Args:
        coord: Coordinate string in various formats
        is_latitude: Whether this is a latitude (for validation)
    
    Returns:
        Decimal coordinate value
        
    Raises:
        ValueError: If coordinate format is invalid or out of range
        
    Examples:
        >>> parse_coordinate("32n43")
        32.71666666666667
        >>> parse_coordinate("-117.15")
        -117.15
        >>> parse_coordinate("51°23'30\"N")
        51.39166666666667
    """
    coord_type = "latitude" if is_latitude else "longitude"
    original_coord = coord  # Keep original for logging
    coord = coord.strip().replace('°', ' ').replace("'", ' ').replace('"', ' ')

    logger.debug(f"Parsing {coord_type}: original='{original_coord}', cleaned='{coord}'")

    # Check for DMS pattern FIRST (before float conversion) to avoid scientific notation issues
    # Pattern for formats like: 32n43, 32N43, 32n43'30, 117w09, 117e09, etc.
    # Pattern for formats like: 32n43, 32N43, 32n43'30, 117w09, etc.
    pattern = r'^(\d+)([nsewNSEW])(\d+)(?:[\'\"]*(\d+))?[\'\"]*$'
    match = re.match(pattern, coord.replace(' ', ''))

    if match:
        degrees = int(match.group(1))
        direction = match.group(2).lower()
        minutes = int(match.group(3)) if match.group(3) else 0
        seconds = int(match.group(4)) if match.group(4) else 0

        logger.debug(f"Matched DMS pattern: {degrees}° {minutes}' {seconds}\" {direction.upper()}")

        decimal = degrees + (minutes / 60) + (seconds / 3600)

        # Apply sign based on direction
        if direction in ['s', 'w']:
            decimal = -decimal

        logger.debug(f"Converted to decimal: {decimal}")

        # Validate range
        if is_latitude and not -90 <= decimal <= 90:
            error_msg = f"Latitude must be between -90 and 90 degrees. Got: {decimal}"
            logger.error(f"DMS range validation failed: {error_msg}")
            raise ValueError(error_msg)
        elif not is_latitude and not -180 <= decimal <= 180:
            error_msg = f"Longitude must be between -180 and 180 degrees. Got: {decimal}"
            logger.error(f"DMS range validation failed: {error_msg}")
            raise ValueError(error_msg)

        logger.debug(f"Successfully parsed and validated {coord_type}: {decimal}")
        return decimal
    
    # Try space-separated format: "32 43 30 N" or "32 43 N"
    logger.debug(f"DMS pattern failed, trying space-separated format")
    parts = coord.upper().split()
    if len(parts) >= 3 and parts[-1] in ['N', 'S', 'E', 'W']:
        try:
            degrees = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 2 else 0
            seconds = int(parts[2]) if len(parts) > 3 else 0
            direction = parts[-1].lower()

            logger.debug(f"Matched space-separated: {degrees}° {minutes}' {seconds}\" {direction.upper()}")

            decimal = degrees + (minutes / 60) + (seconds / 3600)
            if direction in ['s', 'w']:
                decimal = -decimal

            logger.debug(f"Converted to decimal: {decimal}")

            # Validate range
            if is_latitude and not -90 <= decimal <= 90:
                error_msg = f"Latitude must be between -90 and 90 degrees. Got: {decimal}"
                logger.error(f"Space-separated range validation failed: {error_msg}")
                raise ValueError(error_msg)
            elif not is_latitude and not -180 <= decimal <= 180:
                error_msg = f"Longitude must be between -180 and 180 degrees. Got: {decimal}"
                logger.error(f"Space-separated range validation failed: {error_msg}")
                raise ValueError(error_msg)

            logger.debug(f"Successfully parsed and validated {coord_type}: {decimal}")
            return decimal
        except (ValueError, IndexError) as e:
            logger.debug(f"Space-separated parsing failed: {e}")
            pass

    # Finally, try parsing as decimal (after DMS to avoid scientific notation confusion)
    logger.debug(f"Space-separated format failed, trying decimal format")
    try:
        result = float(coord)
        logger.debug(f"Successfully parsed as decimal: {result}")

        # Validate range
        if is_latitude and not -90 <= result <= 90:
            error_msg = f"Latitude must be between -90 and 90 degrees. Got: {result}"
            logger.error(f"Decimal range validation failed: {error_msg}")
            raise ValueError(error_msg)
        elif not is_latitude and not -180 <= result <= 180:
            error_msg = f"Longitude must be between -180 and 180 degrees. Got: {result}"
            logger.error(f"Decimal range validation failed: {error_msg}")
            raise ValueError(error_msg)

        logger.debug(f"Successfully validated {coord_type}: {result}")
        return result
    except ValueError as e:
        if "must be between" in str(e):
            raise  # Re-raise range validation errors
        logger.debug(f"Decimal parsing failed: {e}")

    error_msg = (f"Invalid {coord_type} format: '{original_coord}'. "
                f"Supported formats: decimal (32.71 or -117.15), "
                f"DMS with direction (32n43 or 117w09), "
                f"or space-separated (32 43 30 N)")
    logger.error(error_msg)
    raise ValueError(error_msg)


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


def create_subject(date_time: str, latitude: float, longitude: float, timezone: str = None) -> charts.Subject:
    """
    Create an Immanuel Subject with optional timezone.

    Args:
        date_time: Date and time string in ISO format
        latitude: Parsed latitude as float
        longitude: Parsed longitude as float
        timezone: Optional IANA timezone name

    Returns:
        Configured Subject instance
    """
    subject_kwargs = {
        'date_time': date_time,
        'latitude': latitude,
        'longitude': longitude
    }
    if timezone:
        subject_kwargs['timezone'] = timezone
    return charts.Subject(**subject_kwargs)


def parse_datetime_value(value: Union[str, datetime]) -> datetime:
    """Parse various datetime formats used throughout the API."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Unsupported datetime input: {value!r}")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Empty datetime string")

    # Remove Olson/IANA timezone names (e.g., Europe/London)
    parts = cleaned.split()
    if parts and ('/' in parts[-1] or parts[-1].upper() == parts[-1] and len(parts[-1]) <= 4):
        cleaned = ' '.join(parts[:-1]) if len(parts) > 1 else cleaned

    # Strip trailing timezone offsets or Z markers
    cleaned = re.sub(r'(Z|[+-]\d{2}:?\d{2})$', '', cleaned)

    iso_candidate = cleaned
    if 'T' not in iso_candidate and ' ' in iso_candidate:
        first_space = iso_candidate.find(' ')
        if first_space != -1:
            iso_candidate = iso_candidate[:first_space] + 'T' + iso_candidate[first_space + 1:]
    try:
        return datetime.fromisoformat(iso_candidate)
    except ValueError:
        pass

    fallback_formats = (
        '%a %b %d %Y %H:%M:%S',
        '%a %b %d %Y %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d'
    )
    for fmt in fallback_formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse datetime string: {value}")


def attach_lifecycle_section(
    result: Dict[str, Any],
    natal_chart,
    comparison_chart,
    birth_datetime: Union[str, datetime],
    comparison_datetime: Union[str, datetime],
    include_future: bool = True,
    future_years: int = 20,
    max_future_events: int = 10,
    additional_events: Optional[List[Dict[str, Any]]] = None
) -> None:
    """Populate lifecycle fields on the result dictionary."""
    if not LIFECYCLE_AVAILABLE:
        result["lifecycle_events"] = None
        result["lifecycle_summary"] = None
        return

    try:
        birth_dt = parse_datetime_value(birth_datetime)
        comparison_dt = parse_datetime_value(comparison_datetime)

        lifecycle_data = detect_lifecycle_events(
            natal_chart=natal_chart,
            transit_chart=comparison_chart,
            birth_datetime=birth_dt,
            transit_datetime=comparison_dt,
            include_future=include_future,
            future_years=future_years,
            max_future_events=max_future_events
        )

        payload = format_lifecycle_event_feed(
            lifecycle_data,
            comparison_dt,
            additional_events=additional_events
        )

        result["lifecycle_events"] = payload["events"]
        result["lifecycle_summary"] = payload["summary"]

    except Exception as exc:
        logger.warning("Lifecycle events detection failed: %s", exc, exc_info=True)
        result["lifecycle_events"] = None
        result["lifecycle_summary"] = None


@mcp.tool()
def generate_compact_natal_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Generates a compact natal chart with essential information.

    This tool provides a streamlined version of the natal chart, focusing on the most critical
    astrological data: major celestial objects, their positions, and major aspects. It omits
    more detailed data like weightings and chart shape for a faster and more concise output.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').
                  If not provided, timezone is inferred from coordinates.

    Returns:
        A compact Natal chart object serialized to a JSON dictionary, including simplified
        objects, houses, and aspects.
    """
    try:
        logger.info(f"Generating compact natal chart for {date_time} at {latitude}, {longitude} (tz: {timezone})")

        # Validate inputs first
        validate_inputs(date_time, latitude, longitude)

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate natal chart
        natal = charts.Natal(subject)

        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(natal, cls=CompactJSONSerializer))

        now_dt = datetime.utcnow().replace(microsecond=0)
        try:
            transit_subject = charts.Subject(
                date_time=now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                latitude=lat,
                longitude=lon
            )
            transit_chart = charts.Natal(transit_subject)
            attach_lifecycle_section(
                result,
                natal_chart=natal,
                comparison_chart=transit_chart,
                birth_datetime=date_time,
                comparison_datetime=now_dt
            )
        except Exception as lifecycle_error:
            logger.warning("Lifecycle events unavailable for compact natal chart: %s", lifecycle_error, exc_info=True)
            result["lifecycle_events"] = None
            result["lifecycle_summary"] = None

        logger.info("Compact natal chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating compact natal chart: {str(e)}")
        return handle_chart_error(e)

@mcp.tool()
def generate_natal_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Generates a natal (birth) chart for a specific person or event.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').
                  If not provided, timezone is inferred from coordinates.

    Returns:
        The full Natal chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating natal chart for {date_time} at {latitude}, {longitude} (tz: {timezone})")

        # Validate inputs first
        validate_inputs(date_time, latitude, longitude)

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate natal chart
        natal = charts.Natal(subject)

        # Serialize to JSON
        result = json.loads(json.dumps(natal, cls=ToJSON))

        # Lifecycle analysis uses current transits as reference
        now_dt = datetime.utcnow().replace(microsecond=0)
        try:
            transit_subject = charts.Subject(
                date_time=now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                latitude=lat,
                longitude=lon
            )
            transit_chart = charts.Natal(transit_subject)
            attach_lifecycle_section(
                result,
                natal_chart=natal,
                comparison_chart=transit_chart,
                birth_datetime=date_time,
                comparison_datetime=now_dt
            )
        except Exception as lifecycle_error:
            logger.warning("Lifecycle events unavailable for natal chart: %s", lifecycle_error, exc_info=True)
            result["lifecycle_events"] = None
            result["lifecycle_summary"] = None

        logger.info("Natal chart generated successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error generating natal chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def get_chart_summary(
    date_time: str,
    latitude: str,
    longitude: str,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Get a simplified summary of key chart information.

    Args:
        date_time: The birth date and time in ISO format
        latitude: The latitude of the birth location
        longitude: The longitude of the birth location
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York')

    Returns:
        A simplified summary with just the essential information.
    """
    try:
        logger.info(f"Generating chart summary for {date_time} at {latitude}, {longitude}")

        validate_inputs(date_time, latitude, longitude)

        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        subject = create_subject(date_time, lat, lon, timezone)
        natal = charts.Natal(subject)

        # Extract key information with defensive error handling
        logger.debug(f"Natal chart created successfully. Objects type: {type(natal.objects)}")

        # Access celestial objects
        sun = natal.objects.get(chart_const.SUN)  # Use constant instead of magic number
        moon = natal.objects.get(chart_const.MOON)
        asc = natal.objects.get(chart_const.ASC)

        logger.debug(f"Retrieved objects - Sun: {sun}, Moon: {moon}, Asc: {asc}")

        # Extract sign names with error handling
        try:
            sun_sign = sun.sign.name if (sun and hasattr(sun, 'sign') and hasattr(sun.sign, 'name')) else "Unknown"
            moon_sign = moon.sign.name if (moon and hasattr(moon, 'sign') and hasattr(moon.sign, 'name')) else "Unknown"
            rising_sign = asc.sign.name if (asc and hasattr(asc, 'sign') and hasattr(asc.sign, 'name')) else "Unknown"
        except AttributeError as e:
            logger.error(f"Error accessing sign names: {e}")
            sun_sign = moon_sign = rising_sign = "Unknown"

        # Extract other chart properties with error handling
        try:
            chart_shape = natal.shape if hasattr(natal, 'shape') else "Unknown"
        except Exception as e:
            logger.error(f"Error accessing chart shape: {e}")
            chart_shape = "Unknown"

        try:
            moon_phase = natal.moon_phase.formatted if (hasattr(natal, 'moon_phase') and hasattr(natal.moon_phase, 'formatted')) else "Unknown"
        except Exception as e:
            logger.error(f"Error accessing moon phase: {e}")
            moon_phase = "Unknown"

        try:
            diurnal = natal.diurnal if hasattr(natal, 'diurnal') else None
        except Exception as e:
            logger.error(f"Error accessing diurnal: {e}")
            diurnal = None

        try:
            house_system = natal.house_system if hasattr(natal, 'house_system') else "Unknown"
        except Exception as e:
            logger.error(f"Error accessing house system: {e}")
            house_system = "Unknown"

        result = {
            "sun_sign": sun_sign,
            "moon_sign": moon_sign,
            "rising_sign": rising_sign,
            "chart_shape": chart_shape,
            "moon_phase": moon_phase,
            "diurnal": diurnal,
            "house_system": house_system
        }

        logger.info(f"Chart summary generated successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating chart summary: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def get_planetary_positions(
    date_time: str,
    latitude: str,
    longitude: str,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Get just the planetary positions in a simplified format.

    Args:
        date_time: The birth date and time in ISO format
        latitude: The latitude of the birth location
        longitude: The longitude of the birth location
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York')

    Returns:
        Dictionary containing planetary positions in signs and houses.
    """
    try:
        logger.info(f"Getting planetary positions for {date_time} at {latitude}, {longitude}")

        validate_inputs(date_time, latitude, longitude)

        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        subject = create_subject(date_time, lat, lon, timezone)
        natal = charts.Natal(subject)
        
        planets = {}
        planet_names = {
            4000001: "Sun", 4000002: "Moon", 4000003: "Mercury",
            4000004: "Venus", 4000006: "Mars", 4000007: "Jupiter",
            4000008: "Saturn", 4000009: "Uranus", 4000010: "Neptune",
            4000011: "Pluto"
        }
        
        for planet_id, name in planet_names.items():
            if planet_id in natal.objects:
                planet = natal.objects[planet_id]
                planets[name] = {
                    "sign": planet.sign.name,
                    "degree": planet.sign_longitude.formatted,
                    "house": planet.house.number,
                    "retrograde": planet.movement.retrograde if hasattr(planet, 'movement') else False
                }
        
        result = {"planets": planets}
        logger.info("Planetary positions retrieved successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error getting planetary positions: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_solar_return_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    return_year: int,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Generates a solar return chart for a given year.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        return_year: The year for which to calculate the solar return.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').

    Returns:
        The full SolarReturn chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating solar return chart for {date_time} at {latitude}, {longitude} for year {return_year}")

        # Validate inputs first
        validate_inputs(date_time, latitude, longitude)

        # Validate return year
        if not 1900 <= return_year <= 2100:
            raise ValueError(f"Return year must be between 1900 and 2100. Got: {return_year}")

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate charts
        natal_chart = charts.Natal(subject)
        solar_return = charts.SolarReturn(subject, return_year)

        # Serialize to JSON
        result = json.loads(json.dumps(solar_return, cls=ToJSON))

        solar_return_dt = getattr(solar_return, 'solar_return_date_time', None) or result.get('solar_return_date_time')
        if not solar_return_dt:
            solar_return_dt = f"{return_year}-01-01 00:00:00"

        attach_lifecycle_section(
            result,
            natal_chart=natal_chart,
            comparison_chart=solar_return,
            birth_datetime=date_time,
            comparison_datetime=solar_return_dt
        )

        logger.info("Solar return chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating solar return chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_compact_solar_return_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    return_year: int,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Generates a compact solar return chart for a given year.

    This tool provides a streamlined version of the solar return chart, focusing on the most critical
    astrological data: major celestial objects, their positions, and major aspects. It omits
    more detailed data like weightings and chart shape for a faster and more concise output.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        return_year: The year for which to calculate the solar return.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').

    Returns:
        A compact SolarReturn chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating compact solar return chart for {date_time} at {latitude}, {longitude} for year {return_year}")

        # Validate inputs first
        validate_inputs(date_time, latitude, longitude)

        # Validate return year
        if not 1900 <= return_year <= 2100:
            raise ValueError(f"Return year must be between 1900 and 2100. Got: {return_year}")

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate charts
        natal_chart = charts.Natal(subject)
        solar_return = charts.SolarReturn(subject, return_year)

        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(solar_return, cls=CompactJSONSerializer))

        solar_return_dt = getattr(solar_return, 'solar_return_date_time', None) or result.get('solar_return_date_time')
        if not solar_return_dt:
            solar_return_dt = f"{return_year}-01-01 00:00:00"

        attach_lifecycle_section(
            result,
            natal_chart=natal_chart,
            comparison_chart=solar_return,
            birth_datetime=date_time,
            comparison_datetime=solar_return_dt
        )

        logger.info("Compact solar return chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating compact solar return chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_progressed_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    progression_date_time: str,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Generates a secondary progression chart for a native chart to a specific future date.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        progression_date_time: The date and time to progress the chart to, in ISO format.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').

    Returns:
        The full Progressed chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating progressed chart from {date_time} to {progression_date_time} at {latitude}, {longitude}")

        # Validate inputs
        validate_inputs(date_time, latitude, longitude)
        validate_inputs(progression_date_time, latitude, longitude)  # Reuse validation for progression date

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate charts
        natal_chart = charts.Natal(subject)
        progressed = charts.Progressed(subject, progression_date_time)

        # Serialize to JSON
        result = json.loads(json.dumps(progressed, cls=ToJSON))

        progression_dt_value = getattr(progressed, 'progression_date_time', None) or progression_date_time

        transit_subject = charts.Subject(
            date_time=progression_date_time,
            latitude=lat,
            longitude=lon
        )
        reference_transits = charts.Natal(transit_subject)

        additional_events: List[Dict[str, Any]] = []
        if LIFECYCLE_AVAILABLE:
            try:
                birth_dt = parse_datetime_value(date_time)
                progression_dt = parse_datetime_value(progression_dt_value)
                additional_events = detect_progressed_moon_return(
                    natal_chart,
                    progressed,
                    birth_dt,
                    progression_dt
                )
            except Exception as moon_error:
                logger.debug(f"Progressed Moon detection skipped: {moon_error}")

        attach_lifecycle_section(
            result,
            natal_chart=natal_chart,
            comparison_chart=reference_transits,
            birth_datetime=date_time,
            comparison_datetime=progression_dt_value,
            additional_events=additional_events
        )

        logger.info("Progressed chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating progressed chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_compact_progressed_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    progression_date_time: str,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Generates a compact secondary progression chart for a native chart to a specific future date.

    This tool provides a streamlined version of the progressed chart, focusing on the most critical
    astrological data: major celestial objects, their positions, and major aspects. It omits
    more detailed data like weightings and chart shape for a faster and more concise output.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        progression_date_time: The date and time to progress the chart to, in ISO format.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').

    Returns:
        A compact Progressed chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating compact progressed chart from {date_time} to {progression_date_time} at {latitude}, {longitude}")

        # Validate inputs
        validate_inputs(date_time, latitude, longitude)
        validate_inputs(progression_date_time, latitude, longitude)  # Reuse validation for progression date

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate charts
        natal_chart = charts.Natal(subject)
        progressed = charts.Progressed(subject, progression_date_time)

        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(progressed, cls=CompactJSONSerializer))

        progression_dt_value = getattr(progressed, 'progression_date_time', None) or progression_date_time

        transit_subject = charts.Subject(
            date_time=progression_date_time,
            latitude=lat,
            longitude=lon
        )
        reference_transits = charts.Natal(transit_subject)

        additional_events: List[Dict[str, Any]] = []
        if LIFECYCLE_AVAILABLE:
            try:
                birth_dt = parse_datetime_value(date_time)
                progression_dt = parse_datetime_value(progression_dt_value)
                additional_events = detect_progressed_moon_return(
                    natal_chart,
                    progressed,
                    birth_dt,
                    progression_dt
                )
            except Exception as moon_error:
                logger.debug(f"Progressed Moon detection skipped: {moon_error}")

        attach_lifecycle_section(
            result,
            natal_chart=natal_chart,
            comparison_chart=reference_transits,
            birth_datetime=date_time,
            comparison_datetime=progression_dt_value,
            additional_events=additional_events
        )

        logger.info("Compact progressed chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating compact progressed chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_composite_chart(
    native_date_time: str,
    native_latitude: str,
    native_longitude: str,
    partner_date_time: str,
    partner_latitude: str,
    partner_longitude: str,
    native_timezone: str = None,
    partner_timezone: str = None
) -> Dict[str, Any]:
    """
    Generates a composite (midpoint) chart for two subjects.

    Args:
        native_date_time: The birth date and time of the first subject in ISO format.
        native_latitude: The latitude of the first subject's birth location.
        native_longitude: The longitude of the first subject's birth location.
        partner_date_time: The birth date and time of the second subject in ISO format.
        partner_latitude: The latitude of the second subject's birth location.
        partner_longitude: The longitude of the second subject's birth location.
        native_timezone: Optional IANA timezone for first subject (e.g., 'Europe/London').
        partner_timezone: Optional IANA timezone for second subject (e.g., 'America/New_York').

    Returns:
        The full Composite chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating composite chart between {native_date_time} and {partner_date_time}")

        # Validate inputs for both subjects
        validate_inputs(native_date_time, native_latitude, native_longitude)
        validate_inputs(partner_date_time, partner_latitude, partner_longitude)

        # Parse coordinates for native
        native_lat = parse_coordinate(native_latitude, is_latitude=True)
        native_lon = parse_coordinate(native_longitude, is_latitude=False)

        # Parse coordinates for partner
        partner_lat = parse_coordinate(partner_latitude, is_latitude=True)
        partner_lon = parse_coordinate(partner_longitude, is_latitude=False)
        
        # Create subjects with optional timezones
        native = create_subject(native_date_time, native_lat, native_lon, native_timezone)
        partner = create_subject(partner_date_time, partner_lat, partner_lon, partner_timezone)

        # Generate composite chart
        composite = charts.Composite(native, partner)

        # Serialize to JSON
        result = json.loads(json.dumps(composite, cls=ToJSON))
        logger.info("Composite chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating composite chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_compact_composite_chart(
    native_date_time: str,
    native_latitude: str,
    native_longitude: str,
    partner_date_time: str,
    partner_latitude: str,
    partner_longitude: str,
    native_timezone: str = None,
    partner_timezone: str = None
) -> Dict[str, Any]:
    """
    Generates a compact composite (midpoint) chart for two subjects.

    This tool provides a streamlined version of the composite chart, focusing on the most critical
    astrological data: major celestial objects, their positions, and major aspects. It omits
    more detailed data like weightings and chart shape for a faster and more concise output.

    Args:
        native_date_time: The birth date and time of the first subject in ISO format.
        native_latitude: The latitude of the first subject's birth location.
        native_longitude: The longitude of the first subject's birth location.
        partner_date_time: The birth date and time of the second subject in ISO format.
        partner_latitude: The latitude of the second subject's birth location.
        partner_longitude: The longitude of the second subject's birth location.
        native_timezone: Optional IANA timezone for first subject (e.g., 'Europe/London').
        partner_timezone: Optional IANA timezone for second subject (e.g., 'America/New_York').

    Returns:
        A compact Composite chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating compact composite chart between {native_date_time} and {partner_date_time}")

        # Validate inputs for both subjects
        validate_inputs(native_date_time, native_latitude, native_longitude)
        validate_inputs(partner_date_time, partner_latitude, partner_longitude)

        # Parse coordinates for native
        native_lat = parse_coordinate(native_latitude, is_latitude=True)
        native_lon = parse_coordinate(native_longitude, is_latitude=False)

        # Parse coordinates for partner
        partner_lat = parse_coordinate(partner_latitude, is_latitude=True)
        partner_lon = parse_coordinate(partner_longitude, is_latitude=False)

        # Create subjects with optional timezones
        native = create_subject(native_date_time, native_lat, native_lon, native_timezone)
        partner = create_subject(partner_date_time, partner_lat, partner_lon, partner_timezone)

        # Generate composite chart
        composite = charts.Composite(native, partner)

        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(composite, cls=CompactJSONSerializer))
        logger.info("Compact composite chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating compact composite chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_synastry_aspects(
    native_date_time: str,
    native_latitude: str,
    native_longitude: str,
    partner_date_time: str,
    partner_latitude: str,
    partner_longitude: str,
    native_timezone: str = None,
    partner_timezone: str = None
) -> Dict[str, Any]:
    """
    Calculates the synastry aspects between two charts. This shows how one person's planets aspect another's.

    Args:
        native_date_time: The birth date and time of the first subject (whose chart will contain the aspects).
        native_latitude: The latitude of the first subject's birth location.
        native_longitude: The longitude of the first subject's birth location.
        partner_date_time: The birth date and time of the second subject (whose planets are being aspected).
        partner_latitude: The latitude of the second subject's birth location.
        partner_longitude: The longitude of the second subject's birth location.
        native_timezone: Optional IANA timezone for first subject (e.g., 'Europe/London').
        partner_timezone: Optional IANA timezone for second subject (e.g., 'America/New_York').

    Returns:
        The aspects dictionary from the primary (native) Natal chart object, serialized to JSON.
    """
    try:
        logger.info(f"Generating synastry aspects between {native_date_time} and {partner_date_time}")

        # Validate inputs for both subjects
        validate_inputs(native_date_time, native_latitude, native_longitude)
        validate_inputs(partner_date_time, partner_latitude, partner_longitude)

        # Parse coordinates for native
        native_lat = parse_coordinate(native_latitude, is_latitude=True)
        native_lon = parse_coordinate(native_longitude, is_latitude=False)

        # Parse coordinates for partner
        partner_lat = parse_coordinate(partner_latitude, is_latitude=True)
        partner_lon = parse_coordinate(partner_longitude, is_latitude=False)

        # Create subjects with optional timezones
        native_subject = create_subject(native_date_time, native_lat, native_lon, native_timezone)
        partner_subject = create_subject(partner_date_time, partner_lat, partner_lon, partner_timezone)
        
        # Create partner chart first
        partner_chart = charts.Natal(partner_subject)
        
        # Create native chart with aspects to partner
        native_chart = charts.Natal(native_subject, aspects_to=partner_chart)
        
        # Extract and return aspects
        chart_data = json.loads(json.dumps(native_chart, cls=ToJSON))
        result = chart_data.get('aspects', {})
        logger.info("Synastry aspects generated successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error generating synastry aspects: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_compact_synastry_aspects(
    native_date_time: str,
    native_latitude: str,
    native_longitude: str,
    partner_date_time: str,
    partner_latitude: str,
    partner_longitude: str,
    native_timezone: str = None,
    partner_timezone: str = None,
    include_interpretations: bool = True
) -> Dict[str, Any]:
    """
    Calculates compact synastry aspects between two charts, filtered to show only major aspects between major objects.

    This tool provides a streamlined version of synastry aspects, focusing on the most critical
    astrological connections: major aspects between major celestial objects only. It omits
    minor aspects and minor objects for a faster and more concise output.

    Args:
        native_date_time: The birth date and time of the first subject (whose chart will contain the aspects).
        native_latitude: The latitude of the first subject's birth location.
        native_longitude: The longitude of the first subject's birth location.
        partner_date_time: The birth date and time of the second subject (whose planets are being aspected).
        partner_latitude: The latitude of the second subject's birth location.
        partner_longitude: The longitude of the second subject's birth location.
        native_timezone: Optional IANA timezone for first subject (e.g., 'Europe/London').
        partner_timezone: Optional IANA timezone for second subject (e.g., 'America/New_York').
        include_interpretations: Include aspect interpretation keywords (default: True).

    Returns:
        Filtered synastry aspects showing only major aspects between major objects.
    """
    try:
        logger.info(f"Generating compact synastry aspects between {native_date_time} and {partner_date_time}")

        # Validate inputs for both subjects
        validate_inputs(native_date_time, native_latitude, native_longitude)
        validate_inputs(partner_date_time, partner_latitude, partner_longitude)

        # Parse coordinates for native
        native_lat = parse_coordinate(native_latitude, is_latitude=True)
        native_lon = parse_coordinate(native_longitude, is_latitude=False)

        # Parse coordinates for partner
        partner_lat = parse_coordinate(partner_latitude, is_latitude=True)
        partner_lon = parse_coordinate(partner_longitude, is_latitude=False)

        # Create subjects with optional timezones
        native_subject = create_subject(native_date_time, native_lat, native_lon, native_timezone)
        partner_subject = create_subject(partner_date_time, partner_lat, partner_lon, partner_timezone)
        
        # Create partner chart first
        partner_chart = charts.Natal(partner_subject)

        # Create native chart with aspects to partner
        native_chart = charts.Natal(native_subject, aspects_to=partner_chart)

        # Serialize the entire chart using compact serializer to get filtered aspects
        compact_chart_data = json.loads(json.dumps(native_chart, cls=CompactJSONSerializer))
        filtered_aspects = compact_chart_data.get('aspects', [])

        # Add interpretation hints if requested
        if include_interpretations:
            filtered_aspects = add_aspect_interpretations(filtered_aspects)

        result = {"aspects": filtered_aspects}
        logger.info("Compact synastry aspects generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating compact synastry aspects: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_transit_chart(
    latitude: str,
    longitude: str
) -> Dict[str, Any]:
    """
    Generates a chart for the current moment for a given location, showing current planetary positions.

    Args:
        latitude: The latitude of the location, e.g., '32n43'.
        longitude: The longitude of the location, e.g., '117w09'.

    Returns:
        The full Transits chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating transit chart for current time at {latitude}, {longitude}")
        
        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)
        
        # Generate transits chart
        transits = charts.Transits(latitude=lat, longitude=lon)
        
        # Serialize to JSON
        result = json.loads(json.dumps(transits, cls=ToJSON))
        logger.info("Transit chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating transit chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_compact_transit_chart(
    latitude: str,
    longitude: str
) -> Dict[str, Any]:
    """
    Generates a compact chart for the current moment for a given location, showing current planetary positions with filtering.
    
    This tool provides a streamlined version of the transit chart, focusing on the most critical
    astrological data: major celestial objects and their current positions. It omits
    minor objects and detailed properties for a faster and more concise output.
    
    Args:
        latitude: The latitude of the location, e.g., '32n43'.
        longitude: The longitude of the location, e.g., '117w09'.
    
    Returns:
        A compact Transits chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating compact transit chart for current time at {latitude}, {longitude}")
        
        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)
        
        # Generate transits chart
        transits = charts.Transits(latitude=lat, longitude=lon)
        
        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(transits, cls=CompactJSONSerializer))
        logger.info("Compact transit chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating compact transit chart: {str(e)}")
        return handle_chart_error(e)


# Aspect interpretation keywords for enhanced output
ASPECT_INTERPRETATIONS = {
    'conjunction': {
        'keywords': ['fusion', 'intensity', 'new beginnings'],
        'nature': 'variable',
        'description': 'Merging of energies, can be harmonious or challenging depending on planets'
    },
    'opposition': {
        'keywords': ['tension', 'awareness', 'projection', 'relationships'],
        'nature': 'challenging',
        'description': 'Polarization requiring integration and balance'
    },
    'square': {
        'keywords': ['friction', 'action', 'challenge', 'growth'],
        'nature': 'challenging',
        'description': 'Dynamic tension that motivates change and development'
    },
    'trine': {
        'keywords': ['harmony', 'flow', 'ease', 'talent'],
        'nature': 'benefic',
        'description': 'Natural gifts and smooth energy flow'
    },
    'sextile': {
        'keywords': ['opportunity', 'cooperation', 'skill'],
        'nature': 'benefic',
        'description': 'Supportive energy that requires activation'
    },
    'quincunx': {
        'keywords': ['adjustment', 'health', 'service'],
        'nature': 'variable',
        'description': 'Requires adaptation and fine-tuning'
    },
    'semi-sextile': {
        'keywords': ['subtle', 'growth', 'awareness'],
        'nature': 'minor',
        'description': 'Mild supportive influence requiring attention'
    },
    'semi-square': {
        'keywords': ['irritation', 'minor friction', 'motivation'],
        'nature': 'minor challenging',
        'description': 'Minor tension that prompts small adjustments'
    },
    'sesquiquadrate': {
        'keywords': ['agitation', 'restlessness', 'drive'],
        'nature': 'minor challenging',
        'description': 'Persistent tension requiring resolution'
    }
}


# Planet combination specific interpretations
# Format: (planet1, planet2, aspect_type): {keywords, nature, description}
PLANET_COMBINATION_INTERPRETATIONS = {
    # Sun combinations (9 entries)
    ('Moon', 'Sun', 'conjunction'): {
        'keywords': ['integration', 'wholeness', 'new beginning', 'conscious emotion'],
        'nature': 'variable',
        'description': 'Unity of will and feeling, emotional clarity'
    },
    ('Sun', 'Venus', 'conjunction'): {
        'keywords': ['charm', 'creativity', 'pleasure', 'self-worth', 'beauty'],
        'nature': 'benefic',
        'description': 'Enhanced attractiveness and creative self-expression'
    },
    ('Mars', 'Sun', 'conjunction'): {
        'keywords': ['courage', 'drive', 'assertion', 'action', 'potential conflict'],
        'nature': 'variable',
        'description': 'Dynamic energy, assertiveness, need for action'
    },
    ('Jupiter', 'Sun', 'conjunction'): {
        'keywords': ['confidence', 'expansion', 'opportunity', 'optimism', 'success'],
        'nature': 'benefic',
        'description': 'Enhanced vitality, confidence, and opportunities for growth'
    },
    ('Saturn', 'Sun', 'conjunction'): {
        'keywords': ['discipline', 'responsibility', 'limitation', 'maturity', 'challenge'],
        'nature': 'variable',
        'description': 'Serious focus, self-discipline, karmic lessons'
    },
    ('Sun', 'Uranus', 'conjunction'): {
        'keywords': ['innovation', 'independence', 'breakthrough', 'sudden change', 'awakening'],
        'nature': 'inspirational',
        'description': 'Unique self-expression, sudden insights, need for freedom'
    },
    ('Neptune', 'Sun', 'conjunction'): {
        'keywords': ['inspiration', 'spirituality', 'idealism', 'confusion', 'transcendence'],
        'nature': 'inspirational',
        'description': 'Heightened sensitivity, spiritual awareness, potential confusion about identity'
    },
    ('Pluto', 'Sun', 'conjunction'): {
        'keywords': ['transformation', 'power', 'intensity', 'rebirth', 'control'],
        'nature': 'transformative',
        'description': 'Deep transformation of identity, power dynamics, regeneration'
    },
    ('Mercury', 'Sun', 'conjunction'): {
        'keywords': ['mental clarity', 'communication', 'learning', 'awareness', 'thought'],
        'nature': 'variable',
        'description': 'Enhanced mental focus, clear communication of will'
    },

    # Moon combinations (8 entries - Sun already covered above)
    ('Moon', 'Venus', 'conjunction'): {
        'keywords': ['emotional harmony', 'love', 'comfort', 'nurturing', 'beauty'],
        'nature': 'benefic',
        'description': 'Emotional warmth, artistic sensitivity, need for harmony'
    },
    ('Mars', 'Moon', 'conjunction'): {
        'keywords': ['emotional intensity', 'reactive', 'passion', 'urgency', 'defensiveness'],
        'nature': 'variable',
        'description': 'Emotional volatility, instinctive action, protective impulses'
    },
    ('Jupiter', 'Moon', 'conjunction'): {
        'keywords': ['emotional generosity', 'optimism', 'protection', 'abundance', 'faith'],
        'nature': 'benefic',
        'description': 'Emotional expansiveness, faith, generosity of feeling'
    },
    ('Moon', 'Saturn', 'conjunction'): {
        'keywords': ['emotional control', 'seriousness', 'duty', 'restriction', 'maturity'],
        'nature': 'variable',
        'description': 'Emotional reserve, sense of duty, need for security'
    },
    ('Moon', 'Uranus', 'conjunction'): {
        'keywords': ['emotional freedom', 'unpredictability', 'excitement', 'change', 'awakening'],
        'nature': 'inspirational',
        'description': 'Emotional independence, sudden mood changes, need for excitement'
    },
    ('Moon', 'Neptune', 'conjunction'): {
        'keywords': ['emotional sensitivity', 'empathy', 'psychic', 'idealism', 'confusion'],
        'nature': 'inspirational',
        'description': 'Deep emotional sensitivity, psychic receptivity, boundary dissolution'
    },
    ('Moon', 'Pluto', 'conjunction'): {
        'keywords': ['emotional transformation', 'intensity', 'depth', 'power', 'catharsis'],
        'nature': 'transformative',
        'description': 'Deep emotional transformation, powerful feelings, psychological insight'
    },
    ('Mercury', 'Moon', 'conjunction'): {
        'keywords': ['emotional expression', 'intuitive thinking', 'communication', 'memory', 'perception'],
        'nature': 'variable',
        'description': 'Integration of feeling and thought, emotional intelligence'
    },

    # Mercury combinations (7 entries - Sun and Moon already covered)
    ('Mercury', 'Venus', 'conjunction'): {
        'keywords': ['diplomatic', 'artistic expression', 'charm', 'pleasant communication', 'aesthetics'],
        'nature': 'benefic',
        'description': 'Charming communication, artistic thinking, diplomatic expression'
    },
    ('Mars', 'Mercury', 'conjunction'): {
        'keywords': ['quick thinking', 'sharp speech', 'debate', 'mental energy', 'argument'],
        'nature': 'variable',
        'description': 'Quick, decisive thinking, assertive communication, potential arguments'
    },
    ('Jupiter', 'Mercury', 'conjunction'): {
        'keywords': ['optimistic thinking', 'learning', 'wisdom', 'teaching', 'expansion'],
        'nature': 'benefic',
        'description': 'Optimistic mindset, love of learning, philosophical thinking'
    },
    ('Mercury', 'Saturn', 'conjunction'): {
        'keywords': ['serious thinking', 'concentration', 'practicality', 'criticism', 'discipline'],
        'nature': 'variable',
        'description': 'Methodical thinking, concentration, practical communication'
    },
    ('Mercury', 'Uranus', 'conjunction'): {
        'keywords': ['innovative thinking', 'genius', 'originality', 'sudden insight', 'unconventional'],
        'nature': 'inspirational',
        'description': 'Original thinking, sudden insights, unconventional communication'
    },
    ('Mercury', 'Neptune', 'conjunction'): {
        'keywords': ['imaginative thinking', 'intuition', 'creativity', 'confusion', 'inspiration'],
        'nature': 'inspirational',
        'description': 'Imaginative thinking, intuitive perception, potential for confusion'
    },
    ('Mercury', 'Pluto', 'conjunction'): {
        'keywords': ['deep thinking', 'penetrating insight', 'persuasion', 'obsession', 'research'],
        'nature': 'transformative',
        'description': 'Penetrating mind, investigative thinking, transformative ideas'
    },

    # Venus combinations (6 entries - Sun, Moon, Mercury already covered)
    ('Mars', 'Venus', 'conjunction'): {
        'keywords': ['passion', 'attraction', 'desire', 'creativity', 'magnetism'],
        'nature': 'variable',
        'description': 'Passionate attraction, creative drive, sexual magnetism'
    },
    ('Jupiter', 'Venus', 'conjunction'): {
        'keywords': ['joy', 'abundance', 'love', 'generosity', 'beauty'],
        'nature': 'benefic',
        'description': 'Enhanced love and beauty, social success, generosity'
    },
    ('Saturn', 'Venus', 'conjunction'): {
        'keywords': ['commitment', 'loyalty', 'limitation', 'seriousness', 'duty in love'],
        'nature': 'variable',
        'description': 'Serious commitment, loyalty, potential restriction in love'
    },
    ('Uranus', 'Venus', 'conjunction'): {
        'keywords': ['unconventional love', 'excitement', 'freedom', 'attraction', 'change'],
        'nature': 'inspirational',
        'description': 'Unconventional relationships, sudden attractions, need for freedom in love'
    },
    ('Neptune', 'Venus', 'conjunction'): {
        'keywords': ['romantic idealism', 'spiritual love', 'compassion', 'illusion', 'transcendence'],
        'nature': 'inspirational',
        'description': 'Idealistic love, spiritual connection, potential for illusion'
    },
    ('Pluto', 'Venus', 'conjunction'): {
        'keywords': ['intense love', 'transformation', 'passion', 'obsession', 'depth'],
        'nature': 'transformative',
        'description': 'Intense, transformative love, deep passion, power in relationships'
    },

    # Mars combinations (5 entries - Sun, Moon, Mercury, Venus already covered)
    ('Jupiter', 'Mars', 'conjunction'): {
        'keywords': ['enthusiasm', 'courage', 'adventure', 'success', 'excess energy'],
        'nature': 'benefic',
        'description': 'Enthusiastic action, courage, success through initiative'
    },
    ('Mars', 'Saturn', 'conjunction'): {
        'keywords': ['controlled energy', 'frustration', 'discipline', 'endurance', 'strategic'],
        'nature': 'variable',
        'description': 'Disciplined action, controlled energy, potential frustration'
    },
    ('Mars', 'Uranus', 'conjunction'): {
        'keywords': ['sudden action', 'rebellion', 'innovation', 'breakthrough', 'impulsiveness'],
        'nature': 'inspirational',
        'description': 'Sudden, innovative action, breakthrough energy, potential recklessness'
    },
    ('Mars', 'Neptune', 'conjunction'): {
        'keywords': ['inspired action', 'confusion', 'idealism', 'spiritual drive', 'deception'],
        'nature': 'inspirational',
        'description': 'Inspired action, spiritual drive, potential confusion or deception'
    },
    ('Mars', 'Pluto', 'conjunction'): {
        'keywords': ['intense power', 'transformation', 'force', 'control', 'regeneration'],
        'nature': 'transformative',
        'description': 'Powerful transformative energy, intense drive, potential for control issues'
    },

    # Jupiter combinations (4 entries - Sun, Moon, Mercury, Venus, Mars already covered)
    ('Jupiter', 'Saturn', 'conjunction'): {
        'keywords': ['balanced growth', 'wisdom', 'structure', 'social order', 'responsibility'],
        'nature': 'variable',
        'description': 'Balance between expansion and contraction, structured growth'
    },
    ('Jupiter', 'Uranus', 'conjunction'): {
        'keywords': ['breakthrough', 'innovation', 'opportunity', 'freedom', 'sudden expansion'],
        'nature': 'inspirational',
        'description': 'Sudden opportunities, innovative growth, breakthrough expansion'
    },
    ('Jupiter', 'Neptune', 'conjunction'): {
        'keywords': ['spiritual growth', 'idealism', 'compassion', 'faith', 'inspiration'],
        'nature': 'inspirational',
        'description': 'Spiritual expansion, idealistic vision, compassionate growth'
    },
    ('Jupiter', 'Pluto', 'conjunction'): {
        'keywords': ['transformation', 'power', 'success', 'intensity', 'regeneration'],
        'nature': 'transformative',
        'description': 'Powerful transformation, deep growth, success through transformation'
    },

    # Saturn combinations (3 entries - Sun, Moon, Mercury, Venus, Mars, Jupiter already covered)
    ('Saturn', 'Uranus', 'conjunction'): {
        'keywords': ['structured innovation', 'rebellion vs authority', 'breakthrough', 'tension', 'reform'],
        'nature': 'variable',
        'description': 'Tension between old and new, structured innovation, reform'
    },
    ('Neptune', 'Saturn', 'conjunction'): {
        'keywords': ['practical idealism', 'manifesting dreams', 'discipline', 'reality check', 'structure'],
        'nature': 'variable',
        'description': 'Manifesting ideals into reality, practical spirituality'
    },
    ('Pluto', 'Saturn', 'conjunction'): {
        'keywords': ['deep transformation', 'power', 'authority', 'reconstruction', 'karmic'],
        'nature': 'transformative',
        'description': 'Deep structural transformation, karmic authority, rebuilding foundations'
    },

    # Outer planet combinations (3 entries)
    ('Neptune', 'Uranus', 'conjunction'): {
        'keywords': ['visionary', 'spiritual awakening', 'innovation', 'idealism', 'inspiration'],
        'nature': 'inspirational',
        'description': 'Visionary innovation, spiritual awakening, inspired idealism'
    },
    ('Pluto', 'Uranus', 'conjunction'): {
        'keywords': ['revolutionary', 'breakthrough', 'transformation', 'liberation', 'upheaval'],
        'nature': 'transformative',
        'description': 'Revolutionary transformation, breakthrough change, liberation'
    },
    ('Neptune', 'Pluto', 'conjunction'): {
        'keywords': ['spiritual transformation', 'collective evolution', 'deep healing', 'transcendence', 'regeneration'],
        'nature': 'transformative',
        'description': 'Deep spiritual transformation, collective regeneration'
    },

    # Opposition aspects - key planet pairs
    ('Moon', 'Sun', 'opposition'): {
        'keywords': ['awareness', 'tension', 'full moon energy', 'relationship', 'culmination'],
        'nature': 'variable',
        'description': 'Conscious awareness of inner dynamics, relationship tension'
    },
    ('Jupiter', 'Sun', 'opposition'): {
        'keywords': ['overconfidence', 'expansion', 'growth through challenge', 'excess', 'learning'],
        'nature': 'growth-oriented',
        'description': 'Growth through opposition, learning through excess or overconfidence'
    },
    ('Saturn', 'Sun', 'opposition'): {
        'keywords': ['restriction', 'authority conflict', 'maturity', 'responsibility', 'limitation'],
        'nature': 'challenging',
        'description': 'Tension with authority, learning discipline and responsibility'
    },

    # Square aspects - key planet pairs
    ('Mars', 'Sun', 'square'): {
        'keywords': ['conflict', 'assertion', 'energy blocks', 'frustration', 'action'],
        'nature': 'challenging',
        'description': 'Energy conflicts, frustration leading to action, assertion challenges'
    },
    ('Jupiter', 'Sun', 'square'): {
        'keywords': ['overextension', 'growth', 'learning', 'excess', 'opportunity through challenge'],
        'nature': 'growth-oriented',
        'description': 'Growth through overextension, learning from excess'
    },
    ('Saturn', 'Sun', 'square'): {
        'keywords': ['obstacle', 'discipline', 'limitation', 'hard work', 'maturity'],
        'nature': 'challenging',
        'description': 'Obstacles requiring discipline, hard work leading to maturity'
    },
    ('Mars', 'Moon', 'square'): {
        'keywords': ['emotional tension', 'reactive', 'anger', 'urgency', 'action'],
        'nature': 'challenging',
        'description': 'Emotional volatility, reactive behavior, urgency to act'
    },

    # Trine aspects - key planet pairs
    ('Jupiter', 'Sun', 'trine'): {
        'keywords': ['confidence', 'success', 'growth', 'opportunity', 'optimism'],
        'nature': 'benefic',
        'description': 'Natural confidence, easy growth opportunities, success'
    },
    ('Saturn', 'Sun', 'trine'): {
        'keywords': ['discipline', 'achievement', 'structure', 'maturity', 'endurance'],
        'nature': 'benefic',
        'description': 'Natural discipline, steady achievement, structured success'
    },
    ('Mars', 'Sun', 'trine'): {
        'keywords': ['energy', 'courage', 'action', 'vitality', 'success'],
        'nature': 'benefic',
        'description': 'Natural energy flow, courageous action, vital success'
    },
    ('Moon', 'Sun', 'trine'): {
        'keywords': ['harmony', 'emotional balance', 'flow', 'integration', 'ease'],
        'nature': 'benefic',
        'description': 'Natural harmony between will and feeling, emotional ease'
    },

    # Sextile aspects - key planet pairs
    ('Jupiter', 'Sun', 'sextile'): {
        'keywords': ['opportunity', 'growth', 'optimism', 'potential', 'expansion'],
        'nature': 'benefic',
        'description': 'Growth opportunities requiring initiative, positive potential'
    },
    ('Saturn', 'Sun', 'sextile'): {
        'keywords': ['practical', 'opportunity', 'discipline', 'achievement', 'structure'],
        'nature': 'benefic',
        'description': 'Practical opportunities, disciplined achievement'
    },
    ('Mars', 'Sun', 'sextile'): {
        'keywords': ['energy', 'opportunity', 'action', 'initiative', 'courage'],
        'nature': 'benefic',
        'description': 'Energetic opportunities, action-oriented initiative'
    },
}


def get_planet_pair_key(obj1: str, obj2: str, aspect_type: str) -> tuple:
    """Create normalized key for planet pair lookups (alphabetically sorted)."""
    planets = sorted([obj1, obj2])
    return (planets[0], planets[1], aspect_type.lower())


def get_context_aware_interpretation(obj1: str, obj2: str, aspect_type: str) -> Dict[str, Any]:
    """
    Get interpretation based on planet combination and aspect type.

    Priority:
    1. Exact planet-pair + aspect match
    2. Jupiter benefic bias (growth-oriented for square/opposition)
    3. Pluto/Chiron = transformative
    4. Neptune/Uranus = inspirational
    5. Generic aspect interpretation (fallback)
    """
    # Try planet-specific interpretation first
    pair_key = get_planet_pair_key(obj1, obj2, aspect_type)
    if pair_key in PLANET_COMBINATION_INTERPRETATIONS:
        return PLANET_COMBINATION_INTERPRETATIONS[pair_key]

    # Jupiter benefic bias
    if 'Jupiter' in [obj1, obj2] and aspect_type.lower() in ['opposition', 'square']:
        return {
            'keywords': ['growth', 'expansion', 'excess', 'learning', 'opportunity'],
            'nature': 'growth-oriented',
            'description': f'Jupiter {aspect_type} brings growth through challenge'
        }

    # Pluto/Chiron = transformative
    if any(p in [obj1, obj2] for p in ['Pluto', 'Chiron']):
        base_interp = ASPECT_INTERPRETATIONS.get(aspect_type.lower(), {})
        return {
            'keywords': base_interp.get('keywords', []) + ['transformation'],
            'nature': 'transformative',
            'description': base_interp.get('description', '')
        }

    # Neptune/Uranus = inspirational
    if any(p in [obj1, obj2] for p in ['Neptune', 'Uranus']):
        base_interp = ASPECT_INTERPRETATIONS.get(aspect_type.lower(), {})
        return {
            'keywords': base_interp.get('keywords', []) + ['inspiration'],
            'nature': 'inspirational',
            'description': base_interp.get('description', '')
        }

    # Fallback to generic
    return ASPECT_INTERPRETATIONS.get(aspect_type.lower(), {
        'keywords': ['energy', 'connection', 'influence'],
        'nature': 'variable',
        'description': 'Planetary interaction'
    })


def normalize_aspects_to_list(aspects: Union[List[Dict[str, Any]], Dict[str, Any]],
                              filter_self_aspects: bool = True) -> List[Dict[str, Any]]:
    """
    Normalize aspects data to a flat list format and optionally filter self-aspects.

    The compact serializer returns aspects as a list for regular charts,
    but synastry/transit charts with aspects_to may return nested dicts.

    Args:
        aspects: Either a list of aspect dicts, or a nested dict structure
                 from synastry/transit charts
        filter_self_aspects: If True, remove aspects where active == passive
                           (default: True, as self-aspects are astrologically meaningless)

    Returns:
        Flat list of aspect dictionaries with self-aspects removed
    """
    aspect_list = []

    if isinstance(aspects, list):
        aspect_list = aspects
    elif isinstance(aspects, dict):
        # Handle nested dict format: {from_id: {to_id: aspect_data}}
        for from_key, to_aspects in aspects.items():
            if isinstance(to_aspects, dict):
                for to_key, aspect_data in to_aspects.items():
                    if isinstance(aspect_data, dict):
                        aspect_list.append(aspect_data)

    # Filter out self-aspects if requested
    if filter_self_aspects:
        original_count = len(aspect_list)
        aspect_list = [
            asp for asp in aspect_list
            if isinstance(asp, dict) and asp.get('active') != asp.get('passive')
        ]
        filtered_count = original_count - len(aspect_list)
        if filtered_count > 0:
            logger.debug(f"Filtered {filtered_count} self-aspects, {len(aspect_list)} aspects remaining")

    return aspect_list


def add_aspect_interpretations(aspects: Union[List[Dict[str, Any]], Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhance aspect data with context-aware interpretation based on planet combinations.

    Args:
        aspects: List of aspect dictionaries or nested dict structure

    Returns:
        Enhanced aspect list with planet-pair specific interpretation keywords
    """
    # Normalize to list and filter self-aspects
    aspect_list = normalize_aspects_to_list(aspects, filter_self_aspects=True)

    enhanced = []
    for aspect in aspect_list:
        if not isinstance(aspect, dict):
            continue

        obj1 = aspect.get('object1', '')
        obj2 = aspect.get('object2', '')
        aspect_type = aspect.get('type', '')

        # Get context-aware interpretation
        interp = get_context_aware_interpretation(obj1, obj2, aspect_type)

        aspect['keywords'] = interp.get('keywords', [])
        aspect['nature'] = interp.get('nature', 'variable')

        # Optional detailed interpretation
        if 'description' in interp:
            aspect['interpretation'] = interp['description']

        enhanced.append(aspect)

    logger.debug(f"Added context-aware interpretations to {len(enhanced)} aspects")
    return enhanced


# ============================================================================
# Aspect Pagination Helpers (for MCP size limit compliance)
# ============================================================================

def classify_aspect_priority(aspect: dict) -> str:
    """
    Classify aspect by orb into priority tiers.

    Tight aspects (0-2°): Peak influence, most noticeable effects
    Moderate aspects (2-5°): Secondary influence, still noticeable
    Loose aspects (5-8°): Background influence, subtle effects

    Args:
        aspect: Aspect dictionary with 'orb' field

    Returns:
        "tight", "moderate", or "loose"
    """
    orb = abs(aspect.get('orb', 0))

    if orb <= 2.0:
        return "tight"
    elif orb <= 5.0:
        return "moderate"
    else:
        return "loose"


def filter_aspects_by_priority(aspects: list, priority: str) -> list:
    """
    Filter aspects to only those matching the specified priority tier.

    Args:
        aspects: List of aspect dictionaries
        priority: "tight", "moderate", "loose", or "all"

    Returns:
        Filtered list of aspects
    """
    if priority == "all":
        return aspects

    return [asp for asp in aspects if classify_aspect_priority(asp) == priority]


def classify_all_aspects(aspects: list) -> tuple:
    """
    Classify all aspects into priority tiers.

    Args:
        aspects: List of aspect dictionaries

    Returns:
        Tuple of (tight_aspects, moderate_aspects, loose_aspects)
    """
    tight = []
    moderate = []
    loose = []

    for aspect in aspects:
        priority = classify_aspect_priority(aspect)
        if priority == "tight":
            tight.append(aspect)
        elif priority == "moderate":
            moderate.append(aspect)
        else:
            loose.append(aspect)

    return (tight, moderate, loose)


def build_aspect_summary(
    tight: list,
    moderate: list,
    loose: list,
    current_priority: str
) -> dict:
    """
    Build summary counts for aspect pagination.

    Args:
        tight: List of tight aspects
        moderate: List of moderate aspects
        loose: List of loose aspects
        current_priority: The priority tier being returned

    Returns:
        Summary dictionary with counts and current page info
    """
    summary = {
        "tight_aspects": len(tight),
        "moderate_aspects": len(moderate),
        "loose_aspects": len(loose),
        "total_aspects": len(tight) + len(moderate) + len(loose)
    }

    # Indicate which aspects are in this response
    if current_priority == "tight":
        summary["returned_in_this_page"] = len(tight)
    elif current_priority == "moderate":
        summary["returned_in_this_page"] = len(moderate)
    elif current_priority == "loose":
        summary["returned_in_this_page"] = len(loose)
    else:  # "all"
        summary["returned_in_this_page"] = summary["total_aspects"]

    return summary


def build_pagination_object(
    current_priority: str,
    has_tight: bool,
    has_moderate: bool,
    has_loose: bool
) -> dict:
    """
    Build pagination metadata for aspect navigation.

    Args:
        current_priority: Current priority tier ("tight", "moderate", "loose", "all")
        has_tight: Whether tight aspects exist
        has_moderate: Whether moderate aspects exist
        has_loose: Whether loose aspects exist

    Returns:
        Pagination metadata dictionary
    """
    # Define page mapping
    priority_pages = {
        "tight": 1,
        "moderate": 2,
        "loose": 3,
        "all": None
    }

    current_page = priority_pages.get(current_priority)
    total_pages = sum([has_tight, has_moderate, has_loose])

    # Determine next page
    next_page = None
    if current_priority == "tight" and has_moderate:
        next_page = "moderate"
    elif current_priority == "moderate" and has_loose:
        next_page = "loose"

    has_more = next_page is not None

    pagination = {
        "current_page": current_page,
        "total_pages": total_pages,
        "has_more_aspects": has_more
    }

    if next_page:
        pagination["next_page"] = next_page
        pagination["instructions"] = f"To get {next_page} aspects, call again with aspect_priority='{next_page}'"

    return pagination


def estimate_response_size(response: dict) -> int:
    """
    Estimate JSON response size in bytes.

    Args:
        response: Response dictionary

    Returns:
        Size in bytes
    """
    import json
    return len(json.dumps(response))


@mcp.tool()
def generate_transit_to_natal(
    natal_date_time: str,
    natal_latitude: str,
    natal_longitude: str,
    transit_date_time: str,
    transit_latitude: str | None = None,
    transit_longitude: str | None = None,
    timezone: str | None = None,
    aspect_priority: str = "tight",  # Changed from "all" to "tight" for MCP size safety
    include_all_aspects: bool = False,
    include_lifecycle_events: bool = True
) -> Dict[str, Any]:
    """
    Calculates transiting planet aspects to a natal chart for a specific date.

    This is the most commonly used predictive technique in astrology. It shows how
    current planetary positions interact with the birth chart.

    OPTIMIZED RESPONSE: Thanks to response optimization (84.9% size reduction), aspects
    are efficiently organized by astrological significance. Default "tight" priority returns
    the most critical transits (0-2° orb) while staying well under MCP size limits.

    Args:
        natal_date_time: Birth date and time in ISO format, e.g., '1990-01-15 12:00:00'.
        natal_latitude: Birth location latitude, e.g., '51n30' or '51.5'.
        natal_longitude: Birth location longitude, e.g., '0w10' or '-0.17'.
        transit_date_time: Date/time for transits in ISO format, e.g., '2024-12-18 12:00:00'.
        transit_latitude: Optional transit location latitude (defaults to natal location).
        transit_longitude: Optional transit location longitude (defaults to natal location).
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').
        aspect_priority: Priority tier to return - "tight" (default, 0-2°), "moderate" (2-5°),
                        "loose" (5-8°), or "all" (all aspects, auto-adjusts to "tight" if
                        lifecycle events enabled). Use to filter by orb precision.
        include_all_aspects: Deprecated. Kept for backward compatibility.
        include_lifecycle_events: Include lifecycle events analysis (planetary returns,
                                 major life transits, future timeline). Default: True.

    Returns:
        Dictionary containing natal chart summary, transit positions, paginated aspects,
        aspect summary, pagination metadata, and lifecycle events (if enabled).
    """
    try:
        logger.info(f"[TRANSIT-FULL] Starting transit-to-natal for natal {natal_date_time} with transits at {transit_date_time}")

        # Validate natal inputs
        logger.debug(f"[TRANSIT-FULL] Validating inputs")
        validate_inputs(natal_date_time, natal_latitude, natal_longitude)

        # Parse natal coordinates
        logger.debug(f"[TRANSIT-FULL] Parsing coordinates: natal_lat={natal_latitude}, natal_lon={natal_longitude}")
        natal_lat = parse_coordinate(natal_latitude, is_latitude=True)
        natal_lon = parse_coordinate(natal_longitude, is_latitude=False)

        # Use natal location for transits if not specified
        transit_lat = parse_coordinate(transit_latitude, is_latitude=True) if transit_latitude else natal_lat
        transit_lon = parse_coordinate(transit_longitude, is_latitude=False) if transit_longitude else natal_lon
        logger.debug(f"[TRANSIT-FULL] Transit coords: lat={transit_lat}, lon={transit_lon}")

        # Create natal subject
        logger.debug(f"[TRANSIT-FULL] Creating natal subject")
        natal_subject = charts.Subject(
            date_time=natal_date_time,
            latitude=natal_lat,
            longitude=natal_lon
        )

        # Create transit subject for the specified date
        logger.debug(f"[TRANSIT-FULL] Creating transit subject")
        transit_subject = charts.Subject(
            date_time=transit_date_time,
            latitude=transit_lat,
            longitude=transit_lon
        )

        # Generate natal chart
        logger.debug(f"[TRANSIT-FULL] Generating natal chart")
        natal_chart = charts.Natal(natal_subject)

        # Generate transit chart with aspects to natal
        logger.debug(f"[TRANSIT-FULL] Generating transit chart with aspects to natal")
        transit_chart = charts.Natal(transit_subject, aspects_to=natal_chart)

        # Serialize both charts
        logger.debug(f"[TRANSIT-FULL] Serializing natal chart with ToJSON")
        natal_data = json.loads(json.dumps(natal_chart, cls=ToJSON))
        logger.debug(f"[TRANSIT-FULL] Serializing transit chart with ToJSON")
        transit_data = json.loads(json.dumps(transit_chart, cls=ToJSON))
        logger.debug(f"[TRANSIT-FULL] Serialization complete")

        # Extract natal summary using direct chart object access (not from JSON)
        # This avoids the "Unknown" bug by accessing objects before serialization
        logger.debug(f"[TRANSIT-FULL] Extracting natal summary")
        sun_sign = "Unknown"
        moon_sign = "Unknown"
        rising_sign = "Unknown"

        try:
            sun = natal_chart.objects.get(chart_const.SUN)
            if sun and hasattr(sun, 'sign') and hasattr(sun.sign, 'name'):
                sun_sign = sun.sign.name
        except Exception as e:
            logger.debug(f"Could not extract sun sign: {e}")

        try:
            moon = natal_chart.objects.get(chart_const.MOON)
            if moon and hasattr(moon, 'sign') and hasattr(moon.sign, 'name'):
                moon_sign = moon.sign.name
        except Exception as e:
            logger.debug(f"Could not extract moon sign: {e}")

        try:
            asc = natal_chart.objects.get(chart_const.ASC)
            if asc and hasattr(asc, 'sign') and hasattr(asc.sign, 'name'):
                rising_sign = asc.sign.name
        except Exception as e:
            logger.debug(f"Could not extract rising sign: {e}")

        # Build result with natal summary and transit aspects
        logger.debug(f"[TRANSIT-FULL] Building result dictionary")

        # Filter self-aspects from the aspects dictionary
        # normalize_aspects_to_list will flatten the nested dict and remove self-aspects
        filtered_aspects = normalize_aspects_to_list(
            transit_data.get('aspects', {}),
            filter_self_aspects=True
        )

        # Add object names to aspects for readability (like compact serializer does)
        # Create lookup dict: {object_index: object_name}
        object_names = {}
        for obj_key, obj_data in transit_data.get('objects', {}).items():
            if isinstance(obj_data, dict) and 'index' in obj_data and 'name' in obj_data:
                object_names[obj_data['index']] = obj_data['name']

        # Also add natal object names
        for obj_key, obj_data in natal_data.get('objects', {}).items():
            if isinstance(obj_data, dict) and 'index' in obj_data and 'name' in obj_data:
                object_names[obj_data['index']] = obj_data['name']

        # Add object1 and object2 fields to each aspect
        for aspect in filtered_aspects:
            if isinstance(aspect, dict):
                active_id = aspect.get('active')
                passive_id = aspect.get('passive')
                if active_id in object_names:
                    aspect['object1'] = object_names[active_id]
                if passive_id in object_names:
                    aspect['object2'] = object_names[passive_id]

        logger.info(f"[TRANSIT-FULL] Total aspects after filtering: {len(filtered_aspects)}")

        # === PAGINATION LOGIC ===
        # Classify all aspects by priority tier
        tight_aspects, moderate_aspects, loose_aspects = classify_all_aspects(filtered_aspects)
        logger.info(f"[TRANSIT-FULL] Classified aspects - tight: {len(tight_aspects)}, moderate: {len(moderate_aspects)}, loose: {len(loose_aspects)}")

        # Determine which aspects to return
        if include_all_aspects:
            logger.warning(f"[TRANSIT-FULL] include_all_aspects=True - returning all {len(filtered_aspects)} aspects (may exceed MCP limits)")
            aspects_to_return = filtered_aspects
            effective_priority = "all"
        else:
            # Validate aspect_priority parameter
            valid_priorities = ["tight", "moderate", "loose", "all"]
            if aspect_priority not in valid_priorities:
                logger.warning(f"[TRANSIT-FULL] Invalid aspect_priority '{aspect_priority}', defaulting to 'tight'")
                aspect_priority = "tight"

            # CRITICAL FIX: Auto-adjust priority when lifecycle events enabled to avoid MCP size limits
            # Full aspect data (~59 KB for "all" priority) + lifecycle events (~5-7 KB) exceeds ~50 KB MCP limit
            if include_lifecycle_events and aspect_priority == "all":
                logger.warning(
                    f"[TRANSIT-FULL] Auto-adjusting aspect_priority from 'all' to 'tight' "
                    f"because lifecycle events are enabled (prevents MCP size limit exceeded)"
                )
                aspect_priority = "tight"

            # Filter by requested priority
            aspects_to_return = filter_aspects_by_priority(filtered_aspects, aspect_priority)
            effective_priority = aspect_priority
            logger.info(f"[TRANSIT-FULL] Returning {len(aspects_to_return)} {effective_priority} aspects")

        # Build aspect summary
        aspect_summary = build_aspect_summary(
            tight_aspects,
            moderate_aspects,
            loose_aspects,
            effective_priority
        )

        # Build pagination metadata
        pagination = build_pagination_object(
            effective_priority,
            has_tight=len(tight_aspects) > 0,
            has_moderate=len(moderate_aspects) > 0,
            has_loose=len(loose_aspects) > 0
        )

        # === OPTIMIZE RESPONSE STRUCTURE ===
        # Use optimized builders to reduce response size by 60-70%
        optimized_positions = build_optimized_transit_positions(transit_data)
        optimized_aspects = build_optimized_aspects(aspects_to_return)
        dignities = build_dignities_section(transit_data)

        result = {
            "natal_summary": {
                "sun": sun_sign,
                "moon": moon_sign,
                "rising": rising_sign
            },
            "transit_date": transit_date_time,
            "transit_positions": optimized_positions,
            "dignities": dignities,
            "transit_to_natal_aspects": optimized_aspects,
            "aspect_summary": aspect_summary,
            "pagination": pagination,
            "timezone": timezone
        }

        # === LIFECYCLE EVENTS DETECTION ===
        if include_lifecycle_events:
            if LIFECYCLE_AVAILABLE:
                attach_lifecycle_section(
                    result,
                    natal_chart=natal_chart,
                    comparison_chart=transit_chart,
                    birth_datetime=natal_date_time,
                    comparison_datetime=transit_date_time
                )
            else:
                logger.warning("[TRANSIT-FULL] Lifecycle events requested but module not available")
                result["lifecycle_events"] = None
                result["lifecycle_summary"] = None
        else:
            result["lifecycle_events"] = None
            result["lifecycle_summary"] = None

        # Verify result is JSON serializable before returning
        logger.debug("[TRANSIT-FULL] Verifying JSON serializability")
        try:
            json_test = json.dumps(result)
            result_size = len(json_test) / 1024
            logger.info(f"[TRANSIT-FULL] Result successfully serialized, size: {result_size:.2f} KB")
        except (TypeError, ValueError) as e:
            logger.error(f"[TRANSIT-FULL] CRITICAL: Result not JSON serializable: {e}")
            raise

        logger.info("[TRANSIT-FULL] Transit-to-natal generated successfully, returning result")
        return result

    except Exception as e:
        logger.error(f"[TRANSIT-FULL] Error generating transit-to-natal: {str(e)}", exc_info=True)
        return handle_chart_error(e)


@mcp.tool()
def generate_compact_transit_to_natal(
    natal_date_time: str,
    natal_latitude: str,
    natal_longitude: str,
    transit_date_time: str,
    transit_latitude: str | None = None,
    transit_longitude: str | None = None,
    timezone: str | None = None,
    include_interpretations: bool = True,
    include_lifecycle_events: bool = True
) -> Dict[str, Any]:
    """
    Calculates compact transiting planet aspects to a natal chart with interpretation hints.

    This streamlined version focuses on major planets and major aspects only, with optional
    interpretation keywords to aid understanding.

    Args:
        natal_date_time: Birth date and time in ISO format, e.g., '1990-01-15 12:00:00'.
        natal_latitude: Birth location latitude, e.g., '51n30' or '51.5'.
        natal_longitude: Birth location longitude, e.g., '0w10' or '-0.17'.
        transit_date_time: Date/time for transits in ISO format, e.g., '2024-12-18 12:00:00'.
        transit_latitude: Optional transit location latitude (defaults to natal location).
        transit_longitude: Optional transit location longitude (defaults to natal location).
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').
        include_interpretations: Include aspect interpretation keywords (default: True).
        include_lifecycle_events: Include lifecycle analysis (default: True).

    Returns:
        Compact dictionary with natal summary, transit positions, and filtered major aspects
        with interpretation hints.
    """
    try:
        logger.info(f"Generating compact transit-to-natal for natal {natal_date_time} with transits at {transit_date_time}")

        # Validate natal inputs
        validate_inputs(natal_date_time, natal_latitude, natal_longitude)

        # Parse natal coordinates
        natal_lat = parse_coordinate(natal_latitude, is_latitude=True)
        natal_lon = parse_coordinate(natal_longitude, is_latitude=False)

        # Use natal location for transits if not specified
        transit_lat = parse_coordinate(transit_latitude, is_latitude=True) if transit_latitude else natal_lat
        transit_lon = parse_coordinate(transit_longitude, is_latitude=False) if transit_longitude else natal_lon

        # Create natal subject
        natal_subject = charts.Subject(
            date_time=natal_date_time,
            latitude=natal_lat,
            longitude=natal_lon
        )

        # Create transit subject for the specified date
        transit_subject = charts.Subject(
            date_time=transit_date_time,
            latitude=transit_lat,
            longitude=transit_lon
        )

        # Generate natal chart
        natal_chart = charts.Natal(natal_subject)

        # Generate transit chart with aspects to natal
        transit_chart = charts.Natal(transit_subject, aspects_to=natal_chart)

        # Serialize transit chart using compact serializer
        transit_data = json.loads(json.dumps(transit_chart, cls=CompactJSONSerializer))

        # Get aspects and optionally add interpretations
        aspects = transit_data.get('aspects', [])
        if include_interpretations:
            aspects = add_aspect_interpretations(aspects)

        # Extract natal summary using direct chart object access (not from JSON)
        # This avoids the "Unknown" bug by accessing objects before serialization
        sun_sign = "Unknown"
        moon_sign = "Unknown"
        rising_sign = "Unknown"

        try:
            sun = natal_chart.objects.get(chart_const.SUN)
            if sun and hasattr(sun, 'sign') and hasattr(sun.sign, 'name'):
                sun_sign = sun.sign.name
        except Exception as e:
            logger.debug(f"Could not extract sun sign: {e}")

        try:
            moon = natal_chart.objects.get(chart_const.MOON)
            if moon and hasattr(moon, 'sign') and hasattr(moon.sign, 'name'):
                moon_sign = moon.sign.name
        except Exception as e:
            logger.debug(f"Could not extract moon sign: {e}")

        try:
            asc = natal_chart.objects.get(chart_const.ASC)
            if asc and hasattr(asc, 'sign') and hasattr(asc.sign, 'name'):
                rising_sign = asc.sign.name
        except Exception as e:
            logger.debug(f"Could not extract rising sign: {e}")

        # Build compact result
        result = {
            "natal_summary": {
                "date_time": natal_date_time,
                "sun_sign": sun_sign,
                "moon_sign": moon_sign,
                "rising_sign": rising_sign
            },
            "transit_date": transit_date_time,
            "transit_positions": transit_data.get('objects', {}),
            "transit_to_natal_aspects": aspects,
            "timezone": timezone
        }

        if include_lifecycle_events:
            if LIFECYCLE_AVAILABLE:
                attach_lifecycle_section(
                    result,
                    natal_chart=natal_chart,
                    comparison_chart=transit_chart,
                    birth_datetime=natal_date_time,
                    comparison_datetime=transit_date_time
                )
            else:
                logger.warning("[TRANSIT-COMPACT] Lifecycle requested but module unavailable")
                result["lifecycle_events"] = None
                result["lifecycle_summary"] = None
        else:
            result["lifecycle_events"] = None
            result["lifecycle_summary"] = None

        logger.info("Compact transit-to-natal generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating compact transit-to-natal: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def configure_immanuel_settings(
    setting_key: str,
    setting_value: str
) -> Dict[str, Any]:
    """
    Configures the global settings for the Immanuel library, affecting all subsequent chart calculations.
    See the Immanuel documentation for available keys and values.
    
    Args:
        setting_key: The name of the setting to change, e.g., 'house_system' or 'locale'.
        setting_value: The value to set. For lists like 'objects', provide a comma-separated string of 
                      integer constants or names, e.g., '4000001,4000002,Antares'. For constants, 
                      provide the string name, e.g., 'CAMPANUS'.
    
    Returns:
        A confirmation message with old and new values.
    """
    try:
        logger.info(f"Configuring setting: {setting_key} = {setting_value}")
        
        from immanuel import setup
        
        # Validate setting key
        valid_settings = [
            'house_system', 'objects', 'angles', 'aspects', 'locale',
            'mc_progression_method', 'lunar_phase_method', 'solar_arc_method',
            'orb_calculation_method'
        ]
        
        if setting_key not in valid_settings and not setting_key.endswith('_orb'):
            return {
                "status": "warning",
                "message": f"Unknown setting '{setting_key}'. Valid options: {', '.join(valid_settings)}",
                "applied": False
            }
        
        # Get the current settings object
        settings = setup.settings
        old_value = getattr(settings, setting_key, None)
        
        # Special handling for different setting types
        if setting_key == 'house_system':
            # Convert string to constant
            const_value = getattr(chart_const, setting_value.upper())
            setattr(settings, setting_key, const_value)
            
        elif setting_key == 'objects':
            # Parse comma-separated list of objects
            object_list = []
            for item in setting_value.split(','):
                item = item.strip()
                # Try as integer first
                try:
                    object_list.append(int(item))
                except ValueError:
                    # Try as constant name
                    if hasattr(data_const, item.upper()):
                        object_list.append(getattr(data_const, item.upper()))
                    else:
                        # Keep as string (for named objects like stars)
                        object_list.append(item)
            
            setattr(settings, setting_key, object_list)
            
        elif setting_key in ['angles', 'aspects']:
            # Parse comma-separated list of aspect/angle constants
            const_list = []
            for item in setting_value.split(','):
                item = item.strip()
                if hasattr(chart_const, item.upper()):
                    const_list.append(getattr(chart_const, item.upper()))
                else:
                    const_list.append(int(item))
            
            setattr(settings, setting_key, const_list)
            
        elif setting_key == 'locale':
            # Direct string assignment
            setattr(settings, setting_key, setting_value)
            
        elif setting_key == 'mc_progression_method':
            # Convert string to constant
            const_value = getattr(calc_const, setting_value.upper())
            setattr(settings, setting_key, const_value)
            
        elif setting_key in ['lunar_phase_method', 'solar_arc_method']:
            # Convert string to constant
            const_value = getattr(calc_const, setting_value.upper())
            setattr(settings, setting_key, const_value)
            
        elif setting_key == 'orb_calculation_method':
            # Convert string to constant
            const_value = getattr(chart_const, setting_value.upper())
            setattr(settings, setting_key, const_value)
            
        elif setting_key.endswith('_orb'):
            # Numeric orb values
            setattr(settings, setting_key, float(setting_value))
            
        else:
            # Try direct assignment for other types
            # Attempt to convert to appropriate type
            try:
                # Try as boolean
                if setting_value.lower() in ['true', 'false']:
                    setattr(settings, setting_key, setting_value.lower() == 'true')
                else:
                    # Try as number
                    try:
                        if '.' in setting_value:
                            setattr(settings, setting_key, float(setting_value))
                        else:
                            setattr(settings, setting_key, int(setting_value))
                    except ValueError:
                        # Keep as string
                        setattr(settings, setting_key, setting_value)
            except Exception as e:
                logger.warning(f"Error setting {setting_key}: {e}")
                setattr(settings, setting_key, setting_value)
        
        result = {
            "status": "success",
            "message": f"Setting '{setting_key}' updated from '{old_value}' to '{setting_value}'.",
            "old_value": str(old_value),
            "new_value": setting_value
        }
        logger.info("Setting configured successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error configuring setting: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def list_available_settings() -> Dict[str, Any]:
    """
    List all available Immanuel settings and their current values.

    Returns:
        Dictionary of available settings with both numeric codes and readable names.
    """
    try:
        from immanuel import setup
        settings = setup.settings

        # House system mapping (chart_const.X values to names)
        HOUSE_SYSTEMS = {
            101: "ALCABITUS",
            102: "AZIMUTHAL",
            103: "CAMPANUS",
            104: "EQUAL",
            105: "KOCH",
            106: "MERIDIAN",
            107: "MORINUS",
            108: "PLACIDUS",
            109: "POLICH_PAGE",
            110: "PORPHYRIUS",
            111: "REGIOMONTANUS",
            112: "VEHLOW_EQUAL",
            113: "WHOLE_SIGN"
        }

        # Aspect angle mapping (degrees to aspect names)
        ASPECT_ANGLES = {
            0.0: "Conjunction (0°)",
            180.0: "Opposition (180°)",
            90.0: "Square (90°)",
            120.0: "Trine (120°)",
            60.0: "Sextile (60°)",
            150.0: "Quincunx (150°)",
            30.0: "Semi-sextile (30°)",
            45.0: "Semi-square (45°)",
            135.0: "Sesquiquadrate (135°)"
        }

        # Get current values
        house_system_code = getattr(settings, 'house_system', None)
        house_system_name = HOUSE_SYSTEMS.get(house_system_code, f"Unknown ({house_system_code})")

        current_aspects = getattr(settings, 'aspects', [])
        aspect_names = [ASPECT_ANGLES.get(angle, f"{angle}°") for angle in current_aspects]

        setting_info = {
            'house_system': {
                'current': house_system_code,
                'name': house_system_name,
                'description': 'House system used for chart calculations',
                'available_systems': list(HOUSE_SYSTEMS.values())
            },
            'locale': {
                'current': getattr(settings, 'locale', None),
                'description': 'Locale for formatting output (None = default)'
            },
            'objects': {
                'current': len(getattr(settings, 'objects', [])),
                'description': 'Number of celestial objects included in charts'
            },
            'aspects': {
                'current': len(current_aspects),
                'aspect_angles': aspect_names,
                'description': 'Aspects calculated between objects'
            }
        }

        return {
            "status": "success",
            "settings": setting_info
        }

    except Exception as e:
        logger.error(f"Error listing settings: {str(e)}")
        return handle_chart_error(e)


def main():
    """Run the MCP server with stdio transport for Claude Desktop compatibility."""
    try:
        logger.info("Starting Enhanced Immanuel Astrology MCP Server")
        # Explicitly use stdio transport for Claude Desktop compatibility
        # stdio is the default and works with Claude Desktop's process spawning
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

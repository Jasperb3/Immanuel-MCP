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

# Suppress any third-party library logging that might go to stdout/stderr
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# Initialize the MCP server
mcp = FastMCP("immanuel-astrology-server")


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

        # Generate solar return chart
        solar_return = charts.SolarReturn(subject, return_year)
        
        # Serialize to JSON
        result = json.loads(json.dumps(solar_return, cls=ToJSON))
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

        # Generate solar return chart
        solar_return = charts.SolarReturn(subject, return_year)
        
        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(solar_return, cls=CompactJSONSerializer))
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

        # Generate progressed chart
        progressed = charts.Progressed(subject, progression_date_time)
        
        # Serialize to JSON
        result = json.loads(json.dumps(progressed, cls=ToJSON))
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

        # Generate progressed chart
        progressed = charts.Progressed(subject, progression_date_time)
        
        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(progressed, cls=CompactJSONSerializer))
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


@mcp.tool()
def generate_transit_to_natal(
    natal_date_time: str,
    natal_latitude: str,
    natal_longitude: str,
    transit_date_time: str,
    transit_latitude: str | None = None,
    transit_longitude: str | None = None,
    timezone: str | None = None
) -> Dict[str, Any]:
    """
    Calculates transiting planet aspects to a natal chart for a specific date.

    This is the most commonly used predictive technique in astrology. It shows how
    current planetary positions interact with the birth chart.

    Args:
        natal_date_time: Birth date and time in ISO format, e.g., '1990-01-15 12:00:00'.
        natal_latitude: Birth location latitude, e.g., '51n30' or '51.5'.
        natal_longitude: Birth location longitude, e.g., '0w10' or '-0.17'.
        transit_date_time: Date/time for transits in ISO format, e.g., '2024-12-18 12:00:00'.
        transit_latitude: Optional transit location latitude (defaults to natal location).
        transit_longitude: Optional transit location longitude (defaults to natal location).
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').

    Returns:
        Dictionary containing natal chart summary, transit positions, and aspects between them.
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

        logger.info(f"[TRANSIT-FULL] Returning {len(filtered_aspects)} filtered aspects with object names")

        result = {
            "natal_summary": {
                "date_time": natal_date_time,
                "sun_sign": sun_sign,
                "moon_sign": moon_sign,
                "rising_sign": rising_sign
            },
            "transit_date": transit_date_time,
            "transit_positions": transit_data.get('objects', {}),
            "transit_to_natal_aspects": filtered_aspects,
            "timezone": timezone
        }

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
    include_interpretations: bool = True
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
        Dictionary of available settings and their current values.
    """
    try:
        from immanuel import setup
        settings = setup.settings
        
        setting_info = {
            'house_system': {
                'current': getattr(settings, 'house_system', 'Unknown'),
                'description': 'House system to use (e.g., PLACIDUS, CAMPANUS, etc.)'
            },
            'locale': {
                'current': getattr(settings, 'locale', 'Unknown'),
                'description': 'Locale for formatting output'
            },
            'objects': {
                'current': len(getattr(settings, 'objects', [])),
                'description': 'Number of objects included in charts'
            },
            'aspects': {
                'current': len(getattr(settings, 'aspects', [])),
                'description': 'Number of aspects calculated'
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
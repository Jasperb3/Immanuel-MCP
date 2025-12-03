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
from mcp.types import TextContent
from compact_serializer import CompactJSONSerializer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    coord = coord.strip().replace('°', ' ').replace("'", ' ').replace('"', ' ')
    
    # Try direct float conversion first
    try:
        result = float(coord)
        # Validate range
        if is_latitude and not -90 <= result <= 90:
            raise ValueError(f"Latitude must be between -90 and 90 degrees. Got: {result}")
        elif not is_latitude and not -180 <= result <= 180:
            raise ValueError(f"Longitude must be between -180 and 180 degrees. Got: {result}")
        return result
    except ValueError as e:
        if "must be between" in str(e):
            raise  # Re-raise range validation errors
        pass
    
    # Parse traditional format with improved regex
    # Pattern for formats like: 32n43, 32N43, 32n43'30, 117w09, etc.
    pattern = r'^(\d+)([nsewNSEW])(\d+)(?:[\'\"]*(\d+))?[\'\"]*$'
    match = re.match(pattern, coord.replace(' ', ''))
    
    if match:
        degrees = int(match.group(1))
        direction = match.group(2).lower()
        minutes = int(match.group(3)) if match.group(3) else 0
        seconds = int(match.group(4)) if match.group(4) else 0
        
        decimal = degrees + (minutes / 60) + (seconds / 3600)
        
        # Apply sign based on direction
        if direction in ['s', 'w']:
            decimal = -decimal
        
        # Validate range
        if is_latitude and not -90 <= decimal <= 90:
            raise ValueError(f"Latitude must be between -90 and 90 degrees. Got: {decimal}")
        elif not is_latitude and not -180 <= decimal <= 180:
            raise ValueError(f"Longitude must be between -180 and 180 degrees. Got: {decimal}")
            
        return decimal
    
    # Try space-separated format: "32 43 30 N" or "32 43 N"
    parts = coord.upper().split()
    if len(parts) >= 3 and parts[-1] in ['N', 'S', 'E', 'W']:
        try:
            degrees = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 2 else 0
            seconds = int(parts[2]) if len(parts) > 3 else 0
            direction = parts[-1].lower()
            
            decimal = degrees + (minutes / 60) + (seconds / 3600)
            if direction in ['s', 'w']:
                decimal = -decimal
            
            # Validate range
            if is_latitude and not -90 <= decimal <= 90:
                raise ValueError(f"Latitude must be between -90 and 90 degrees. Got: {decimal}")
            elif not is_latitude and not -180 <= decimal <= 180:
                raise ValueError(f"Longitude must be between -180 and 180 degrees. Got: {decimal}")
                
            return decimal
        except (ValueError, IndexError):
            pass
    
    raise ValueError(f"Invalid coordinate format: {coord}. "
                    f"Supported formats: decimal (32.71), DMS (32n43, 32°43'30\"), "
                    f"or space-separated (32 43 30 N)")


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


@mcp.tool()
def generate_compact_natal_chart(
    date_time: str,
    latitude: str,
    longitude: str,
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

    Returns:
        A compact Natal chart object serialized to a JSON dictionary, including simplified
        objects, houses, and aspects.
    """
    try:
        logger.info(f"Generating compact natal chart for {date_time} at {latitude}, {longitude}")

        # Validate inputs first
        validate_inputs(date_time, latitude, longitude)

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        # Create subject
        subject = charts.Subject(
            date_time=date_time,
            latitude=lat,
            longitude=lon
        )

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
) -> Dict[str, Any]:
    """
    Generates a natal (birth) chart for a specific person or event.
    
    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
    
    Returns:
        The full Natal chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating natal chart for {date_time} at {latitude}, {longitude}")
        
        # Validate inputs first
        validate_inputs(date_time, latitude, longitude)
        
        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)
        
        # Create subject
        subject = charts.Subject(
            date_time=date_time,
            latitude=lat,
            longitude=lon
        )
        
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
) -> Dict[str, Any]:
    """
    Get a simplified summary of key chart information.
    
    Args:
        date_time: The birth date and time in ISO format
        latitude: The latitude of the birth location
        longitude: The longitude of the birth location
    
    Returns:
        A simplified summary with just the essential information.
    """
    try:
        logger.info(f"Generating chart summary for {date_time} at {latitude}, {longitude}")
        
        validate_inputs(date_time, latitude, longitude)
        
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)
        
        subject = charts.Subject(date_time=date_time, latitude=lat, longitude=lon)
        natal = charts.Natal(subject)
        
        # Extract key information
        sun = natal.objects.get(4000001)  # Sun
        moon = natal.objects.get(4000002)  # Moon
        asc = natal.objects.get(3000001)  # Ascendant
        
        result = {
            "sun_sign": sun.sign.name if sun else "Unknown",
            "moon_sign": moon.sign.name if moon else "Unknown", 
            "rising_sign": asc.sign.name if asc else "Unknown",
            "chart_shape": natal.shape,
            "moon_phase": natal.moon_phase.formatted,
            "diurnal": natal.diurnal,
            "house_system": natal.house_system
        }
        
        logger.info("Chart summary generated successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error generating chart summary: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def get_planetary_positions(
    date_time: str,
    latitude: str,
    longitude: str,
) -> Dict[str, Any]:
    """
    Get just the planetary positions in a simplified format.
    
    Args:
        date_time: The birth date and time in ISO format
        latitude: The latitude of the birth location
        longitude: The longitude of the birth location
    
    Returns:
        Dictionary containing planetary positions in signs and houses.
    """
    try:
        logger.info(f"Getting planetary positions for {date_time} at {latitude}, {longitude}")
        
        validate_inputs(date_time, latitude, longitude)
        
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)
        
        subject = charts.Subject(date_time=date_time, latitude=lat, longitude=lon)
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
    return_year: int
) -> Dict[str, Any]:
    """
    Generates a solar return chart for a given year.
    
    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        return_year: The year for which to calculate the solar return.
    
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
        
        # Create subject
        subject = charts.Subject(
            date_time=date_time,
            latitude=lat,
            longitude=lon
        )
        
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
    return_year: int
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
        
        # Create subject
        subject = charts.Subject(
            date_time=date_time,
            latitude=lat,
            longitude=lon
        )
        
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
    progression_date_time: str
) -> Dict[str, Any]:
    """
    Generates a secondary progression chart for a native chart to a specific future date.
    
    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        progression_date_time: The date and time to progress the chart to, in ISO format.
    
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
        
        # Create subject
        subject = charts.Subject(
            date_time=date_time,
            latitude=lat,
            longitude=lon
        )
        
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
    progression_date_time: str
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
        
        # Create subject
        subject = charts.Subject(
            date_time=date_time,
            latitude=lat,
            longitude=lon
        )
        
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
    partner_longitude: str
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
        
        # Create subjects
        native = charts.Subject(
            date_time=native_date_time,
            latitude=native_lat,
            longitude=native_lon
        )
        
        partner = charts.Subject(
            date_time=partner_date_time,
            latitude=partner_lat,
            longitude=partner_lon
        )
        
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
    partner_longitude: str
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
        
        # Create subjects
        native = charts.Subject(
            date_time=native_date_time,
            latitude=native_lat,
            longitude=native_lon
        )
        
        partner = charts.Subject(
            date_time=partner_date_time,
            latitude=partner_lat,
            longitude=partner_lon
        )
        
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
    partner_longitude: str
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
        
        # Create subjects
        native_subject = charts.Subject(
            date_time=native_date_time,
            latitude=native_lat,
            longitude=native_lon
        )
        
        partner_subject = charts.Subject(
            date_time=partner_date_time,
            latitude=partner_lat,
            longitude=partner_lon
        )
        
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
    partner_longitude: str
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
        
        # Create subjects
        native_subject = charts.Subject(
            date_time=native_date_time,
            latitude=native_lat,
            longitude=native_lon
        )
        
        partner_subject = charts.Subject(
            date_time=partner_date_time,
            latitude=partner_lat,
            longitude=partner_lon
        )
        
        # Create partner chart first
        partner_chart = charts.Natal(partner_subject)
        
        # Create native chart with aspects to partner
        native_chart = charts.Natal(native_subject, aspects_to=partner_chart)
        
        # Serialize the entire chart using compact serializer to get filtered aspects
        compact_chart_data = json.loads(json.dumps(native_chart, cls=CompactJSONSerializer))
        filtered_aspects = compact_chart_data.get('aspects', [])
        
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
    """Run the MCP server."""
    try:
        logger.info("Starting Enhanced Immanuel Astrology MCP Server")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
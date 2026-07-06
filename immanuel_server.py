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
from datetime import datetime, timezone as dt_timezone
from typing import Any, Dict, List, Optional, Union

import immanuel
from immanuel import charts
from immanuel.const import chart as chart_const
from immanuel.const import data as data_const
from immanuel.classes.serialize import ToJSON
from immanuel.tools import convert
from scripts.compact_serializer import CompactJSONSerializer

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

# Import lifecycle events detection system (after logger is configured).
# This import is intentionally unconditional: a broken lifecycle package
# should fail the server at startup, not silently degrade every response.
from immanuel_mcp.lifecycle import detect_progressed_moon_return
from immanuel_mcp.lifecycle.attach import attach_lifecycle_section

# Suppress any third-party library logging that might go to stdout/stderr
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# The single shared MCP server instance. All entry points (this script and
# `python -m immanuel_mcp`) register tools against this same object.
from immanuel_mcp.app import mcp


# ============================================================================
# Shared helpers (single source of truth in the immanuel_mcp package)
# ============================================================================

from immanuel_mcp.utils.coordinates import parse_coordinate
from immanuel_mcp.utils.errors import validate_inputs, handle_chart_error
from immanuel_mcp.utils.subjects import create_subject
from immanuel_mcp.utils.datetimes import parse_datetime_value
from immanuel_mcp.utils.settings import build_call_settings, build_applied_settings
from immanuel_mcp.optimizers.positions import build_optimized_transit_positions
from immanuel_mcp.optimizers.dignities import build_dignities_section
from immanuel_mcp.optimizers.aspects import build_optimized_aspects
from immanuel_mcp.optimizers.cross_aspects import (
    build_full_cross_aspects,
    build_compact_cross_aspects,
)
from immanuel_mcp.pagination.helpers import (
    classify_all_aspects,
    filter_aspects_by_priority,
    build_aspect_summary,
    build_pagination_object,
)
from immanuel_mcp.interpretations.aspects import (
    add_aspect_interpretations,
    normalize_aspects_to_list,
)


@mcp.tool()
def generate_compact_natal_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    timezone: str = None,
    house_system: str = None
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
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

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

        call_settings = build_call_settings(house_system)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate natal chart
        natal = charts.Natal(subject, settings=call_settings)

        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(natal, cls=CompactJSONSerializer))

        # Lifecycle analysis uses current transits as reference. The UTC
        # timestamp is paired with an explicit UTC timezone on the Subject;
        # previously it was interpreted as local time at the birth
        # coordinates, shifting the reference instant by up to +/-12 hours.
        now_dt = datetime.now(dt_timezone.utc).replace(microsecond=0, tzinfo=None)
        try:
            transit_subject = create_subject(
                now_dt.strftime("%Y-%m-%d %H:%M:%S"), lat, lon, 'UTC'
            )
            transit_chart = charts.Natal(transit_subject, settings=call_settings)
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

        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
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
    timezone: str = None,
    house_system: str = None
) -> Dict[str, Any]:
    """
    Generates a natal (birth) chart for a specific person or event.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').
                  If not provided, timezone is inferred from coordinates.
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

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

        call_settings = build_call_settings(house_system)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate natal chart
        natal = charts.Natal(subject, settings=call_settings)

        # Serialize to JSON
        result = json.loads(json.dumps(natal, cls=ToJSON))

        # Lifecycle analysis uses current transits as reference. The UTC
        # timestamp is paired with an explicit UTC timezone on the Subject;
        # previously it was interpreted as local time at the birth
        # coordinates, shifting the reference instant by up to +/-12 hours.
        now_dt = datetime.now(dt_timezone.utc).replace(microsecond=0, tzinfo=None)
        try:
            transit_subject = create_subject(
                now_dt.strftime("%Y-%m-%d %H:%M:%S"), lat, lon, 'UTC'
            )
            transit_chart = charts.Natal(transit_subject, settings=call_settings)
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

        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
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
    timezone: str = None,
    house_system: str = None
) -> Dict[str, Any]:
    """
    Get a simplified summary of key chart information.

    Args:
        date_time: The birth date and time in ISO format
        latitude: The latitude of the birth location
        longitude: The longitude of the birth location
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York')
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

    Returns:
        A simplified summary with just the essential information.
    """
    try:
        logger.info(f"Generating chart summary for {date_time} at {latitude}, {longitude}")

        validate_inputs(date_time, latitude, longitude)

        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        call_settings = build_call_settings(house_system)

        subject = create_subject(date_time, lat, lon, timezone)
        natal = charts.Natal(subject, settings=call_settings)

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
            chart_house_system = natal.house_system if hasattr(natal, 'house_system') else "Unknown"
        except Exception as e:
            logger.error(f"Error accessing house system: {e}")
            chart_house_system = "Unknown"

        result = {
            "sun_sign": sun_sign,
            "moon_sign": moon_sign,
            "rising_sign": rising_sign,
            "chart_shape": chart_shape,
            "moon_phase": moon_phase,
            "diurnal": diurnal,
            "house_system": chart_house_system,
            "applied_settings": build_applied_settings(house_system),
            "status": "success"
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
    timezone: str = None,
    house_system: str = None
) -> Dict[str, Any]:
    """
    Get just the planetary positions in a simplified format.

    Args:
        date_time: The birth date and time in ISO format
        latitude: The latitude of the birth location
        longitude: The longitude of the birth location
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York')
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

    Returns:
        Dictionary containing planetary positions in signs and houses.
    """
    try:
        logger.info(f"Getting planetary positions for {date_time} at {latitude}, {longitude}")

        validate_inputs(date_time, latitude, longitude)

        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        call_settings = build_call_settings(house_system)

        subject = create_subject(date_time, lat, lon, timezone)
        natal = charts.Natal(subject, settings=call_settings)
        
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
        
        result = {
            "planets": planets,
            "applied_settings": build_applied_settings(house_system),
            "status": "success"
        }
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
    timezone: str = None,
    house_system: str = None,
    include_natal_aspects: bool = True,
    return_latitude: str = None,
    return_longitude: str = None
) -> Dict[str, Any]:
    """
    Generates a solar return chart for a given year.

    Return charts are conventionally cast for where the person is at the
    return moment, not the birthplace: pass return_latitude/return_longitude
    to relocate. The return moment itself is location-independent and stays
    identical; only the houses/angles change. Timestamps remain expressed in
    the birth timezone.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        return_year: The year for which to calculate the solar return.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.
        include_natal_aspects: Include return-planet-to-natal aspects — a primary
                               layer of return interpretation — under
                               'natal_cross_aspects' (default: True).
        return_latitude: Optional latitude to relocate the return chart to
                         (defaults to the birth latitude).
        return_longitude: Optional longitude to relocate the return chart to
                          (defaults to the birth longitude).

    Returns:
        The full SolarReturn chart object serialized to a JSON dictionary, plus
        return-to-natal aspects under 'natal_cross_aspects' (each entry carries
        'return_object' and 'natal_object') and a 'return_location' echo.
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

        call_settings = build_call_settings(house_system)

        relocated = return_latitude is not None or return_longitude is not None
        return_lat = parse_coordinate(return_latitude, is_latitude=True) if return_latitude else lat
        return_lon = parse_coordinate(return_longitude, is_latitude=False) if return_longitude else lon

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate charts
        natal_chart = charts.Natal(subject, settings=call_settings)

        if relocated:
            # The return moment depends only on the Sun's geocentric longitude
            # (location-independent), so relocation = casting the same moment
            # at other coordinates. The birth *instant* must be preserved:
            # pass the resolved birth timezone explicitly, otherwise it would
            # be reinterpreted in the return location's zone and the whole
            # chart silently wrong.
            birth_tz = timezone or str(subject.date_time.tzinfo)
            return_subject = create_subject(date_time, return_lat, return_lon, birth_tz)
        else:
            return_subject = subject
        solar_return = charts.SolarReturn(return_subject, return_year, settings=call_settings)

        # Serialize to JSON
        result = json.loads(json.dumps(solar_return, cls=ToJSON))

        # Return-to-natal aspects (the chart's own internal aspects stay
        # under 'aspects'; the two lists are never merged)
        if include_natal_aspects:
            cross_chart = charts.SolarReturn(
                return_subject, return_year,
                aspects_to=natal_chart, settings=call_settings
            )
            cross_data = json.loads(json.dumps(cross_chart, cls=ToJSON))
            result["natal_cross_aspects"] = build_full_cross_aspects(
                cross_data, "return_object")
        else:
            result["natal_cross_aspects"] = None

        # Extract solar return datetime (handle wrapped DateTime object)
        solar_return_dt_obj = getattr(solar_return, 'solar_return_date_time', None)
        if solar_return_dt_obj and hasattr(solar_return_dt_obj, 'datetime'):
            # It's a wrapped DateTime object, extract the datetime
            solar_return_dt = solar_return_dt_obj.datetime.strftime("%Y-%m-%d %H:%M:%S")
        elif solar_return_dt_obj:
            # Try to convert to string
            solar_return_dt = str(solar_return_dt_obj)
        else:
            # Fallback to result dict or default
            solar_return_dt = result.get('solar_return_date_time', f"{return_year}-01-01 00:00:00")

        # Create a transit chart for lifecycle event detection (SolarReturn object doesn't work)
        try:
            transit_subject = charts.Subject(
                date_time=solar_return_dt,
                latitude=lat,
                longitude=lon
            )
            transit_chart_for_lifecycle = charts.Natal(transit_subject, settings=call_settings)

            attach_lifecycle_section(
                result,
                natal_chart=natal_chart,
                comparison_chart=transit_chart_for_lifecycle,
                birth_datetime=date_time,
                comparison_datetime=solar_return_dt
            )
        except Exception as e:
            logger.warning(f"Could not attach lifecycle events to solar return: {e}")
            result["lifecycle_events"] = None
            result["lifecycle_summary"] = None

        result["return_location"] = {
            "latitude": return_lat,
            "longitude": return_lon,
            "relocated": relocated
        }
        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
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
    timezone: str = None,
    house_system: str = None,
    include_natal_aspects: bool = True,
    aspect_priority: str = "tight",
    return_latitude: str = None,
    return_longitude: str = None
) -> Dict[str, Any]:
    """
    Generates a compact solar return chart for a given year.

    This tool provides a streamlined version of the solar return chart, focusing on the most critical
    astrological data: major celestial objects, their positions, and major aspects. It omits
    more detailed data like weightings and chart shape for a faster and more concise output.

    Return charts are conventionally cast for where the person is at the
    return moment, not the birthplace: pass return_latitude/return_longitude
    to relocate. The return moment itself is location-independent and stays
    identical; only the houses/angles change. Timestamps remain expressed in
    the birth timezone.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        return_year: The year for which to calculate the solar return.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.
        include_natal_aspects: Include return-planet-to-natal aspects under
                               'natal_cross_aspects' (default: True).
        aspect_priority: Priority tier for the natal cross-aspects - "tight"
                         (default, 0-2° actual orb), "moderate" (>2-5°),
                         "loose" (>5°), or "all".
        return_latitude: Optional latitude to relocate the return chart to
                         (defaults to the birth latitude).
        return_longitude: Optional longitude to relocate the return chart to
                          (defaults to the birth longitude).

    Returns:
        A compact SolarReturn chart object serialized to a JSON dictionary, plus
        return-to-natal aspects under 'natal_cross_aspects' (each entry carries
        'return_object' and 'natal_object') and a 'return_location' echo.
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

        call_settings = build_call_settings(house_system)

        relocated = return_latitude is not None or return_longitude is not None
        return_lat = parse_coordinate(return_latitude, is_latitude=True) if return_latitude else lat
        return_lon = parse_coordinate(return_longitude, is_latitude=False) if return_longitude else lon

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate charts
        natal_chart = charts.Natal(subject, settings=call_settings)

        if relocated:
            # The return moment depends only on the Sun's geocentric longitude
            # (location-independent), so relocation = casting the same moment
            # at other coordinates. The birth *instant* must be preserved:
            # pass the resolved birth timezone explicitly, otherwise it would
            # be reinterpreted in the return location's zone and the whole
            # chart silently wrong.
            birth_tz = timezone or str(subject.date_time.tzinfo)
            return_subject = create_subject(date_time, return_lat, return_lon, birth_tz)
        else:
            return_subject = subject
        solar_return = charts.SolarReturn(return_subject, return_year, settings=call_settings)

        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(solar_return, cls=CompactJSONSerializer))

        # Return-to-natal aspects (major objects/aspects, priority-filtered)
        if include_natal_aspects:
            cross_chart = charts.SolarReturn(
                return_subject, return_year,
                aspects_to=natal_chart, settings=call_settings
            )
            cross_data = json.loads(json.dumps(cross_chart, cls=CompactJSONSerializer))
            cross_aspects, cross_summary = build_compact_cross_aspects(
                cross_data, "return_object", aspect_priority)
            result["natal_cross_aspects"] = cross_aspects
            result["natal_cross_aspect_summary"] = cross_summary
        else:
            result["natal_cross_aspects"] = None

        # Extract solar return datetime (handle wrapped DateTime object)
        solar_return_dt_obj = getattr(solar_return, 'solar_return_date_time', None)
        if solar_return_dt_obj and hasattr(solar_return_dt_obj, 'datetime'):
            # It's a wrapped DateTime object, extract the datetime
            solar_return_dt = solar_return_dt_obj.datetime.strftime("%Y-%m-%d %H:%M:%S")
        elif solar_return_dt_obj:
            # Try to convert to string
            solar_return_dt = str(solar_return_dt_obj)
        else:
            # Fallback to result dict or default
            solar_return_dt = result.get('solar_return_date_time', f"{return_year}-01-01 00:00:00")

        # Create a transit chart for lifecycle event detection (SolarReturn object doesn't work)
        try:
            transit_subject = charts.Subject(
                date_time=solar_return_dt,
                latitude=lat,
                longitude=lon
            )
            transit_chart_for_lifecycle = charts.Natal(transit_subject, settings=call_settings)

            attach_lifecycle_section(
                result,
                natal_chart=natal_chart,
                comparison_chart=transit_chart_for_lifecycle,
                birth_datetime=date_time,
                comparison_datetime=solar_return_dt
            )
        except Exception as e:
            logger.warning(f"Could not attach lifecycle events to compact solar return: {e}")
            result["lifecycle_events"] = None
            result["lifecycle_summary"] = None

        result["return_location"] = {
            "latitude": return_lat,
            "longitude": return_lon,
            "relocated": relocated
        }
        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
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
    timezone: str = None,
    house_system: str = None,
    include_natal_aspects: bool = True
) -> Dict[str, Any]:
    """
    Generates a secondary progression chart for a native chart to a specific future date.

    Args:
        date_time: The birth date and time in ISO format, e.g., 'YYYY-MM-DD HH:MM:SS'.
        latitude: The latitude of the birth location, e.g., '32n43' or '32.71'.
        longitude: The longitude of the birth location, e.g., '117w09' or '-117.15'.
        progression_date_time: The date and time to progress the chart to, in ISO format.
        timezone: Optional IANA timezone name (e.g., 'Europe/London', 'America/New_York').
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.
        include_natal_aspects: Include progressed-to-natal aspects — the core
                               technique of secondary progressions — under
                               'natal_cross_aspects' (default: True).

    Returns:
        The full Progressed chart object serialized to a JSON dictionary, plus
        progressed-to-natal aspects under 'natal_cross_aspects' (each entry
        carries 'progressed_object' and 'natal_object').
    """
    try:
        logger.info(f"Generating progressed chart from {date_time} to {progression_date_time} at {latitude}, {longitude}")

        # Validate inputs
        validate_inputs(date_time, latitude, longitude)
        validate_inputs(progression_date_time, latitude, longitude)  # Reuse validation for progression date

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        call_settings = build_call_settings(house_system)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate charts
        natal_chart = charts.Natal(subject, settings=call_settings)
        progressed = charts.Progressed(subject, progression_date_time, settings=call_settings)

        # Serialize to JSON
        result = json.loads(json.dumps(progressed, cls=ToJSON))

        # Progressed-to-natal aspects (the chart's own internal aspects stay
        # under 'aspects'; the two lists are never merged)
        if include_natal_aspects:
            cross_chart = charts.Progressed(
                subject, progression_date_time,
                aspects_to=natal_chart, settings=call_settings
            )
            cross_data = json.loads(json.dumps(cross_chart, cls=ToJSON))
            result["natal_cross_aspects"] = build_full_cross_aspects(
                cross_data, "progressed_object")
        else:
            result["natal_cross_aspects"] = None

        # Extract progression datetime (handle wrapped DateTime object)
        progression_dt_obj = getattr(progressed, 'progression_date_time', None)
        if progression_dt_obj and hasattr(progression_dt_obj, 'datetime'):
            # It's a wrapped DateTime object, extract the datetime
            progression_dt_value = progression_dt_obj.datetime.strftime("%Y-%m-%d %H:%M:%S")
        elif progression_dt_obj:
            # Try to convert to string
            progression_dt_value = str(progression_dt_obj)
        else:
            # Fallback to input parameter
            progression_dt_value = progression_date_time

        transit_subject = charts.Subject(
            date_time=progression_date_time,
            latitude=lat,
            longitude=lon
        )
        reference_transits = charts.Natal(transit_subject, settings=call_settings)

        additional_events: List[Dict[str, Any]] = []
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

        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
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
    timezone: str = None,
    house_system: str = None,
    include_natal_aspects: bool = True,
    aspect_priority: str = "tight"
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
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.
        include_natal_aspects: Include progressed-to-natal aspects under
                               'natal_cross_aspects' (default: True).
        aspect_priority: Priority tier for the natal cross-aspects - "tight"
                         (default, 0-2° actual orb), "moderate" (>2-5°),
                         "loose" (>5°), or "all".

    Returns:
        A compact Progressed chart object serialized to a JSON dictionary, plus
        progressed-to-natal aspects under 'natal_cross_aspects' (each entry
        carries 'progressed_object' and 'natal_object').
    """
    try:
        logger.info(f"Generating compact progressed chart from {date_time} to {progression_date_time} at {latitude}, {longitude}")

        # Validate inputs
        validate_inputs(date_time, latitude, longitude)
        validate_inputs(progression_date_time, latitude, longitude)  # Reuse validation for progression date

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        call_settings = build_call_settings(house_system)

        # Create subject with optional timezone
        subject = create_subject(date_time, lat, lon, timezone)

        # Generate charts
        natal_chart = charts.Natal(subject, settings=call_settings)
        progressed = charts.Progressed(subject, progression_date_time, settings=call_settings)

        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(progressed, cls=CompactJSONSerializer))

        # Progressed-to-natal aspects (major objects/aspects, priority-filtered)
        if include_natal_aspects:
            cross_chart = charts.Progressed(
                subject, progression_date_time,
                aspects_to=natal_chart, settings=call_settings
            )
            cross_data = json.loads(json.dumps(cross_chart, cls=CompactJSONSerializer))
            cross_aspects, cross_summary = build_compact_cross_aspects(
                cross_data, "progressed_object", aspect_priority)
            result["natal_cross_aspects"] = cross_aspects
            result["natal_cross_aspect_summary"] = cross_summary
        else:
            result["natal_cross_aspects"] = None

        # Extract progression datetime (handle wrapped DateTime object)
        progression_dt_obj = getattr(progressed, 'progression_date_time', None)
        if progression_dt_obj and hasattr(progression_dt_obj, 'datetime'):
            # It's a wrapped DateTime object, extract the datetime
            progression_dt_value = progression_dt_obj.datetime.strftime("%Y-%m-%d %H:%M:%S")
        elif progression_dt_obj:
            # Try to convert to string
            progression_dt_value = str(progression_dt_obj)
        else:
            # Fallback to input parameter
            progression_dt_value = progression_date_time

        transit_subject = charts.Subject(
            date_time=progression_date_time,
            latitude=lat,
            longitude=lon
        )
        reference_transits = charts.Natal(transit_subject, settings=call_settings)

        additional_events: List[Dict[str, Any]] = []
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

        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
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
    partner_timezone: str = None,
    house_system: str = None
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
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

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
        
        call_settings = build_call_settings(house_system)

        # Create subjects with optional timezones
        native = create_subject(native_date_time, native_lat, native_lon, native_timezone)
        partner = create_subject(partner_date_time, partner_lat, partner_lon, partner_timezone)

        # Generate composite chart
        composite = charts.Composite(native, partner, settings=call_settings)

        # Serialize to JSON
        result = json.loads(json.dumps(composite, cls=ToJSON))
        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
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
    partner_timezone: str = None,
    house_system: str = None
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
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

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

        call_settings = build_call_settings(house_system)

        # Create subjects with optional timezones
        native = create_subject(native_date_time, native_lat, native_lon, native_timezone)
        partner = create_subject(partner_date_time, partner_lat, partner_lon, partner_timezone)

        # Generate composite chart
        composite = charts.Composite(native, partner, settings=call_settings)

        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(composite, cls=CompactJSONSerializer))
        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
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
    partner_timezone: str = None,
    house_system: str = None
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
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

    Returns:
        Dictionary with the aspects from the primary (native) Natal chart under
        'aspects', plus the applied_settings echo.
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
        call_settings = build_call_settings(house_system)

        native_subject = create_subject(native_date_time, native_lat, native_lon, native_timezone)
        partner_subject = create_subject(partner_date_time, partner_lat, partner_lon, partner_timezone)

        # Create partner chart first
        partner_chart = charts.Natal(partner_subject, settings=call_settings)

        # Create native chart with aspects to partner
        native_chart = charts.Natal(native_subject, aspects_to=partner_chart, settings=call_settings)

        # Extract and return aspects
        chart_data = json.loads(json.dumps(native_chart, cls=ToJSON))
        result = {
            "aspects": chart_data.get('aspects', {}),
            "applied_settings": build_applied_settings(house_system),
            "status": "success"
        }
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
    include_interpretations: bool = True,
    house_system: str = None
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
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

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
        call_settings = build_call_settings(house_system)

        native_subject = create_subject(native_date_time, native_lat, native_lon, native_timezone)
        partner_subject = create_subject(partner_date_time, partner_lat, partner_lon, partner_timezone)

        # Create partner chart first
        partner_chart = charts.Natal(partner_subject, settings=call_settings)

        # Create native chart with aspects to partner
        native_chart = charts.Natal(native_subject, aspects_to=partner_chart, settings=call_settings)

        # Serialize the entire chart using compact serializer to get filtered aspects
        compact_chart_data = json.loads(json.dumps(native_chart, cls=CompactJSONSerializer))
        filtered_aspects = compact_chart_data.get('aspects', [])

        # The serializer's from_object/to_object carry the inter-chart
        # direction: from = the native's planet, to = the partner's planet.
        for aspect in filtered_aspects:
            if isinstance(aspect, dict):
                aspect['native_object'] = aspect.pop('from_object', None)
                aspect['partner_object'] = aspect.pop('to_object', None)

        # Add interpretation hints if requested
        if include_interpretations:
            filtered_aspects = add_aspect_interpretations(filtered_aspects)

        result = {
            "aspects": filtered_aspects,
            "applied_settings": build_applied_settings(house_system),
            "status": "success"
        }
        logger.info("Compact synastry aspects generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating compact synastry aspects: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_transit_chart(
    latitude: str,
    longitude: str,
    house_system: str = None
) -> Dict[str, Any]:
    """
    Generates a chart for the current moment for a given location, showing current planetary positions.

    Args:
        latitude: The latitude of the location, e.g., '32n43'.
        longitude: The longitude of the location, e.g., '117w09'.
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

    Returns:
        The full Transits chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating transit chart for current time at {latitude}, {longitude}")

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        call_settings = build_call_settings(house_system)

        # Generate transits chart
        transits = charts.Transits(latitude=lat, longitude=lon, settings=call_settings)

        # Serialize to JSON
        result = json.loads(json.dumps(transits, cls=ToJSON))
        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
        logger.info("Transit chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating transit chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_compact_transit_chart(
    latitude: str,
    longitude: str,
    house_system: str = None
) -> Dict[str, Any]:
    """
    Generates a compact chart for the current moment for a given location, showing current planetary positions with filtering.

    This tool provides a streamlined version of the transit chart, focusing on the most critical
    astrological data: major celestial objects and their current positions. It omits
    minor objects and detailed properties for a faster and more concise output.

    Args:
        latitude: The latitude of the location, e.g., '32n43'.
        longitude: The longitude of the location, e.g., '117w09'.
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.

    Returns:
        A compact Transits chart object serialized to a JSON dictionary.
    """
    try:
        logger.info(f"Generating compact transit chart for current time at {latitude}, {longitude}")

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        call_settings = build_call_settings(house_system)

        # Generate transits chart
        transits = charts.Transits(latitude=lat, longitude=lon, settings=call_settings)

        # Serialize to JSON using the compact serializer
        result = json.loads(json.dumps(transits, cls=CompactJSONSerializer))
        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
        logger.info("Compact transit chart generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating compact transit chart: {str(e)}")
        return handle_chart_error(e)


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
    include_lifecycle_events: bool = True,
    house_system: str = None
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
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Applied to both natal and transit charts.
                      Does not affect the session-global settings.

    Returns:
        Dictionary containing natal chart summary, transit positions, paginated aspects,
        aspect summary, pagination metadata, and lifecycle events (if enabled).
    """
    try:
        logger.info(f"[TRANSIT-FULL] Starting transit-to-natal for natal {natal_date_time} with transits at {transit_date_time}")

        # CRITICAL FIX: Handle None for aspect_priority (MCP may pass None instead of using default)
        if aspect_priority is None:
            aspect_priority = "tight"
            logger.info(f"[TRANSIT-FULL] aspect_priority was None, defaulting to 'tight'")

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

        call_settings = build_call_settings(house_system)

        # Create natal and transit subjects. The optional timezone applies to
        # both datetimes; when omitted, immanuel infers it from coordinates.
        logger.debug(f"[TRANSIT-FULL] Creating natal subject")
        natal_subject = create_subject(natal_date_time, natal_lat, natal_lon, timezone)

        # Create transit subject for the specified date
        logger.debug(f"[TRANSIT-FULL] Creating transit subject")
        transit_subject = create_subject(transit_date_time, transit_lat, transit_lon, timezone)

        # Generate natal chart
        logger.debug(f"[TRANSIT-FULL] Generating natal chart")
        natal_chart = charts.Natal(natal_subject, settings=call_settings)

        # Generate transit chart with aspects to natal
        logger.debug(f"[TRANSIT-FULL] Generating transit chart with aspects to natal")
        transit_chart = charts.Natal(transit_subject, aspects_to=natal_chart, settings=call_settings)

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

        # Add object1 and object2 fields to each aspect, plus the direction.
        # active/passive are speed-ordered by immanuel and say nothing about
        # which chart each object belongs to; from_index/to_index (captured
        # from the nested aspect structure) do: from = transiting object,
        # to = natal object.
        for aspect in filtered_aspects:
            if isinstance(aspect, dict):
                active_id = aspect.get('active')
                passive_id = aspect.get('passive')
                if active_id in object_names:
                    aspect['object1'] = object_names[active_id]
                if passive_id in object_names:
                    aspect['object2'] = object_names[passive_id]
                from_id = aspect.pop('from_index', None)
                to_id = aspect.pop('to_index', None)
                if from_id in object_names and to_id in object_names:
                    aspect['transiting_object'] = object_names[from_id]
                    aspect['natal_object'] = object_names[to_id]

        logger.info(f"[TRANSIT-FULL] Total aspects after filtering: {len(filtered_aspects)}")

        # === PAGINATION LOGIC ===
        # Classify all aspects by priority tier
        tight_aspects, moderate_aspects, loose_aspects = classify_all_aspects(filtered_aspects)
        logger.info(f"[TRANSIT-FULL] Classified aspects - tight: {len(tight_aspects)}, moderate: {len(moderate_aspects)}, loose: {len(loose_aspects)}")

        # Determine which aspects to return. The deprecated include_all_aspects
        # flag is treated as aspect_priority="all" so it flows through the same
        # lifecycle size guard instead of bypassing it.
        if include_all_aspects:
            logger.warning("[TRANSIT-FULL] include_all_aspects=True (deprecated) - treating as aspect_priority='all'")
            aspect_priority = "all"

        # Validate aspect_priority parameter
        valid_priorities = ["tight", "moderate", "loose", "all"]
        if aspect_priority not in valid_priorities:
            logger.warning(f"[TRANSIT-FULL] Invalid aspect_priority '{aspect_priority}', defaulting to 'tight'")
            aspect_priority = "tight"

        # Auto-adjust priority when lifecycle events enabled to avoid MCP size limits.
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
            "timezone": timezone,
            "applied_settings": build_applied_settings(house_system),
            "status": "success"
        }

        # === LIFECYCLE EVENTS DETECTION ===
        if include_lifecycle_events:
            attach_lifecycle_section(
                result,
                natal_chart=natal_chart,
                comparison_chart=transit_chart,
                birth_datetime=natal_date_time,
                comparison_datetime=transit_date_time
            )
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
    include_lifecycle_events: bool = True,
    house_system: str = None
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
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Applied to both natal and transit charts.
                      Does not affect the session-global settings.

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

        call_settings = build_call_settings(house_system)

        # Create natal and transit subjects. The optional timezone applies to
        # both datetimes; when omitted, immanuel infers it from coordinates.
        natal_subject = create_subject(natal_date_time, natal_lat, natal_lon, timezone)

        # Create transit subject for the specified date
        transit_subject = create_subject(transit_date_time, transit_lat, transit_lon, timezone)

        # Generate natal chart
        natal_chart = charts.Natal(natal_subject, settings=call_settings)

        # Generate transit chart with aspects to natal
        transit_chart = charts.Natal(transit_subject, aspects_to=natal_chart, settings=call_settings)

        # Serialize transit chart using compact serializer
        transit_data = json.loads(json.dumps(transit_chart, cls=CompactJSONSerializer))

        # Get aspects and optionally add interpretations. The serializer's
        # from_object/to_object carry the direction: from = transiting
        # object, to = natal object.
        aspects = transit_data.get('aspects', [])
        for aspect in aspects:
            if isinstance(aspect, dict):
                aspect['transiting_object'] = aspect.pop('from_object', None)
                aspect['natal_object'] = aspect.pop('to_object', None)
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
            "timezone": timezone,
            "applied_settings": build_applied_settings(house_system),
            "status": "success"
        }

        if include_lifecycle_events:
            attach_lifecycle_section(
                result,
                natal_chart=natal_chart,
                comparison_chart=transit_chart,
                birth_datetime=natal_date_time,
                comparison_datetime=transit_date_time
            )
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

    This changes global state for every subsequent chart in the session. For
    a one-off setting, prefer the per-call parameters (e.g. `house_system`)
    on the chart tools. Use `reset_immanuel_settings` to restore defaults.

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
        from immanuel_mcp.utils.settings import (
            resolve_house_system,
            resolve_progression_method,
            resolve_orb_calculation,
        )

        # The legacy 'orb_calculation_method' key never matched the library
        # attribute; accept it as an alias for the real 'orb_calculation'.
        if setting_key == 'orb_calculation_method':
            setting_key = 'orb_calculation'

        # Validate setting key. (lunar_phase_method and solar_arc_method were
        # dropped in v0.6.0: they do not exist in the immanuel library and
        # configuring them was a silent no-op.)
        valid_settings = [
            'house_system', 'objects', 'angles', 'aspects', 'locale',
            'mc_progression_method', 'orb_calculation'
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
            # Convert string to constant, with validation listing valid names
            const_value = resolve_house_system(setting_value)
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
            # Convert string to constant, with validation listing valid names
            const_value = resolve_progression_method(setting_value)
            setattr(settings, setting_key, const_value)

        elif setting_key == 'orb_calculation':
            # Convert string to constant, with validation listing valid names
            const_value = resolve_orb_calculation(setting_value)
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
            "new_value": setting_value,
            "scope": "session-global"
        }
        logger.info("Setting configured successfully")
        return result

    except Exception as e:
        logger.error(f"Error configuring setting: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def reset_immanuel_settings() -> Dict[str, Any]:
    """
    Reset the global Immanuel settings to library defaults, undoing every
    change made via configure_immanuel_settings in this session.

    Returns:
        Confirmation with a summary of the restored default values.
    """
    try:
        from immanuel_mcp.utils.settings import reset_global_settings

        logger.info("Resetting Immanuel settings to library defaults")
        restored = reset_global_settings()
        return {
            "status": "success",
            "message": "Immanuel settings restored to library defaults.",
            "scope": "session-global",
            "restored_defaults": restored
        }

    except Exception as e:
        logger.error(f"Error resetting settings: {str(e)}")
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
        from immanuel.const import names as names_const
        settings = setup.settings

        # House system mapping straight from the library so new systems
        # never show up as "Unknown"
        HOUSE_SYSTEMS = dict(names_const.HOUSE_SYSTEMS)

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


# Register the lunar return tools on the shared MCP instance. This import
# must come after the tool definitions above so a partially initialized
# module is never observed, and must not be moved into a try/except: a
# missing chart module is a startup error, not an optional feature.
import immanuel_mcp.charts.lunar_return  # noqa: E402,F401


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

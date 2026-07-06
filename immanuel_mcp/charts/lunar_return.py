"""Lunar Return Chart Generation

A lunar return occurs when the Moon returns to its exact natal position,
happening approximately every 27-28 days. This is a monthly predictive
technique showing themes and energies for the coming month.

Since the Immanuel library doesn't have a built-in LunarReturn class,
this module implements custom logic to:
1. Calculate the natal Moon's position
2. Find when the transiting Moon returns to that position
3. Generate a chart for that moment
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict

from immanuel import charts
from immanuel.classes.serialize import ToJSON
from immanuel.const import chart as chart_const
from immanuel.tools import date as date_tools
from immanuel.tools import ephemeris
from scripts.compact_serializer import CompactJSONSerializer

from ..app import mcp
from ..lifecycle.attach import attach_lifecycle_section
from ..utils.coordinates import parse_coordinate
from ..utils.subjects import create_subject
from ..utils.errors import handle_chart_error, validate_inputs
from ..utils.settings import build_call_settings, build_applied_settings
from ..optimizers.cross_aspects import (
    build_full_cross_aspects,
    build_compact_cross_aspects,
)

logger = logging.getLogger(__name__)

# Search parameters. The Moon moves ~13 degrees/day and never retrogrades,
# so a 6-hour scan step (~3.3 degrees) safely brackets the crossing, and
# bisection converges to well under a minute of clock time.
_SCAN_STEP_JD = 0.25
_ONE_MINUTE_JD = 1 / 1440


def _moon_longitude(jd: float) -> float:
    """Geocentric ecliptic longitude of the Moon at a Julian date."""
    return ephemeris.get_planet(chart_const.MOON, jd)['lon']


def _signed_delta(moon_lon: float, target_lon: float) -> float:
    """Signed angular distance from target to Moon, normalized to (-180, 180]."""
    diff = (moon_lon - target_lon) % 360
    return diff - 360 if diff > 180 else diff


def _find_lunar_return_jd(
    natal_moon_longitude: float,
    year: int,
    month: int,
    lat: float,
    lon: float,
    timezone: str = None
) -> float:
    """
    Find the Julian date of the Moon's return to its natal position within
    a given month. See find_lunar_return_date for the search semantics; the
    month window is interpreted in the given timezone (or the zone inferred
    from the coordinates when omitted).

    Raises:
        ValueError: If no lunar return is found in the specified month
    """
    target = natal_moon_longitude % 360

    month_start = datetime(year, month, 1)
    month_end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

    start_jd = date_tools.to_jd(month_start, lat=lat, lon=lon, time_zone=timezone)
    end_jd = date_tools.to_jd(month_end, lat=lat, lon=lon, time_zone=timezone)

    # Scan for a sign change in the signed delta. The Moon only moves
    # forward, so the delta increases through 0 at the return; jumps of
    # ~360 at the antipode are excluded by the wrap check.
    prev_jd = start_jd
    prev_delta = _signed_delta(_moon_longitude(start_jd), target)

    jd = start_jd + _SCAN_STEP_JD
    while jd < end_jd + _SCAN_STEP_JD:
        probe_jd = min(jd, end_jd)
        delta = _signed_delta(_moon_longitude(probe_jd), target)

        if prev_delta < 0 <= delta and (delta - prev_delta) < 180:
            # Bracketed: bisect to under a minute.
            lo, hi = prev_jd, probe_jd
            while (hi - lo) > _ONE_MINUTE_JD / 2:
                mid = (lo + hi) / 2
                if _signed_delta(_moon_longitude(mid), target) >= 0:
                    hi = mid
                else:
                    lo = mid
            return (lo + hi) / 2

        if probe_jd >= end_jd:
            break
        prev_jd, prev_delta = probe_jd, delta
        jd += _SCAN_STEP_JD

    raise ValueError(f"No lunar return found in {year}-{month:02d}")


def find_lunar_return_date(
    natal_moon_longitude: float,
    year: int,
    month: int,
    lat: float,
    lon: float,
    timezone: str = None
) -> datetime:
    """
    Find the moment the Moon returns to its natal position within a given month.

    The search runs in Julian-day space against the ephemeris directly (a
    single swisseph call per probe) rather than constructing a full chart
    per probe, and bisects the bracketed crossing to under one minute of
    clock time.

    Note: the sidereal lunar month is ~27.3 days, so a 30/31-day calendar
    month occasionally contains two returns (one near the 1st and one near
    the end). This function returns the first.

    Args:
        natal_moon_longitude: The natal Moon's ecliptic longitude in degrees
        year: The year to search for the lunar return
        month: The month to search for the lunar return (1-12)
        lat: Latitude for the chart
        lon: Longitude for the chart
        timezone: Optional IANA timezone (month boundaries and the returned
            datetime are interpreted in this zone, or the zone inferred from
            the coordinates when omitted)

    Returns:
        Naive datetime of the lunar return moment in the chart's local time

    Raises:
        ValueError: If no lunar return is found in the specified month
    """
    return_jd = _find_lunar_return_jd(natal_moon_longitude, year, month, lat, lon, timezone)
    local_dt = date_tools.to_datetime(return_jd, lat=lat, lon=lon, time_zone=timezone)
    return local_dt.replace(tzinfo=None)


@mcp.tool()
def generate_lunar_return_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    return_year: int,
    return_month: int,
    timezone: str = None,
    house_system: str = None,
    include_natal_aspects: bool = True,
    return_latitude: str = None,
    return_longitude: str = None
) -> Dict[str, Any]:
    """
    Calculate lunar return chart for specified month/year.

    A lunar return occurs when the Moon returns to its natal position,
    happening approximately every 27-28 days. This is a monthly predictive
    technique showing themes and energies for the coming month.

    Return charts are conventionally cast for where the person is at the
    return moment, not the birthplace: pass return_latitude/return_longitude
    to relocate. The return moment itself (found by ephemeris search from the
    birth-location natal Moon) stays identical; only the houses/angles change.
    Relocated charts report the return moment in the return location's zone.

    Args:
        date_time: Birth date and time in ISO format (e.g., '1990-01-15 14:30:00')
        latitude: Birth location latitude (e.g., '32n43' or '32.71')
        longitude: Birth location longitude (e.g., '117w09' or '-117.15')
        return_year: Year for the lunar return (e.g., 2025)
        return_month: Month for the lunar return (1-12)
        timezone: Optional IANA timezone name (e.g., 'America/New_York')
        house_system: Optional house system for this call only (e.g., 'CAMPANUS',
                      'WHOLE_SIGN'). Does not affect the session-global settings.
        include_natal_aspects: Include return-planet-to-natal aspects under
                               'natal_cross_aspects' (default: True).
        return_latitude: Optional latitude to relocate the return chart to
                         (defaults to the birth latitude).
        return_longitude: Optional longitude to relocate the return chart to
                          (defaults to the birth longitude).

    Returns:
        Full lunar return chart with all positions and aspects, plus
        return-to-natal aspects under 'natal_cross_aspects' (each entry
        carries 'return_object' and 'natal_object') and a 'return_location'
        echo
    """
    try:
        logger.info(f"Generating lunar return chart for {date_time} at {latitude}, {longitude} for {return_year}-{return_month:02d}")

        # Validate inputs
        validate_inputs(date_time, latitude, longitude)

        if not 1 <= return_month <= 12:
            raise ValueError(f"Return month must be between 1 and 12. Got: {return_month}")
        if not 1900 <= return_year <= 2100:
            raise ValueError(f"Return year must be between 1900 and 2100. Got: {return_year}")

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        call_settings = build_call_settings(house_system)

        relocated = return_latitude is not None or return_longitude is not None
        return_lat = parse_coordinate(return_latitude, is_latitude=True) if return_latitude else lat
        return_lon = parse_coordinate(return_longitude, is_latitude=False) if return_longitude else lon

        # Get natal Moon's position
        natal_subject = create_subject(date_time, lat, lon, timezone)
        natal_chart = charts.Natal(natal_subject, settings=call_settings)
        natal_moon = natal_chart.objects.get(4000002)  # Moon's index

        if natal_moon is None:
            raise ValueError("Could not calculate natal Moon position")

        natal_moon_longitude = natal_moon.longitude.raw

        # Find the lunar return moment. The search always runs against the
        # birth-location natal Moon and month window (unchanged by relocation).
        return_jd = _find_lunar_return_jd(
            natal_moon_longitude,
            return_year,
            return_month,
            lat,
            lon,
            timezone
        )
        lunar_return_dt = date_tools.to_datetime(
            return_jd, lat=lat, lon=lon, time_zone=timezone
        ).replace(tzinfo=None)

        # Generate chart for the return moment. Relocation must preserve the
        # absolute instant, not the wall-clock string: the timezone-aware
        # local datetime at the return location carries its own zone into
        # the Subject.
        if relocated:
            return_local_dt = date_tools.to_datetime(return_jd, lat=return_lat, lon=return_lon)
            return_subject = charts.Subject(
                date_time=return_local_dt,
                latitude=return_lat,
                longitude=return_lon
            )
            return_date_value = return_local_dt.isoformat()
        else:
            return_subject = create_subject(
                lunar_return_dt.isoformat(),
                lat,
                lon,
                timezone
            )
            return_date_value = lunar_return_dt.isoformat()
        lunar_return_chart = charts.Natal(return_subject, settings=call_settings)

        # Serialize to JSON
        result = json.loads(json.dumps(lunar_return_chart, cls=ToJSON))

        # Return-to-natal aspects (the chart's own internal aspects stay
        # under 'aspects'; the two lists are never merged)
        if include_natal_aspects:
            cross_chart = charts.Natal(
                return_subject, aspects_to=natal_chart, settings=call_settings)
            cross_data = json.loads(json.dumps(cross_chart, cls=ToJSON))
            result["natal_cross_aspects"] = build_full_cross_aspects(
                cross_data, "return_object")
        else:
            result["natal_cross_aspects"] = None

        # Add metadata about the lunar return
        result['lunar_return_info'] = {
            'return_date': return_date_value,
            'natal_moon_longitude': natal_moon_longitude,
            'return_year': return_year,
            'return_month': return_month
        }
        result['return_location'] = {
            'latitude': return_lat,
            'longitude': return_lon,
            'relocated': relocated
        }

        # Lifecycle context at the return moment (the return chart doubles
        # as the transit reference)
        attach_lifecycle_section(
            result,
            natal_chart=natal_chart,
            comparison_chart=lunar_return_chart,
            birth_datetime=date_time,
            comparison_datetime=lunar_return_dt
        )

        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
        logger.info(f"Lunar return chart generated successfully for {lunar_return_dt.isoformat()}")
        return result

    except Exception as e:
        logger.error(f"Error generating lunar return chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_compact_lunar_return_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    return_year: int,
    return_month: int,
    timezone: str = None,
    house_system: str = None,
    include_natal_aspects: bool = True,
    aspect_priority: str = "tight",
    return_latitude: str = None,
    return_longitude: str = None
) -> Dict[str, Any]:
    """
    Calculate compact lunar return chart with optimized response.

    Return charts are conventionally cast for where the person is at the
    return moment, not the birthplace: pass return_latitude/return_longitude
    to relocate. The return moment itself (found by ephemeris search from the
    birth-location natal Moon) stays identical; only the houses/angles change.
    Relocated charts report the return moment in the return location's zone.

    Same as generate_lunar_return_chart but with streamlined output:
    - Major objects only (Sun through Pluto, angles)
    - Major aspects only (conjunction, opposition, square, trine, sextile)
    - Optimized position format (84.9% smaller)

    Args:
        date_time: Birth date and time in ISO format (e.g., '1990-01-15 14:30:00')
        latitude: Birth location latitude (e.g., '32n43' or '32.71')
        longitude: Birth location longitude (e.g., '117w09' or '-117.15')
        return_year: Year for the lunar return (e.g., 2025)
        return_month: Month for the lunar return (1-12)
        timezone: Optional IANA timezone name (e.g., 'America/New_York')
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
        Compact lunar return chart optimized for LLM processing, plus
        return-to-natal aspects under 'natal_cross_aspects' (each entry
        carries 'return_object' and 'natal_object') and a 'return_location'
        echo
    """
    try:
        logger.info(f"Generating compact lunar return chart for {date_time} at {latitude}, {longitude} for {return_year}-{return_month:02d}")

        # Validate inputs
        validate_inputs(date_time, latitude, longitude)

        if not 1 <= return_month <= 12:
            raise ValueError(f"Return month must be between 1 and 12. Got: {return_month}")
        if not 1900 <= return_year <= 2100:
            raise ValueError(f"Return year must be between 1900 and 2100. Got: {return_year}")

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        call_settings = build_call_settings(house_system)

        relocated = return_latitude is not None or return_longitude is not None
        return_lat = parse_coordinate(return_latitude, is_latitude=True) if return_latitude else lat
        return_lon = parse_coordinate(return_longitude, is_latitude=False) if return_longitude else lon

        # Get natal Moon's position
        natal_subject = create_subject(date_time, lat, lon, timezone)
        natal_chart = charts.Natal(natal_subject, settings=call_settings)
        natal_moon = natal_chart.objects.get(4000002)  # Moon's index

        if natal_moon is None:
            raise ValueError("Could not calculate natal Moon position")

        natal_moon_longitude = natal_moon.longitude.raw

        # Find the lunar return moment. The search always runs against the
        # birth-location natal Moon and month window (unchanged by relocation).
        return_jd = _find_lunar_return_jd(
            natal_moon_longitude,
            return_year,
            return_month,
            lat,
            lon,
            timezone
        )
        lunar_return_dt = date_tools.to_datetime(
            return_jd, lat=lat, lon=lon, time_zone=timezone
        ).replace(tzinfo=None)

        # Generate chart for the return moment. Relocation must preserve the
        # absolute instant, not the wall-clock string: the timezone-aware
        # local datetime at the return location carries its own zone into
        # the Subject.
        if relocated:
            return_local_dt = date_tools.to_datetime(return_jd, lat=return_lat, lon=return_lon)
            return_subject = charts.Subject(
                date_time=return_local_dt,
                latitude=return_lat,
                longitude=return_lon
            )
            return_date_value = return_local_dt.isoformat()
        else:
            return_subject = create_subject(
                lunar_return_dt.isoformat(),
                lat,
                lon,
                timezone
            )
            return_date_value = lunar_return_dt.isoformat()
        lunar_return_chart = charts.Natal(return_subject, settings=call_settings)

        # Serialize to JSON using compact serializer
        result = json.loads(json.dumps(lunar_return_chart, cls=CompactJSONSerializer))

        # Return-to-natal aspects (major objects/aspects, priority-filtered)
        if include_natal_aspects:
            cross_chart = charts.Natal(
                return_subject, aspects_to=natal_chart, settings=call_settings)
            cross_data = json.loads(json.dumps(cross_chart, cls=CompactJSONSerializer))
            cross_aspects, cross_summary = build_compact_cross_aspects(
                cross_data, "return_object", aspect_priority)
            result["natal_cross_aspects"] = cross_aspects
            result["natal_cross_aspect_summary"] = cross_summary
        else:
            result["natal_cross_aspects"] = None

        # Add metadata about the lunar return
        result['lunar_return_info'] = {
            'return_date': return_date_value,
            'natal_moon_longitude': natal_moon_longitude,
            'return_year': return_year,
            'return_month': return_month
        }
        result['return_location'] = {
            'latitude': return_lat,
            'longitude': return_lon,
            'relocated': relocated
        }

        # Lifecycle context at the return moment (the return chart doubles
        # as the transit reference)
        attach_lifecycle_section(
            result,
            natal_chart=natal_chart,
            comparison_chart=lunar_return_chart,
            birth_datetime=date_time,
            comparison_datetime=lunar_return_dt
        )

        result["applied_settings"] = build_applied_settings(house_system)
        result["status"] = "success"
        logger.info(f"Compact lunar return chart generated successfully for {lunar_return_dt.isoformat()}")
        return result

    except Exception as e:
        logger.error(f"Error generating compact lunar return chart: {str(e)}")
        return handle_chart_error(e)

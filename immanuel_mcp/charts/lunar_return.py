"""Lunar Return Chart Generation

A lunar return occurs when the Moon returns to its exact natal position,
happening approximately every 27-28 days. This is a monthly predictive
technique showing themes and energies for the coming month.

Since the Immanuel library doesn't have a built-in LunarReturn class,
this module implements custom logic to:
1. Calculate the natal Moon's position
2. Find when the transiting Moon returns to that position, via the library's
   fixed-point aspect search (immanuel.tools.transit, 1.5.4+)
3. Generate a chart for that moment
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict

from immanuel import charts
from immanuel.const import chart as chart_const
from immanuel.tools import date as date_tools
from ..serializers import CompactJSONSerializer, serialize_full_chart

from ..app import mcp
from ..utils.call_context import reports_warnings
from ..lifecycle.attach import attach_lifecycle_section
from ..utils.coordinates import parse_coordinate
from ..utils.datetimes import iso_timestamp
from ..utils.subjects import create_subject
from ..utils.errors import handle_chart_error, validate_aspect_priority, validate_inputs
from ..utils.settings import build_call_config, build_applied_settings
from ..utils.search import crossed_by, find_return_jd
from ..optimizers.cross_aspects import (
    build_full_cross_aspects,
    build_compact_cross_aspects,
)

logger = logging.getLogger(__name__)


# Restart the search this far past a found return, so it can't find the
# same one again; the next is ~27.3 days on.
_RESTART_DAYS = 1.0
# Returns this close to a month boundary are placed by crossed_by().
_BOUNDARY_DAYS = 1e-5


def _find_lunar_return_jds(
    natal_moon_longitude: float,
    year: int,
    month: int,
    lat: float,
    lon: float,
    timezone: str = None
) -> list:
    """
    Julian dates of every return of the Moon to its natal position within a
    given month: one, or two when a return falls near the 1st and the next
    ~27.3 days later still inside the month. The month window is interpreted
    in the given timezone (or the zone inferred from the coordinates).
    """
    month_start = datetime(year, month, 1)
    month_end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

    start_jd = date_tools.to_jd(month_start, lat=lat, lon=lon, time_zone=timezone)
    end_jd = date_tools.to_jd(month_end, lat=lat, lon=lon, time_zone=timezone)

    def in_month(jd: float) -> bool:
        # Decided on full precision, never on a rounded timestamp. A return
        # within the search precision of either boundary is placed by the
        # Moon's side of the target at the boundary JD itself, which the
        # neighbouring month computes identically, so it lands in exactly
        # one month.
        for boundary, inside_if_crossed in ((start_jd, False), (end_jd, True)):
            if abs(jd - boundary) < _BOUNDARY_DAYS:
                return crossed_by(chart_const.MOON, natal_moon_longitude, boundary) == inside_if_crossed
        return start_jd <= jd < end_jd

    found = []
    return_jd = find_return_jd(
        chart_const.MOON, natal_moon_longitude, start_jd - _BOUNDARY_DAYS)
    while return_jd < end_jd + _BOUNDARY_DAYS:
        if in_month(return_jd):
            found.append(return_jd)
        return_jd = find_return_jd(
            chart_const.MOON, natal_moon_longitude, return_jd + _RESTART_DAYS)
    return found


def _subject_at(jd: float, lat: float, lon: float, timezone: str = None) -> charts.Subject:
    """
    A Subject at the return instant, given by its Julian date. Never by a
    wall-clock time: in the repeated hour of a fall-back night immanuel
    resolves a local time - and even an aware datetime, UTC included - to
    the first reading, so a return at 01:30 GMT on 2026-10-25 was cast at
    01:30 BST, an hour early. The Julian date has no such ambiguity.
    """
    kwargs = {"date_time": jd, "latitude": lat, "longitude": lon}
    if timezone:
        kwargs["timezone"] = timezone
    return charts.Subject(**kwargs)


def _moment_iso(jd: float, lat: float, lon: float, timezone: str = None) -> str:
    """A return moment as return_date shows it (see iso_timestamp), in the
    given zone, or the zone inferred from the coordinates."""
    return iso_timestamp(date_tools.to_datetime(jd, lat=lat, lon=lon, time_zone=timezone))


def _find_lunar_return_jd(
    natal_moon_longitude: float,
    year: int,
    month: int,
    lat: float,
    lon: float,
    timezone: str = None,
    occurrence: int = 1,
) -> float:
    """
    The Julian date of the `occurrence`-th lunar return in a month (1 = the
    first). See _find_lunar_return_jds.

    Raises:
        ValueError: If the month has no such return. The message lists the
            returns it does have.
    """
    returns = _find_lunar_return_jds(natal_moon_longitude, year, month, lat, lon, timezone)
    if not returns:
        raise ValueError(f"No lunar return found in {year}-{month:02d}")
    if not 1 <= occurrence <= len(returns):
        listed = ", ".join(_moment_iso(jd, lat, lon, timezone) for jd in returns)
        raise ValueError(
            f"occurrence={occurrence} does not exist: {year}-{month:02d} has "
            f"{len(returns)} lunar return{'s' if len(returns) > 1 else ''} "
            f"({listed}). Use occurrence 1 to {len(returns)}.")
    return returns[occurrence - 1]


def find_lunar_return_date(
    natal_moon_longitude: float,
    year: int,
    month: int,
    lat: float,
    lon: float,
    timezone: str = None,
    occurrence: int = 1,
) -> datetime:
    """
    Find the moment the Moon returns to its natal position within a given month.

    The search delegates to the library's fixed-point aspect search, which
    converges on the crossing to within 1e-6 degrees without constructing a
    chart per probe.

    Note: the sidereal lunar month is ~27.3 days, so a 30/31-day calendar
    month occasionally contains two returns (one near the 1st and one near
    the end). `occurrence` picks one; the default is the first.

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
    return_jd = _find_lunar_return_jd(
        natal_moon_longitude, year, month, lat, lon, timezone, occurrence)
    local_dt = date_tools.to_datetime(return_jd, lat=lat, lon=lon, time_zone=timezone)
    return local_dt.replace(tzinfo=None)


@mcp.tool()
@reports_warnings
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
    return_longitude: str = None,
    occurrence: int = 1
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
        occurrence: Which return in the month (default 1). About one month in
                    three has two (the sidereal month is ~27.3 days), and the
                    second is reachable only with occurrence=2.
                    lunar_return_info.returns_in_month always lists every
                    return in the month; asking for one that doesn't exist
                    returns an error naming those that do.

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

        call_config = build_call_config(house_system)

        relocated = return_latitude is not None or return_longitude is not None
        return_lat = parse_coordinate(return_latitude, is_latitude=True) if return_latitude else lat
        return_lon = parse_coordinate(return_longitude, is_latitude=False) if return_longitude else lon

        # Get natal Moon's position
        natal_subject = create_subject(date_time, lat, lon, timezone)
        natal_chart = charts.Natal(natal_subject, config=call_config)
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
            timezone,
            occurrence
        )
        return_moment = date_tools.to_datetime(
            return_jd, lat=lat, lon=lon, time_zone=timezone)
        lunar_return_dt = return_moment.replace(tzinfo=None)

        # Generate chart for the return moment. Relocation must preserve the
        # absolute instant, not the wall-clock string: the timezone-aware
        # local datetime at the return location carries its own zone into
        # the Subject.
        if relocated:
            return_local_dt = date_tools.to_datetime(return_jd, lat=return_lat, lon=return_lon)
            return_subject = _subject_at(return_jd, return_lat, return_lon)
            return_date_value = iso_timestamp(return_local_dt)
        else:
            return_subject = _subject_at(return_jd, lat, lon, timezone)
            return_date_value = iso_timestamp(return_moment)
        lunar_return_chart = charts.Natal(return_subject, config=call_config)

        # Serialize to JSON
        result = serialize_full_chart(lunar_return_chart)

        # Return-to-natal aspects (the chart's own internal aspects stay
        # under 'aspects'; the two lists are never merged)
        if include_natal_aspects:
            cross_chart = charts.Natal(
                return_subject, aspects_to=natal_chart, config=call_config)
            cross_data = serialize_full_chart(cross_chart)
            result["natal_cross_aspects"] = build_full_cross_aspects(
                cross_data, "return_object")
        else:
            result["natal_cross_aspects"] = None

        # Add metadata about the lunar return
        result['lunar_return_info'] = {
            'return_date': return_date_value,
            'natal_moon_longitude': natal_moon_longitude,
            'return_year': return_year,
            'return_month': return_month,
            'occurrence': occurrence,
            # Every return in the month, so a second one is visible without
            # guessing; select it with occurrence=2. Same zone as return_date.
            'returns_in_month': [
                _moment_iso(jd, return_lat, return_lon) if relocated
                else _moment_iso(jd, lat, lon, timezone)
                for jd in _find_lunar_return_jds(
                    natal_moon_longitude, return_year, return_month, lat, lon, timezone)
            ],
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
@reports_warnings
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
    return_longitude: str = None,
    occurrence: int = 1
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
        occurrence: Which return in the month (default 1). About one month in
                    three has two (the sidereal month is ~27.3 days), and the
                    second is reachable only with occurrence=2.
                    lunar_return_info.returns_in_month always lists every
                    return in the month; asking for one that doesn't exist
                    returns an error naming those that do.

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
        validate_aspect_priority(aspect_priority)

        if not 1 <= return_month <= 12:
            raise ValueError(f"Return month must be between 1 and 12. Got: {return_month}")
        if not 1900 <= return_year <= 2100:
            raise ValueError(f"Return year must be between 1900 and 2100. Got: {return_year}")

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        call_config = build_call_config(house_system)

        relocated = return_latitude is not None or return_longitude is not None
        return_lat = parse_coordinate(return_latitude, is_latitude=True) if return_latitude else lat
        return_lon = parse_coordinate(return_longitude, is_latitude=False) if return_longitude else lon

        # Get natal Moon's position
        natal_subject = create_subject(date_time, lat, lon, timezone)
        natal_chart = charts.Natal(natal_subject, config=call_config)
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
            timezone,
            occurrence
        )
        return_moment = date_tools.to_datetime(
            return_jd, lat=lat, lon=lon, time_zone=timezone)
        lunar_return_dt = return_moment.replace(tzinfo=None)

        # Generate chart for the return moment. Relocation must preserve the
        # absolute instant, not the wall-clock string: the timezone-aware
        # local datetime at the return location carries its own zone into
        # the Subject.
        if relocated:
            return_local_dt = date_tools.to_datetime(return_jd, lat=return_lat, lon=return_lon)
            return_subject = _subject_at(return_jd, return_lat, return_lon)
            return_date_value = iso_timestamp(return_local_dt)
        else:
            return_subject = _subject_at(return_jd, lat, lon, timezone)
            return_date_value = iso_timestamp(return_moment)
        lunar_return_chart = charts.Natal(return_subject, config=call_config)

        # Serialize to JSON using compact serializer
        result = json.loads(json.dumps(lunar_return_chart, cls=CompactJSONSerializer))

        # Return-to-natal aspects (major objects/aspects, priority-filtered)
        if include_natal_aspects:
            cross_chart = charts.Natal(
                return_subject, aspects_to=natal_chart, config=call_config)
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
            'return_month': return_month,
            'occurrence': occurrence,
            # Every return in the month, so a second one is visible without
            # guessing; select it with occurrence=2. Same zone as return_date.
            'returns_in_month': [
                _moment_iso(jd, return_lat, return_lon) if relocated
                else _moment_iso(jd, lat, lon, timezone)
                for jd in _find_lunar_return_jds(
                    natal_moon_longitude, return_year, return_month, lat, lon, timezone)
            ],
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

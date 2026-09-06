"""Lunation and eclipse calendar.

Immanuel 1.5.4's transit module can locate new/full moons and eclipses
directly from the ephemeris, so these need no chart construction at all.
"""

import logging
from typing import Any, Dict

from immanuel.const import chart as chart_const
from immanuel.const import names as names_const
from immanuel.tools import date as date_tools
from immanuel.tools import ephemeris, position, transit

from ..app import mcp
from ..utils.coordinates import parse_coordinate
from ..utils.datetimes import parse_datetime_value
from ..utils.errors import handle_chart_error

logger = logging.getLogger(__name__)

# The library returns eclipse type as a chart constant; ECLIPSE_TYPES names it.
_ECLIPSE_TYPE_NAMES = dict(names_const.ECLIPSE_TYPES)
_SIGN_NAMES = dict(names_const.SIGNS)

MAX_COUNT = 24


def _moon_placement(jd: float) -> Dict[str, Any]:
    """Sign and degree-within-sign of the Moon at a Julian date."""
    moon = ephemeris.get_planet(chart_const.MOON, jd)
    return {
        "sign": _SIGN_NAMES.get(position.sign(moon)),
        "degree": round(position.sign_longitude(moon), 2),
    }


def _event(kind: str, jd: float, lat: float, lon: float, timezone: str,
           eclipse_type: str = None) -> Dict[str, Any]:
    """Build one calendar entry from a Julian date."""
    entry = {
        "type": kind,
        "date_time_utc": date_tools.to_datetime(
            jd, lat=0.0, lon=0.0, time_zone="UTC").isoformat(),
        "date_time_local": date_tools.to_datetime(
            jd, lat=lat, lon=lon, time_zone=timezone).isoformat(),
        **_moon_placement(jd),
    }
    if eclipse_type is not None:
        entry["eclipse_type"] = eclipse_type
    return entry


@mcp.tool()
def get_lunations_and_eclipses(
    start_date_time: str,
    count: int = 6,
    include_eclipses: bool = True,
    latitude: str = None,
    longitude: str = None,
    timezone: str = None
) -> Dict[str, Any]:
    """
    List upcoming new moons, full moons and eclipses from a given moment.

    Lunations mark the monthly cycle of beginnings (new moon) and culminations
    (full moon); eclipses are the lunations that fall near the nodes and carry
    a longer arc of influence.

    Args:
        start_date_time: Date and time to search forward from, ISO format,
                         e.g. '2026-01-01 00:00:00'.
        count: How many of each event type to return (1-24). Six new and six
               full moons is roughly half a year.
        include_eclipses: Whether to include solar and lunar eclipses.
        latitude: Optional latitude for the local-time column, e.g. '51n30'.
                  Times are reported in UTC as well either way.
        longitude: Optional longitude for the local-time column, e.g. '0w07'.
        timezone: Optional IANA timezone for the local-time column, e.g.
                  'Europe/London'. Inferred from the coordinates if omitted.

    Returns:
        Dictionary with new_moons, full_moons and (when requested)
        solar_eclipses and lunar_eclipses, each a chronological list carrying
        the UTC and local moment plus the Moon's sign and degree.
    """
    try:
        if not 1 <= count <= MAX_COUNT:
            raise ValueError(f"count must be between 1 and {MAX_COUNT}, got {count}")

        lat = parse_coordinate(latitude, is_latitude=True) if latitude else 0.0
        lon = parse_coordinate(longitude, is_latitude=False) if longitude else 0.0
        local_zone = timezone if (timezone or latitude) else "UTC"

        start = parse_datetime_value(start_date_time)
        start_jd = date_tools.to_jd(start, lat=lat, lon=lon, time_zone=local_zone)
        logger.info(f"Listing {count} lunations from {start_date_time}")

        result: Dict[str, Any] = {
            "start_date_time": start.isoformat(),
            "count": count,
        }

        for key, search, label in (
            ("new_moons", transit.next_new_moon, "new_moon"),
            ("full_moons", transit.next_full_moon, "full_moon"),
        ):
            events = []
            jd = start_jd
            for _ in range(count):
                jd = search(jd)
                events.append(_event(label, jd, lat, lon, local_zone))
                jd += 1.0  # past the hit, so the next search cannot re-find it
            result[key] = events

        if include_eclipses:
            for key, search, label in (
                ("solar_eclipses", transit.next_solar_eclipse, "solar_eclipse"),
                ("lunar_eclipses", transit.next_lunar_eclipse, "lunar_eclipse"),
            ):
                events = []
                jd = start_jd
                for _ in range(count):
                    eclipse_type, jd = search(jd)
                    events.append(_event(
                        label, jd, lat, lon, local_zone,
                        eclipse_type=_ECLIPSE_TYPE_NAMES.get(eclipse_type)))
                    jd += 1.0
                result[key] = events

        result["status"] = "success"
        logger.info("Lunation calendar generated successfully")
        return result

    except Exception as e:
        logger.error(f"Error generating lunation calendar: {str(e)}")
        return handle_chart_error(e)

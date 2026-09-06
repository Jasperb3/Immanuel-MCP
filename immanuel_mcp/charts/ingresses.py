"""Planetary sign ingress calendar.

Built on immanuel 1.5.4's transit.next_sign_ingress(), which brackets the
crossing and solves it with brentq rather than stepping the ephemeris.
"""

import logging
from typing import Any, Dict, List

from immanuel.const import names as names_const
from immanuel.tools import date as date_tools
from immanuel.tools import ephemeris, position, transit

from ..app import mcp
from ..utils.datetimes import parse_datetime_value
from ..utils.errors import handle_chart_error
from ..lifecycle.returns import PLANET_CONSTANTS

logger = logging.getLogger(__name__)

_SIGN_NAMES = dict(names_const.SIGNS)

# The slow bodies, whose ingresses mark multi-year collective chapters and are
# what people actually ask about. Faster planets change sign constantly.
DEFAULT_PLANETS = ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"]

MAX_COUNT = 24

# Nudge past a found ingress so the next search cannot re-converge on it.
_STEP_PAST_JD = 0.5


def _next_sign(sign: int) -> int:
    """The sign after this one, wrapping Pisces to Aries."""
    return sign % 12 + 1


def _previous_sign(sign: int) -> int:
    """The sign before this one, wrapping Aries to Pisces."""
    return (sign - 2) % 12 + 1


def _next_ingress_jd(planet_index: int, jd: float) -> float:
    """
    Julian date of a planet's next sign change, in either direction.

    A retrograde planet re-enters the sign it just left, so the next ingress
    is whichever of the forward and backward crossings comes first. Searching
    only forward would silently skip every retrograde re-entry and report the
    sign changes out of order.
    """
    current = position.sign(ephemeris.get_planet(planet_index, jd))
    forward = transit.next_sign_ingress(planet_index, _next_sign(current), jd)
    backward = transit.next_sign_ingress(planet_index, _previous_sign(current), jd)
    return min(forward, backward)


@mcp.tool()
def get_sign_ingresses(
    start_date_time: str,
    planets: List[str] = None,
    count: int = 5,
    timezone: str = None
) -> Dict[str, Any]:
    """
    List the dates on which planets change zodiac sign, from a given moment.

    An ingress marks a shift in the tone of a planet's expression, and for the
    slow bodies it opens a chapter lasting years. Retrograde re-entries are
    included: a planet often crosses a sign boundary three times before it
    settles, and all three crossings are listed in date order.

    Args:
        start_date_time: Date and time to search forward from, ISO format,
                         e.g. '2026-01-01 00:00:00'.
        planets: Planet names to track, e.g. ['Saturn', 'Pluto']. Defaults to
                 Jupiter, Saturn, Uranus, Neptune, Pluto and Chiron.
        count: How many ingresses to return per planet (1-24).
        timezone: Optional IANA timezone for the local-time column, e.g.
                  'Europe/London'. Times are reported in UTC either way.

    Returns:
        Dictionary keyed by planet name, each a chronological list of
        ingresses carrying the sign entered, the sign left, and the moment.
    """
    try:
        if not 1 <= count <= MAX_COUNT:
            raise ValueError(f"count must be between 1 and {MAX_COUNT}, got {count}")

        requested = planets if planets else DEFAULT_PLANETS
        unknown = [p for p in requested if p not in PLANET_CONSTANTS]
        if unknown:
            raise ValueError(
                f"Unknown planet(s): {', '.join(unknown)}. "
                f"Valid values: {', '.join(sorted(PLANET_CONSTANTS))}")

        local_zone = timezone or "UTC"
        start = parse_datetime_value(start_date_time)
        start_jd = date_tools.to_jd(start, lat=0.0, lon=0.0, time_zone=local_zone)
        logger.info(f"Listing {count} ingresses for {', '.join(requested)}")

        ingresses: Dict[str, Any] = {}
        for planet_name in requested:
            planet_index = PLANET_CONSTANTS[planet_name]
            events = []
            jd = start_jd
            for _ in range(count):
                from_sign = position.sign(ephemeris.get_planet(planet_index, jd))
                jd = _next_ingress_jd(planet_index, jd)
                into_sign = position.sign(ephemeris.get_planet(planet_index, jd + _STEP_PAST_JD))
                events.append({
                    "planet": planet_name,
                    "from_sign": _SIGN_NAMES.get(from_sign),
                    "into_sign": _SIGN_NAMES.get(into_sign),
                    "retrograde_re_entry": into_sign == _previous_sign(from_sign),
                    "date_time_utc": date_tools.to_datetime(
                        jd, lat=0.0, lon=0.0, time_zone="UTC").isoformat(),
                    "date_time_local": date_tools.to_datetime(
                        jd, lat=0.0, lon=0.0, time_zone=local_zone).isoformat(),
                })
                jd += _STEP_PAST_JD
            ingresses[planet_name] = events

        logger.info("Ingress calendar generated successfully")
        return {
            "start_date_time": start.isoformat(),
            "count": count,
            "ingresses": ingresses,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error generating ingress calendar: {str(e)}")
        return handle_chart_error(e)

"""Planetary sign ingress calendar.

Deliberately does not use immanuel 1.5.4's transit.next_sign_ingress(), which
skips crossings near a station - see utils.search for why, and for the
station-safe scan used instead.
"""

import logging
from typing import Any, Dict, List

from immanuel.const import names as names_const
from immanuel.tools import date as date_tools
from immanuel.tools import ephemeris, position

from ..app import mcp
from ..utils.datetimes import parse_datetime_value
from ..utils.errors import handle_chart_error
from ..utils.search import find_state_changes
from ..constants import PLANET_CONSTANTS

logger = logging.getLogger(__name__)

_SIGN_NAMES = dict(names_const.SIGNS)

# The slow bodies, whose ingresses mark multi-year collective chapters and are
# what people actually ask about. Faster planets change sign constantly.
DEFAULT_PLANETS = ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"]

MAX_COUNT = 24

# Nudge past a found ingress so the next search cannot re-converge on it.
_STEP_PAST_JD = 0.5

# Search ceiling. Pluto, the slowest tracked body, spends at most ~30 years in
# a sign, so anything beyond this is a runaway rather than a real answer.
_MAX_SEARCH_DAYS = 40 * 365.25


def _next_sign(sign: int) -> int:
    """The sign after this one, wrapping Pisces to Aries."""
    return sign % 12 + 1


def _previous_sign(sign: int) -> int:
    """The sign before this one, wrapping Aries to Pisces."""
    return (sign - 2) % 12 + 1


def _next_ingress_jd(planet_index: int, jd: float) -> float:
    """
    Julian date of a planet's next sign change, in either direction.

    Searches for the next change of sign index rather than for entry into one
    named sign, so a retrograde re-entry into the sign just left is found the
    same way as an ordinary forward ingress - no direction needs guessing.

    Raises:
        ValueError: If no crossing is found within the search ceiling.
    """
    hits = find_state_changes(
        planet_index, jd, jd + _MAX_SEARCH_DAYS, position.sign, max_hits=1)
    if not hits:
        raise ValueError(
            f"No sign change found within {_MAX_SEARCH_DAYS / 365.25:.0f} years")
    return hits[0]


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

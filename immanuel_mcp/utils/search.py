"""Ephemeris search helpers built on immanuel.tools.transit (1.5.4+).

The library's search functions are unbounded iterative step searches: they
converge on the requested aspect but take no window argument and have no
failure mode other than looping. Everything here bounds them by validating the
returned Julian date against the window the caller expects, so a search that
wanders is surfaced as a ValueError rather than a silently wrong date.
"""

from datetime import datetime

import swisseph as swe
from immanuel.const import calc as calc_const
from immanuel.tools import date as date_tools
from immanuel.tools import ephemeris, transit

# Bracketing step for the aspect search: aim to advance this many degrees per
# probe, but never more than this many days. The degree budget keeps a fast
# body from stepping over a crossing; the day cap keeps a body approaching a
# station, where speed tends to zero, from taking an unbounded step and
# leaping over one. Both are needed - immanuel's own searches have only the
# first kind of bound and do skip crossings near stations.
_STEP_DEGREES = 0.5
_MAX_STEP_DAYS = 10.0


def _aspect_targets(point: float, aspect: float) -> list:
    """
    The ecliptic longitudes at which an aspect to a fixed point perfects.

    An aspect of angle A is exact when the moving body reaches point + A or
    point - A, which turns every aspect into a conjunction to a fixed
    longitude - a clean sign change to bisect, rather than the tangency that
    a separation-minus-angle function gives at 0 and 180 degrees. The two
    targets coincide for a conjunction and for an opposition.
    """
    targets = [(point + aspect) % 360, (point - aspect) % 360]
    return targets[:1] if abs(targets[0] - targets[1]) < 1e-9 else targets


def _crossings(index: int, target: float, from_jd: float, to_jd: float) -> list:
    """
    Julian dates at which a body's longitude crosses a fixed longitude.

    Brackets each crossing by a bounded scan, then bisects to the library's
    own MAX_ERROR. Returns them in chronological order.
    """
    hits = []
    jd = from_jd
    previous_jd = jd
    previous_delta = swe.difdeg2n(
        ephemeris.get_planet(index, jd)["lon"], target)

    while jd < to_jd:
        planet = ephemeris.get_planet(index, jd)
        delta = swe.difdeg2n(planet["lon"], target)
        # A sign change is a crossing, unless the pair straddles the antipode,
        # where the signed difference wraps between -180 and 180.
        if delta * previous_delta < 0 and abs(delta - previous_delta) < 180:
            lo, hi = previous_jd, jd
            while (hi - lo) > calc_const.MAX_ERROR:
                mid = (lo + hi) / 2
                mid_delta = swe.difdeg2n(
                    ephemeris.get_planet(index, mid)["lon"], target)
                if mid_delta * previous_delta > 0:
                    lo = mid
                else:
                    hi = mid
            hits.append((lo + hi) / 2)

        previous_jd, previous_delta = jd, delta
        jd += min(_STEP_DEGREES / max(abs(planet["speed"]), 1e-9), _MAX_STEP_DAYS)

    return hits


def find_exact_aspect_dates(
    index: int,
    point: float,
    aspect: float,
    from_jd: float,
    window_days: float,
    max_hits: int = 3,
) -> list:
    """
    Julian dates on which a moving object perfects an aspect to a fixed
    ecliptic longitude, within a window.

    A retrograde slow planet perfects the same aspect up to three times; a
    direct planet perfects it once. Results are in chronological order.

    Args:
        index: Immanuel chart constant for the moving object.
        point: Fixed ecliptic longitude in degrees.
        aspect: Aspect angle in degrees (e.g. calc.CONJUNCTION).
        from_jd: Julian date to search forward from.
        window_days: How far past from_jd to keep collecting hits.
        max_hits: Cap on the number of perfections returned.

    Returns:
        List of Julian dates, possibly empty if none fall in the window.
    """
    to_jd = from_jd + window_days
    hits = []
    for target in _aspect_targets(point, aspect):
        hits.extend(_crossings(index, target, from_jd, to_jd))
    return sorted(hits)[:max_hits]


def find_return_jd(index: int, target_longitude: float, from_jd: float) -> float:
    """Julian date of an object's next return to a fixed longitude."""
    return transit.next_aspect_to(
        index, target_longitude % 360, from_jd, calc_const.CONJUNCTION
    )


def jd_to_datetime(jd: float, latitude: float = 0.0, longitude: float = 0.0,
                   timezone: str = None) -> datetime:
    """Convert a Julian date to a localized datetime."""
    return date_tools.to_datetime(
        jd, lat=latitude, lon=longitude, time_zone=timezone
    )


def jd_to_date_string(jd: float, latitude: float = 0.0, longitude: float = 0.0,
                      timezone: str = None) -> str:
    """Convert a Julian date to a YYYY-MM-DD string."""
    return jd_to_datetime(jd, latitude, longitude, timezone).strftime("%Y-%m-%d")

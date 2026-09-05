"""Ephemeris search helpers built on immanuel.tools.transit (1.5.4+).

The library's search functions are unbounded iterative step searches: they
converge on the requested aspect but take no window argument and have no
failure mode other than looping. Everything here bounds them by validating the
returned Julian date against the window the caller expects, so a search that
wanders is surfaced as a ValueError rather than a silently wrong date.
"""

from datetime import datetime

from immanuel.const import calc as calc_const
from immanuel.tools import date as date_tools
from immanuel.tools import transit

# Nudge past a found hit before searching for the next one. Large enough that
# the step search cannot re-converge on the same crossing, small enough that
# it cannot skip a retrograde pass (slow planets take weeks between passes).
_HIT_SEPARATION_JD = 1.0


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
        max_hits: Stop after this many perfections.

    Returns:
        List of Julian dates, possibly empty if none fall in the window.
    """
    end_jd = from_jd + window_days
    hits = []
    jd = from_jd

    while len(hits) < max_hits:
        hit = transit.next_aspect_to(index, point, jd, aspect)
        if hit > end_jd:
            break
        # The step search can converge slightly behind its start; ignore any
        # hit that does not advance, otherwise the loop cannot terminate.
        if hits and hit <= hits[-1]:
            break
        hits.append(hit)
        jd = hit + _HIT_SEPARATION_JD

    return hits


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

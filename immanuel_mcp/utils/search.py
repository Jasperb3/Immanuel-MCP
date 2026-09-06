"""Station-safe ephemeris searches.

immanuel's own search functions bracket a crossing by stepping 1/|speed| days
at a time. As a body approaches a station its speed tends to zero, the step
grows without bound, and the search leaps clean over the crossing it was
looking for - transit.next_sign_ingress() asked for Venus's next Aries
ingress on 2025-03-28 answers 2026-03-06, skipping the real re-entry on
2025-04-30.

find_state_changes() is the shared fix, and the only scanner in the codebase:
it advances by a degree budget under a day cap, which a station cannot
inflate, then bisects the bracket. Callers supply a state function, so the
same machinery finds sign ingresses (state = which sign) and aspect
perfections (state = which side of a longitude).
"""

from datetime import datetime

import swisseph as swe
from immanuel.const import calc as calc_const
from immanuel.tools import date as date_tools
from immanuel.tools import ephemeris, transit

# Bracketing budget: aim to advance this many degrees per probe, but never
# more than this many days. The degree budget keeps a fast body from stepping
# over a crossing; the day cap keeps a body at a station from taking an
# unbounded step. Both are needed - a body slow enough for the cap to bind
# covers under half a degree across it.
#
# Like any sampling scheme this can still miss a pair of crossings that both
# fall inside one step, which needs a station within a quarter degree of the
# boundary being searched for. Tightening these numbers narrows that window
# at a linear cost in ephemeris calls; it cannot close it.
STEP_DEGREES = 0.5
MAX_STEP_DAYS = 10.0


def find_state_changes(
    index: int,
    from_jd: float,
    to_jd: float,
    state,
    max_hits: int = None,
) -> list:
    """
    Julian dates within a window at which some property of a moving body
    changes value.

    Args:
        index: Immanuel chart constant for the moving object.
        from_jd: Julian date to scan forward from.
        to_jd: Julian date to scan up to.
        state: Callable taking the ephemeris dict for the body and returning
               a comparable value. A change in that value is a crossing; the
               returned date is the first instant carrying the new value.
        max_hits: Stop once this many crossings are found.

    Returns:
        Chronological list of Julian dates, empty if the property never
        changes within the window.
    """
    hits = []
    jd = from_jd
    previous_jd = jd
    previous_state = state(ephemeris.get_planet(index, jd))

    while jd < to_jd:
        planet = ephemeris.get_planet(index, jd)
        current_state = state(planet)

        if current_state != previous_state:
            hits.append(
                _bisect_state_change(index, previous_jd, jd, previous_state, state))
            if max_hits is not None and len(hits) >= max_hits:
                return hits

        previous_jd, previous_state = jd, current_state
        jd += min(STEP_DEGREES / max(abs(planet["speed"]), 1e-9), MAX_STEP_DAYS)

    return hits


def _bisect_state_change(index: int, lo: float, hi: float, lo_state, state) -> float:
    """
    Narrow a bracketed state change to the moment it happens.

    lo still carries lo_state and hi does not; the returned Julian date is the
    first instant that does not, to within the library's own MAX_ERROR.
    """
    while (hi - lo) > calc_const.MAX_ERROR:
        mid = (lo + hi) / 2
        if state(ephemeris.get_planet(index, mid)) == lo_state:
            lo = mid
        else:
            hi = mid
    return hi


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

    The state is which side of the target the body sits on. That flips at the
    antipode as well as at the target, since the signed difference wraps
    between -180 and 180, so each candidate is checked for actually being at
    the target before it is kept.
    """
    def side(planet: dict) -> bool:
        return swe.difdeg2n(planet["lon"], target) >= 0

    return [
        jd for jd in find_state_changes(index, from_jd, to_jd, side)
        if abs(swe.difdeg2n(ephemeris.get_planet(index, jd)["lon"], target)) < 1.0
    ]


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

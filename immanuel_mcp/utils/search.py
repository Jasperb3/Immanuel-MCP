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
from immanuel.const import chart as chart_const
from immanuel.tools import date as date_tools
from immanuel.tools import sweph

# Bracketing budget: aim to advance this many degrees per probe, but never
# more than this many days. The degree budget keeps a fast body from stepping
# over a crossing; the day cap keeps a body at a station from taking an
# unbounded step. Both are needed - a body slow enough for the cap to bind
# covers under half a degree across it.
#
# Two crossings of one boundary inside a single step need the body to turn
# back between them, i.e. a station. Watching the side alone misses that
# pair (the side is the same at both ends), so find_state_changes also
# watches the sign of the speed, which is in every sample already; see
# _station_crossings.
STEP_DEGREES = 0.5
MAX_STEP_DAYS = 10.0

# Tighter day caps for bodies whose longitude oscillates faster than their
# mean motion suggests. The true node wobbles (~1.5 deg, half-month period),
# so near a return it crosses the same longitude several times, 1-3 days
# apart: 1990 London's crosses its natal node on 2027-09-22, 25 and 26. A
# 10-day step put two of those inside one step and reported one crossing,
# chosen by where the samples happened to fall. Six hours resolves crossings
# a day apart; the skip below keeps the cost to the degree or so around the
# target.
_MAX_STEP_DAYS_BY_BODY = {
    chart_const.TRUE_NORTH_NODE: 0.25,
    chart_const.TRUE_SOUTH_NODE: 0.25,
}

# Fixed steps for bodies that never station. The Moon moves 12-15 deg a
# day and never turns back, so two crossings of one longitude are ~27 days
# apart and a quarter-day step (3-4 deg) cannot hold two; the 0.5-deg
# budget would sample it six times as often for nothing.
_FIXED_STEP_DAYS = {
    chart_const.MOON: 0.25,
}

# Upper bounds on each body's geocentric |speed| in degrees/day: the maximum
# sampled daily over 1900-2100, padded 1.5x. A body this far from a target
# longitude cannot reach it sooner than distance / bound, so a crossing search
# may jump that far without being able to miss a crossing. Bodies not listed
# (Sun, Moon) are never skipped.
_MAX_SPEED_PADDING = 1.5
_MAX_SPEED = {
    index: speed * _MAX_SPEED_PADDING for index, speed in {
        chart_const.MERCURY: 2.2027, chart_const.VENUS: 1.2589,
        chart_const.MARS: 0.7914, chart_const.JUPITER: 0.2424,
        chart_const.SATURN: 0.1307, chart_const.URANUS: 0.0646,
        chart_const.NEPTUNE: 0.0405, chart_const.PLUTO: 0.0405,
        chart_const.CHIRON: 0.1460,
        chart_const.TRUE_NORTH_NODE: 0.2590, chart_const.TRUE_SOUTH_NODE: 0.2590,
    }.items()
}

# Distance kept from the target when skipping: inside it, the ordinary
# station-safe stepping takes over.
_SKIP_MARGIN_DEGREES = 1.0


def body_position(index: int, jd: float) -> dict:
    """Ecliptic longitude and speed of a planet, asteroid or lunar node.

    immanuel 1.7's sweph.longitude() serves every body whose position needs
    only a Julian date, nodes included, and skips the declination and the
    rest of the chart object that ephemeris.get() built: the same lon and
    speed at about a third of the cost per sample.
    """
    lon, speed = sweph.longitude(index, jd)
    return {"lon": lon, "speed": speed}


def find_state_changes(
    index: int,
    from_jd: float,
    to_jd: float,
    state,
    max_hits: int = None,
    safe_skip=None,
    may_hide_pair=None,
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
        safe_skip: Optional callable taking the ephemeris dict and returning
               a number of days the state provably cannot change in. The
               scanner advances by the larger of that and its usual step.
        may_hide_pair: Optional callable taking the ephemeris dicts at two
               consecutive samples and the days between them, returning
               False when no pair of state changes can hide between them.
               It only saves the station bisection; without it every
               station between two same-state samples is checked.

    Returns:
        Chronological list of Julian dates, empty if the property never
        changes within the window.
    """
    hits = []
    max_step = _MAX_STEP_DAYS_BY_BODY.get(index, MAX_STEP_DAYS)
    jd = from_jd
    previous_jd = jd
    previous_planet = body_position(index, jd)
    previous_state = state(previous_planet)
    previous_direct = previous_planet["speed"] >= 0

    while jd < to_jd:
        planet = body_position(index, jd)
        current_state = state(planet)
        direct = planet["speed"] >= 0

        if current_state != previous_state:
            found = [_bisect_state_change(index, previous_jd, jd, previous_state, state)]
        elif direct != previous_direct and (
                may_hide_pair is None
                or may_hide_pair(previous_planet, planet, jd - previous_jd)):
            found = _station_crossings(index, previous_jd, jd, previous_state,
                                       previous_direct, state)
        else:
            found = []
        for hit in found:
            hits.append(hit)
            if max_hits is not None and len(hits) >= max_hits:
                return hits

        previous_jd, previous_state, previous_direct = jd, current_state, direct
        previous_planet = planet
        step = _FIXED_STEP_DAYS.get(index) or min(
            STEP_DEGREES / max(abs(planet["speed"]), 1e-9), max_step)
        if safe_skip is not None:
            step = max(step, safe_skip(planet))
        jd += step

    return hits


def station_pair_filter(index: int, distance):
    """
    A may_hide_pair test for find_state_changes, given `distance`: the
    degrees from a sample (ephemeris dict) to the nearest state boundary.

    To cross a boundary and come back, a body travels at least both samples'
    distances to it, and its padded maximum speed bounds how far it can
    travel between them. None for a body with no bound (Sun, Moon), which
    never stations anyway.
    """
    bound = _MAX_SPEED.get(index)
    if bound is None:
        return None

    def may_hide_pair(before: dict, after: dict, days: float) -> bool:
        return distance(before) + distance(after) <= bound * days

    return may_hide_pair


def _station_crossings(index: int, lo: float, hi: float, lo_state, lo_direct: bool,
                       state) -> list:
    """
    The crossings hidden by a station between two samples with the same
    state: [] or a pair.

    Between the samples the body turns, so its longitude runs to an extreme
    at the station and back. On either side of the station the motion is
    one-way, so each half holds at most one crossing; with the same state at
    both ends, there are two (the station itself on the far side) or none.
    1984 San Diego's Neptune stations 17.7" past its square target on
    2025-12-10 and crosses it on 12-06 and 12-14, inside one 10-day step.
    """
    a, b = lo, hi
    while (b - a) > calc_const.MAX_ERROR:
        mid = (a + b) / 2
        if (body_position(index, mid)["speed"] >= 0) == lo_direct:
            a = mid
        else:
            b = mid
    station_state = state(body_position(index, b))
    if station_state == lo_state:
        return []
    return [_bisect_state_change(index, lo, b, lo_state, state),
            _bisect_state_change(index, b, hi, station_state, state)]


def _bisect_state_change(index: int, lo: float, hi: float, lo_state, state) -> float:
    """
    Narrow a bracketed state change to the moment it happens.

    lo still carries lo_state and hi does not; the returned Julian date is the
    first instant that does not, to within the library's own MAX_ERROR.
    """
    while (hi - lo) > calc_const.MAX_ERROR:
        mid = (lo + hi) / 2
        if state(body_position(index, mid)) == lo_state:
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


def _crossings(index: int, target: float, from_jd: float, to_jd: float,
               skip: bool = True) -> list:
    """
    Julian dates at which a body's longitude crosses a fixed longitude.

    The state is which side of the target the body sits on. That flips at the
    antipode as well as at the target, since the signed difference wraps
    between -180 and 180, so each candidate is checked for actually being at
    the target before it is kept.

    With `skip`, a body far from the target jumps ahead by the time it would
    need at its maximum speed to come within _SKIP_MARGIN_DEGREES of it.
    That cannot pass a target crossing; it can pass an antipode flip, which is
    then bisected and discarded like any other. It cut a 20-year lifecycle
    search for a slow planet from ~900 ephemeris samples to a few dozen.

    Nor can it hide a grazing station: throughout a skip the body stays more
    than _SKIP_MARGIN_DEGREES from the target, and inside the margin the
    skip is zero, so a station near the target always falls in an ordinary
    step, where find_state_changes checks it.

    A station between two samples on the same side is only bisected when a
    pair of crossings could hide there: crossing over and back means
    travelling at least the two samples' distances from the target combined,
    which the maximum speed bounds. Without that test the stations a skip
    jumps over, degrees from the target, cost ~200 bisections per lifecycle
    chart.
    """
    def side(planet: dict) -> bool:
        return swe.difdeg2n(planet["lon"], target) >= 0

    def distance(planet: dict) -> float:
        return abs(swe.difdeg2n(planet["lon"], target))

    max_speed = _MAX_SPEED.get(index) if skip else None

    def safe_skip(planet: dict) -> float:
        return max(distance(planet) - _SKIP_MARGIN_DEGREES, 0.0) / max_speed

    return [
        jd for jd in find_state_changes(
            index, from_jd, to_jd, side,
            safe_skip=safe_skip if max_speed else None,
            may_hide_pair=station_pair_filter(index, distance))
        if abs(swe.difdeg2n(body_position(index, jd)["lon"], target)) < 1.0
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


# Consecutive perfections of the same aspect closer together than this belong
# to one pass sequence (a retrograde planet perfects up to three times, months
# apart). The next sequence of the same aspect is always far more than a year
# later, so splitting on the gap never merges, say, a waxing and a waning
# square.
PASS_GAP_DAYS = 365.25

# A cluster search looks this far either side of the reference: the longest
# pass sequences (a slow planet's square) span about two years.
CLUSTER_HALF_WINDOW_DAYS = 4 * 365.25
_CLUSTER_MAX_HITS = 64


def group_passes(jds: list, gap_days: float = PASS_GAP_DAYS) -> list:
    """Split sorted perfection dates into pass sequences, starting a new
    sequence wherever the gap between consecutive hits exceeds gap_days."""
    groups = []
    for jd in sorted(jds):
        if groups and jd - groups[-1][-1] <= gap_days:
            groups[-1].append(jd)
        else:
            groups.append([jd])
    return groups


def find_pass_cluster(index: int, point: float, aspect: float, reference_jd: float,
                      half_window_days: float = CLUSTER_HALF_WINDOW_DAYS) -> list:
    """
    The whole pass sequence of `aspect` to `point` that the reference date
    belongs to: the one whose span (first to last pass) contains it, else the
    one nearest it (in orb before the first pass, or after the last). [] if
    the window holds no perfection.

    The window is fixed, not sized from the body's current speed, and
    uncapped in practice, so a five-pass Pluto square comes back whole
    whichever of its passes the query is near.
    """
    hits = find_exact_aspect_dates(
        index, point, aspect, reference_jd - half_window_days, 2 * half_window_days,
        max_hits=_CLUSTER_MAX_HITS)
    clusters = group_passes(hits)
    if not clusters:
        return []

    def distance(cluster):
        return max(cluster[0] - reference_jd, reference_jd - cluster[-1], 0.0)

    return min(clusters, key=distance)


# find_return_jd: the first scan covers this many days and doubles until a
# return turns up, up to the cap (~82 years, beyond any tracked body's period).
_RETURN_FIRST_WINDOW_DAYS = 30.0
_RETURN_MAX_WINDOW_DAYS = 30000.0
# A return this close to from_jd counts as at from_jd: twice the bisection's
# own precision, so a search started on a return it found finds it again.
RETURN_TIE_DAYS = 2 * calc_const.MAX_ERROR
# Each scan starts this far before from_jd, so a return exactly at from_jd
# has a sample before it to bracket against.
_RETURN_LEAD_DAYS = 1e-4


def find_return_jd(index: int, target_longitude: float, from_jd: float) -> float:
    """
    Julian date of an object's first return to a fixed longitude at or after
    from_jd (a return within RETURN_TIE_DAYS of from_jd counts as at it).

    This used immanuel's transit.next_aspect_to, whose _fixed_aspect_search
    steps a whole day on the unsigned distance while it is at least the
    day's speed. A Moon that accelerates during the day overshoots the
    target, the distance grows, and the loop runs on to the next cycle: 6 of
    528 month searches skipped a return. This is the station-safe signed
    scan (_crossings) instead.

    Each attempt is one continuous scan from just before from_jd, doubling
    its window until a return turns up, so there are no seams inside a scan
    for a return to fall between, and a given from_jd always gives the same
    answer.

    Raises:
        ValueError: if no return turns up within _RETURN_MAX_WINDOW_DAYS.
    """
    target = target_longitude % 360
    window = _RETURN_FIRST_WINDOW_DAYS
    while window <= _RETURN_MAX_WINDOW_DAYS:
        hits = [jd for jd in _crossings(index, target, from_jd - _RETURN_LEAD_DAYS,
                                        from_jd + window)
                if jd >= from_jd - RETURN_TIE_DAYS]
        if hits:
            return _interpolate_crossing(index, target, hits[0])
        window *= 2
    raise ValueError(
        f"No return of object {index} to {target:.4f} deg within "
        f"{_RETURN_MAX_WINDOW_DAYS:.0f} days of JD {from_jd}")


def _interpolate_crossing(index: int, target: float, jd: float) -> float:
    """
    Refine a bisected crossing. Bisection returns the first sampled instant
    past the crossing, up to MAX_ERROR (0.09 s) late, which moves a return
    chart's Ascendant by about 1 arcsec. Over that interval the motion is
    linear, so interpolating across it puts the crossing within milliseconds.
    """
    lo = jd - calc_const.MAX_ERROR
    before = swe.difdeg2n(body_position(index, lo)["lon"], target)
    after = swe.difdeg2n(body_position(index, jd)["lon"], target)
    if after == before:
        return jd
    return lo + calc_const.MAX_ERROR * (-before) / (after - before)


def crossed_by(index: int, target_longitude: float, jd: float) -> bool:
    """
    Whether the body sits on the far side of the target at jd, i.e. a
    crossing just before jd has happened. Evaluated at jd itself, so two
    searches that share a boundary JD agree on which side of it a crossing
    within the search precision falls.
    """
    return swe.difdeg2n(body_position(index, jd)["lon"], target_longitude % 360) >= 0


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

"""Direction and natal house of a transit.

immanuel's `movement` on a cross-chart aspect is unreliable for transits: it
takes whichever object is faster as "active" (a natal Moon outruns transiting
Neptune) and calls any retrograde active object applicative. In a transit the
natal point is fixed, so only the transiting object's motion matters: the
aspect is applying when that motion is closing the orb.
"""

from typing import Any, Dict, List, Optional

# A step small enough to stay on one side of exact for any orb worth reporting.
_STEP_DEGREES = 1e-4


def _orb(transit_longitude: float, natal_longitude: float, angle: float) -> float:
    separation = abs((transit_longitude - natal_longitude + 180.0) % 360.0 - 180.0)
    return abs(separation - angle)


def transit_applying(transit_longitude: float, transit_speed: float,
                     natal_longitude: float, angle: float) -> bool:
    """True when the transiting object's present motion is closing the orb of
    its aspect (of `angle` degrees) to a fixed natal point. An object exactly
    on the aspect, or one standing still, is not applying."""
    if not transit_speed:
        return False
    step = _STEP_DEGREES if transit_speed > 0 else -_STEP_DEGREES
    now = _orb(transit_longitude, natal_longitude, angle)
    return _orb(transit_longitude + step, natal_longitude, angle) < now


def natal_house_of(longitude: float, cusps: List[float]) -> Optional[int]:
    """Number (1-12) of the house whose cusp-to-next-cusp arc holds
    `longitude`, given the twelve cusp longitudes in house order."""
    if len(cusps) != 12:
        return None
    for i, cusp in enumerate(cusps):
        span = (cusps[(i + 1) % 12] - cusp) % 360.0
        if (longitude - cusp) % 360.0 < span:
            return i + 1
    return None


def _by_name(chart) -> Dict[str, Any]:
    return {obj.name: obj for obj in chart.objects.values()}


def annotate_transit_aspects(aspects: List[Dict[str, Any]], transit_chart, natal_chart) -> None:
    """Add `applying` to each transit-to-natal aspect dict that names its
    `transiting_object` and `natal_object` and carries its angle (`angle` in
    compact output, `aspect` in full output)."""
    transiting, natal = _by_name(transit_chart), _by_name(natal_chart)
    for aspect in aspects:
        if not isinstance(aspect, dict):
            continue
        t = transiting.get(aspect.get('transiting_object'))
        n = natal.get(aspect.get('natal_object'))
        angle = aspect.get('angle', aspect.get('aspect'))
        if t is None or n is None or angle is None:
            continue
        aspect['applying'] = transit_applying(t.longitude.raw, t.speed, n.longitude.raw, float(angle))


def natal_cusps(natal_chart) -> Optional[List[float]]:
    """The natal chart's twelve cusp longitudes in house order, or None for
    an untimed chart."""
    houses = getattr(natal_chart, 'houses', None)
    if not houses:
        return None
    ordered = sorted(houses.values(), key=lambda h: h.number)
    return [h.longitude.raw for h in ordered] if len(ordered) == 12 else None


def natal_houses_by_name(transit_chart, natal_chart) -> Dict[str, Optional[int]]:
    """Natal house of each transiting object, keyed by object name; every
    value is None when the natal chart has no houses."""
    cusps = natal_cusps(natal_chart)
    return {
        obj.name: natal_house_of(obj.longitude.raw, cusps) if cusps else None
        for obj in transit_chart.objects.values()
    }

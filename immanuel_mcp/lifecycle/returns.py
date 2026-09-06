"""
Planetary Return Calculations

This module handles detection of planetary returns - when a transiting planet
returns to its natal position. Supports all major planetary cycles including
Saturn Returns, Jupiter Returns, and outer planet returns.

Key concepts:
- Return: When transit planet is within orb of natal position
- Orb: Angular distance between natal and transit positions
- Significance: Importance level based on planet and cycle number
- Status: Whether return is exact, tight, moderate, or loose
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from immanuel.const import calc as calc_const
from immanuel.const import chart as chart_const
from immanuel.tools import date as date_tools

from ..constants import PLANET_CONSTANTS
from ..utils.search import find_exact_aspect_dates
from .constants import (
    ORBITAL_PERIODS,
    RETURN_SIGNIFICANCE,
    RETURN_KEYWORDS,
    RETURN_ORB_TOLERANCE,
    TRACKED_RETURN_PLANETS
)

logger = logging.getLogger(__name__)


def calculate_signed_orb(natal_pos: float, transit_pos: float) -> float:
    """
    Calculate the signed orb between natal and transit positions.

    Handles 360° wrap-around (e.g., 359° to 1° is 2° orb, not 358°).
    Positive orb means transit is ahead of natal position.
    Negative orb means transit is behind natal position.

    Args:
        natal_pos: Natal position in degrees (0-360)
        transit_pos: Transit position in degrees (0-360)

    Returns:
        Signed orb in degrees (-180 to +180)

    Examples:
        >>> calculate_signed_orb(10.0, 12.0)
        2.0
        >>> calculate_signed_orb(359.0, 1.0)
        2.0
        >>> calculate_signed_orb(12.0, 10.0)
        -2.0
    """
    # Calculate raw difference
    diff = transit_pos - natal_pos

    # Normalize to -180 to +180 range
    if diff > 180:
        diff -= 360
    elif diff < -180:
        diff += 360

    return diff


def determine_movement(signed_orb: float, orb_rate: float, exact_threshold: float = 0.5) -> str:
    """
    Determine whether an event is applying, exact, or separating.

    Args:
        signed_orb: Signed deviation from exactness in degrees. The event is
            exact when this reaches 0.
        orb_rate: Rate of change of signed_orb in degrees per day (for a
            return this is simply the transiting planet's speed; for an
            aspect it must incorporate the direction of the separation).
        exact_threshold: Within this many degrees the event counts as exact.

    Returns:
        "exact", "applying", "separating", or "stationary"
    """
    if abs(signed_orb) <= exact_threshold:
        return "exact"
    if orb_rate == 0:
        return "stationary"
    # The absolute orb shrinks when the orb and its rate have opposite signs.
    return "applying" if signed_orb * orb_rate < 0 else "separating"


def find_event_exact_dates(
    planet_index: int,
    natal_longitude: float,
    aspect: float,
    reference: datetime,
    tolerance: float,
    speed: float,
) -> list:
    """
    Ephemeris-searched dates on which a lifecycle event perfects.

    Replaces the linear speed estimate for anything with a real ephemeris.
    A retrograde slow planet perfects the same aspect up to three times, so
    this returns every perfection in the window the event is within orb for.

    The reference datetime is treated as UTC for the search's starting Julian
    date. That is only a starting point - the search converges on the true
    perfection regardless - so the sub-day error from an unknown zone does not
    affect the result.

    Args:
        planet_index: Immanuel chart constant for the transiting planet
        natal_longitude: The natal point's ecliptic longitude in degrees
        aspect: Aspect angle in degrees (0 for a return)
        reference: Datetime the orb was measured at
        tolerance: Orb tolerance in degrees for this event
        speed: The transiting planet's daily motion in degrees

    Returns:
        Chronological list of datetimes, empty if the search finds none.
    """
    daily = max(abs(speed), 1e-4)
    # Cover the whole in-orb span, tripled so retrograde loops that carry the
    # planet back out of orb and in again are not cut off. Bounded so a
    # near-stationary body cannot request a centuries-wide search.
    half_window = min(max(tolerance / daily * 3, 30.0), 730.0)

    reference_jd = date_tools.to_jd(reference, lat=0.0, lon=0.0, time_zone="UTC")
    hits = find_exact_aspect_dates(
        planet_index,
        natal_longitude,
        aspect,
        reference_jd - half_window,
        half_window * 2,
    )
    return [
        date_tools.to_datetime(jd, lat=0.0, lon=0.0, time_zone="UTC").replace(tzinfo=None)
        for jd in hits
    ]


def closest_exact_date(exact_dates: list, reference: datetime):
    """The perfection nearest the reference datetime, or None if there are none."""
    if not exact_dates:
        return None
    return min(exact_dates, key=lambda dt: abs((dt - reference).total_seconds()))


def estimate_exact_datetime(signed_orb: float, orb_rate: float, reference: datetime):
    """
    Linear estimate of when an event perfects, from the current rate.

    Retrograde loops mean slow outer-planet events can perfect several times
    over one to two years; this single-date estimate cannot represent that
    and is flagged as an estimate wherever it is surfaced.

    Args:
        signed_orb: Signed deviation from exactness in degrees
        orb_rate: Rate of change of signed_orb in degrees per day
        reference: Datetime the orb was measured at

    Returns:
        Estimated datetime of exactness, or None if the body is effectively
        stationary or the estimate lands implausibly far away (> ~2 years,
        where a linear projection through retrograde loops is meaningless).
    """
    if abs(orb_rate) < 1e-4:
        return None
    days = -signed_orb / orb_rate
    if abs(days) > 730:
        return None
    return reference + timedelta(days=days)


def determine_orb_status(orb: float, tolerance: float) -> str:
    """
    Categorize orb tightness.

    Args:
        orb: Absolute orb value in degrees
        tolerance: Maximum orb tolerance for this planet

    Returns:
        Status: "exact", "tight", "moderate", "loose", or "inactive"

    Categories:
        - exact: Within 0.5° (regardless of tolerance)
        - tight: Within 33% of tolerance
        - moderate: Within 66% of tolerance
        - loose: Within 100% of tolerance
        - inactive: Beyond tolerance
    """
    abs_orb = abs(orb)

    if abs_orb <= 0.5:
        return "exact"
    elif abs_orb <= (tolerance * 0.33):
        return "tight"
    elif abs_orb <= (tolerance * 0.66):
        return "moderate"
    elif abs_orb <= tolerance:
        return "loose"
    else:
        return "inactive"


def get_return_significance(planet_name: str, return_number: int) -> str:
    """
    Get significance level for a planetary return.

    Uses context-aware significance from RETURN_SIGNIFICANCE constant.
    Some returns have higher significance at specific cycle numbers
    (e.g., 1st Saturn Return is CRITICAL).

    Args:
        planet_name: Name of planet (e.g., "Saturn", "Jupiter")
        return_number: Which return cycle (1, 2, 3, ...)

    Returns:
        Significance level: "CRITICAL", "HIGH", "MODERATE", or "LOW"

    Examples:
        >>> get_return_significance("Saturn", 1)
        "CRITICAL"
        >>> get_return_significance("Jupiter", 2)
        "HIGH"
    """
    if planet_name not in RETURN_SIGNIFICANCE:
        return "MODERATE"

    planet_sig = RETURN_SIGNIFICANCE[planet_name]

    # Check for specific cycle significance
    if return_number in planet_sig:
        return planet_sig[return_number]

    # Fall back to default
    return planet_sig.get("default", "MODERATE")


def calculate_planetary_return(
    planet_name: str,
    natal_chart,
    transit_chart,
    birth_datetime: datetime,
    transit_datetime: datetime
) -> Optional[Dict[str, Any]]:
    """
    Calculate if a planetary return is active and its details.

    A return occurs when the transiting planet returns to the same position
    as in the natal chart (within orb tolerance).

    Args:
        planet_name: Name of planet (must be in PLANET_CONSTANTS)
        natal_chart: Immanuel natal chart object
        transit_chart: Immanuel transit chart object
        birth_datetime: Birth datetime
        transit_datetime: Transit datetime

    Returns:
        Return data dict if active, None if not within orb:
        {
            "planet": "Saturn",
            "type": "saturn_return",
            "cycle_number": 1,
            "natal_position": 125.43,
            "transit_position": 126.87,
            "orb": 1.44,
            "orb_status": "tight",
            "natal_sign": "Leo",
            "transit_sign": "Leo",
            "significance": "CRITICAL",
            "keywords": ["maturity", "responsibility", ...],
            "age": 29.5,
            "status": "active"
        }

    Raises:
        ValueError: If planet name is not recognized
        AttributeError: If chart doesn't contain planet
    """
    # Validate planet name
    if planet_name not in PLANET_CONSTANTS:
        raise ValueError(f"Unknown planet: {planet_name}")

    planet_const = PLANET_CONSTANTS[planet_name]

    # Get planet objects from charts
    try:
        natal_planet = natal_chart.objects.get(planet_const)
        transit_planet = transit_chart.objects.get(planet_const)
    except (AttributeError, KeyError) as e:
        logger.warning(f"Planet {planet_name} not found in chart: {e}")
        return None

    # Extract positions (longitude is an Angle object with .raw attribute)
    natal_pos = natal_planet.longitude.raw
    transit_pos = transit_planet.longitude.raw

    # Calculate orb
    orb = calculate_signed_orb(natal_pos, transit_pos)

    # Check if within tolerance
    tolerance = RETURN_ORB_TOLERANCE.get(planet_name, 2.0)
    orb_status = determine_orb_status(orb, tolerance)

    if orb_status == "inactive":
        return None  # Not within orb

    # Calculate age and cycle number
    age = (transit_datetime - birth_datetime).days / 365.25
    orbital_period = ORBITAL_PERIODS.get(planet_name, 1.0)
    cycle_number = max(1, round(age / orbital_period))

    # Get significance
    significance = get_return_significance(planet_name, cycle_number)

    # Applying/separating from the transiting planet's current speed; the
    # perfection dates come from an ephemeris search, so a retrograde return
    # reports all of its passes rather than one linear guess.
    speed = getattr(transit_planet, 'speed', None)
    movement = None
    exact_dates = []
    exact_datetime = None
    if isinstance(speed, (int, float)):
        movement = determine_movement(orb, speed)
        try:
            exact_dates = find_event_exact_dates(
                planet_const, natal_pos, calc_const.CONJUNCTION,
                transit_datetime, tolerance, speed)
        except Exception as e:
            logger.warning(f"Exact-date search failed for {planet_name} return: {e}")
        exact_datetime = closest_exact_date(exact_dates, transit_datetime)

    # Build return data
    return_data = {
        "planet": planet_name,
        "type": f"{planet_name.lower().replace(' ', '_')}_return",
        "cycle_number": cycle_number,
        "natal_position": round(natal_pos, 2),
        "transit_position": round(transit_pos, 2),
        "orb": round(orb, 2),
        "orb_status": orb_status,
        "movement": movement,
        "exact_date": exact_datetime.strftime("%Y-%m-%d") if exact_datetime else None,
        "exact_dates": [dt.strftime("%Y-%m-%d") for dt in exact_dates],
        "natal_sign": natal_planet.sign.name,
        "transit_sign": transit_planet.sign.name,
        "significance": significance,
        "keywords": RETURN_KEYWORDS.get(planet_name, []),
        "age": round(age, 1),
        "status": "active"
    }

    return return_data


def detect_all_returns(
    natal_chart,
    transit_chart,
    birth_datetime: datetime,
    transit_datetime: datetime,
    planets: Optional[list] = None
) -> list[Dict[str, Any]]:
    """
    Detect all active planetary returns for a given transit time.

    Args:
        natal_chart: Immanuel natal chart object
        transit_chart: Immanuel transit chart object
        birth_datetime: Birth datetime
        transit_datetime: Transit datetime
        planets: List of planet names to check (defaults to TRACKED_RETURN_PLANETS)

    Returns:
        List of active return dicts, sorted by significance then orb

    Examples:
        >>> returns = detect_all_returns(natal, transit, birth_dt, transit_dt)
        >>> len(returns)
        1
        >>> returns[0]["planet"]
        "Saturn"
    """
    if planets is None:
        planets = TRACKED_RETURN_PLANETS

    active_returns = []

    for planet_name in planets:
        try:
            return_data = calculate_planetary_return(
                planet_name,
                natal_chart,
                transit_chart,
                birth_datetime,
                transit_datetime
            )
            if return_data:
                active_returns.append(return_data)
        except Exception as e:
            logger.warning(f"Error calculating {planet_name} return: {e}")
            continue

    # Sort by significance (CRITICAL > HIGH > MODERATE > LOW) then by orb
    significance_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    active_returns.sort(
        key=lambda r: (
            significance_order.get(r["significance"], 4),
            abs(r["orb"])
        )
    )

    return active_returns

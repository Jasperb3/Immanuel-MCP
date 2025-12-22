"""
Lifecycle Events Master Detection

This module provides the main entry point for lifecycle events detection.
It orchestrates all subsystems (returns, transits, timeline) and assembles
the complete lifecycle events response.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from .returns import detect_all_returns, PLANET_CONSTANTS, calculate_signed_orb, determine_orb_status
from .transits import detect_all_major_transits, calculate_aspect_orb, TRANSIT_ORB_TOLERANCE
from .timeline import build_future_timeline, get_lifecycle_stage
from .constants import (
    ORBITAL_PERIODS,
    RETURN_ORB_TOLERANCE,
    RETURN_INTERPRETATIONS
)

logger = logging.getLogger(__name__)


def _enrich_future_events_with_orbs(
    future_events: list,
    natal_chart,
    transit_chart
) -> None:
    """
    Calculate current angular separation for future timeline events.

    This enriches predicted events with current separation information to show
    how close/far the person is from the predicted event. The "current_separation"
    represents degrees of angular distance (0-180°) between current position and
    the position at which the event will be exact.

    Args:
        future_events: List of future event predictions (modified in place)
        natal_chart: Immanuel natal chart object
        transit_chart: Immanuel transit chart object
    """
    for event in future_events:
        event_type = event.get("event_type")

        try:
            if event_type == "return":
                # Calculate orb for planetary return
                planet_name = event.get("planet")
                if planet_name not in PLANET_CONSTANTS:
                    continue

                planet_const = PLANET_CONSTANTS[planet_name]
                natal_planet = natal_chart.objects.get(planet_const)
                transit_planet = transit_chart.objects.get(planet_const)

                # Skip if planet not accessible (e.g., nodes may not be in objects collection)
                if natal_planet is None or transit_planet is None:
                    logger.debug(f"Skipping orb calculation for {planet_name} (not accessible in chart objects)")
                    continue

                natal_pos = natal_planet.longitude.raw
                transit_pos = transit_planet.longitude.raw

                orb = calculate_signed_orb(natal_pos, transit_pos)
                tolerance = RETURN_ORB_TOLERANCE.get(planet_name, 2.0)
                orb_status = determine_orb_status(orb, tolerance)

                event["current_orb"] = round(abs(orb), 2)
                event["orb_status"] = "applicative" if abs(orb) > 0.5 else "exact"

            elif event_type == "major_transit":
                # Calculate orb for major life transit
                natal_object_name = event.get("natal_object")
                transit_object_name = event.get("transit_object")
                aspect_type = event.get("aspect_type")

                if not all([natal_object_name, transit_object_name, aspect_type]):
                    continue

                if natal_object_name not in PLANET_CONSTANTS:
                    continue
                if transit_object_name not in PLANET_CONSTANTS:
                    continue

                natal_planet_const = PLANET_CONSTANTS[natal_object_name]
                transit_planet_const = PLANET_CONSTANTS[transit_object_name]

                natal_planet = natal_chart.objects.get(natal_planet_const)
                transit_planet = transit_chart.objects.get(transit_planet_const)

                natal_pos = natal_planet.longitude.raw
                transit_pos = transit_planet.longitude.raw

                orb = calculate_aspect_orb(natal_pos, transit_pos, aspect_type)

                if orb is not None:
                    event["current_orb"] = round(abs(orb), 2)
                    event["orb_status"] = "applicative" if abs(orb) > 0.5 else "exact"

        except Exception as e:
            logger.warning(
                f"Could not calculate orb for future event {event.get('name', event.get('planet', 'unknown'))}: {e}",
                exc_info=True
            )
            continue


def detect_lifecycle_events(
    natal_chart,
    transit_chart,
    birth_datetime: datetime,
    transit_datetime: datetime,
    include_future: bool = True,
    future_years: int = 20,
    max_future_events: int = 10
) -> Dict[str, Any]:
    """
    Detect all lifecycle events for a given transit time.

    This is the main entry point for the lifecycle events system. It combines:
    - Current active planetary returns (Saturn Return, Jupiter Return, etc.)
    - Current active major life transits (Uranus Opposition, Neptune Square, etc.)
    - Future timeline predictions (upcoming events)
    - Current lifecycle stage (where you are in your life journey)

    Args:
        natal_chart: Immanuel natal chart object
        transit_chart: Immanuel transit chart object
        birth_datetime: Birth datetime
        transit_datetime: Transit datetime
        include_future: Whether to include future timeline (default: True)
        future_years: Years ahead to predict (default: 20)
        max_future_events: Max future events to return (default: 10)

    Returns:
        Complete lifecycle events response:
        {
            "current_events": [
                {
                    "event_type": "return",
                    "planet": "Saturn",
                    "type": "saturn_return",
                    "cycle_number": 1,
                    "orb": 1.2,
                    "orb_status": "tight",
                    "significance": "CRITICAL",
                    "keywords": [...],
                    "age": 29.5,
                    "status": "active"
                }
            ],
            "past_events": [
                {
                    "event_type": "major_transit",
                    "name": "Chiron Opposition",
                    "completed_at_age": 25.3,
                    "years_ago": 4.2
                }
            ],
            "future_timeline": [
                {
                    "event_type": "return",
                    "planet": "Saturn",
                    "predicted_age": 58.5,
                    "predicted_date": "2042-06-15",
                    "years_until": 29.0,
                    "significance": "CRITICAL"
                }
            ],
            "lifecycle_summary": {
                "current_age": 29.5,
                "current_stage": {
                    "stage_name": "Saturn Return",
                    "description": "Karmic maturation",
                    "age_range": [29, 31],
                    "themes": ["responsibility", "maturity", "commitment"]
                },
                "active_event_count": 1,
                "highest_significance": "CRITICAL"
            }
        }

    Examples:
        >>> events = detect_lifecycle_events(natal, transit, birth_dt, transit_dt)
        >>> events["current_events"][0]["planet"]
        "Saturn"
        >>> events["lifecycle_summary"]["current_stage"]["stage_name"]
        "Saturn Return"
    """
    # Calculate current age
    age = (transit_datetime - birth_datetime).days / 365.25

    # Detect current active returns
    logger.info(f"Detecting planetary returns for age {age:.1f}")
    active_returns = detect_all_returns(
        natal_chart,
        transit_chart,
        birth_datetime,
        transit_datetime
    )

    # Detect current active major transits
    logger.info(f"Detecting major life transits for age {age:.1f}")
    active_major_transits = detect_all_major_transits(
        natal_chart,
        transit_chart,
        birth_datetime,
        transit_datetime
    )

    # Combine all current events
    current_events = []

    # Add returns
    for return_data in active_returns:
        return_data["event_type"] = "return"
        current_events.append(return_data)

    # Add major transits
    for transit_data in active_major_transits:
        transit_data["event_type"] = "major_transit"
        current_events.append(transit_data)

    # Sort combined events by significance then orb
    significance_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    current_events.sort(
        key=lambda e: (
            significance_order.get(e["significance"], 4),
            abs(e.get("orb", 999))  # Use high value if orb not present
        )
    )

    # Build past events summary
    past_events = build_past_events_summary(age)

    # Build future timeline (if requested)
    future_timeline = []
    if include_future:
        logger.info(f"Building future timeline ({future_years} years ahead)")
        future_timeline = build_future_timeline(
            age,
            birth_datetime,
            years_ahead=future_years,
            max_events=max_future_events
        )

        # Calculate current orbs for future events to show how close they are
        _enrich_future_events_with_orbs(
            future_timeline,
            natal_chart,
            transit_chart
        )

    # Get current lifecycle stage
    lifecycle_stage = get_lifecycle_stage(age)

    # Determine highest significance level of current events
    highest_significance = "NONE"
    if current_events:
        highest_significance = current_events[0]["significance"]

    # Build lifecycle summary
    lifecycle_summary = {
        "current_age": round(age, 1),
        "current_stage": lifecycle_stage,
        "active_event_count": len(current_events),
        "highest_significance": highest_significance
    }

    lifecycle_summary.update(
        _build_summary_enhancements(current_events, future_timeline, transit_datetime)
    )

    # Assemble complete response
    response = {
        "current_events": current_events,
        "past_events": past_events,
        "future_timeline": future_timeline,
        "lifecycle_summary": lifecycle_summary
    }

    logger.info(
        f"Lifecycle detection complete: {len(current_events)} current, "
        f"{len(future_timeline)} future events"
    )

    return response


def build_past_events_summary(current_age: float) -> list[Dict[str, Any]]:
    """
    Build a summary of significant lifecycle events that have already occurred.

    This provides context for what major transits the person has already
    experienced in their life journey.

    Args:
        current_age: Current age in years

    Returns:
        List of past event summaries:
        [
            {
                "event_type": "major_transit",
                "name": "Chiron Opposition",
                "typical_age": 25,
                "completed_at_age": 25.3,
                "years_ago": 4.2
            },
            ...
        ]
    """
    past_events = []

    # Major milestones with typical ages
    milestones = [
        ("First Jupiter Return", "return", 12),
        ("First Nodal Return", "return", 18),
        ("Second Jupiter Return", "return", 24),
        ("Chiron Opposition", "major_transit", 25),
        ("First Saturn Return", "return", 29),
        ("Pluto Square", "major_transit", 36),
        ("Neptune Square", "major_transit", 39),
        ("Uranus Opposition", "major_transit", 41),
        ("Chiron Return", "return", 50),
        ("Second Saturn Return", "return", 58),
    ]

    for event_name, event_type, typical_age in milestones:
        # Only include if person is past the typical age
        if current_age > typical_age + 1:  # Add 1 year buffer
            past_events.append({
                "event_type": event_type,
                "name": event_name,
                "typical_age": typical_age,
                "completed_at_age": typical_age,  # Approximation
                "years_ago": round(current_age - typical_age, 1)
            })

    return past_events


def _return_event_name(planet: str, cycle: Optional[int]) -> str:
    if cycle:
        return f"{planet} Return Cycle {cycle}"
    return f"{planet} Return"


def _return_event_index(planet: str, cycle: Optional[int]) -> str:
    suffix = f"_C{cycle}" if cycle else ""
    return f"{planet.replace(' ', '_')}_Return{suffix}"


def _get_return_interpretation(planet: str, cycle: Optional[int]) -> str:
    planet_data = RETURN_INTERPRETATIONS.get(planet, {})
    if cycle is not None:
        if cycle in planet_data:
            return planet_data[cycle]
        # Allow fractional keys for oppositions/squares (e.g., 0.5)
        try:
            cycle_key = float(cycle)
        except (TypeError, ValueError):
            cycle_key = None
        if cycle_key and cycle_key in planet_data:
            return planet_data[cycle_key]
    return planet_data.get("default", f"{planet} return cycle of growth and integration.")


def _estimate_date_range(planet: str, tolerance: float, center: Optional[datetime]) -> Optional[str]:
    if center is None:
        return None
    orbital_period = ORBITAL_PERIODS.get(planet)
    if not orbital_period:
        return None
    try:
        deg_per_day = 360 / (orbital_period * 365.25)
    except ZeroDivisionError:  # pragma: no cover - defensive
        return None
    if deg_per_day <= 0:
        return None
    window_days = tolerance / deg_per_day
    start = (center - timedelta(days=window_days)).date()
    end = (center + timedelta(days=window_days)).date()
    return f"{start.isoformat()} to {end.isoformat()}"


def _estimate_transit_date_range(
    transit_object: str,
    aspect_type: str,
    center: Optional[datetime]
) -> Optional[str]:
    """
    Estimate date range for a major life transit (square, opposition).

    Args:
        transit_object: Transiting planet name (e.g., "Uranus", "Neptune")
        aspect_type: Type of aspect ("Square", "Opposition")
        center: Center datetime for the event

    Returns:
        Date range string "YYYY-MM-DD to YYYY-MM-DD" or None
    """
    if center is None:
        return None

    # Get orb tolerance for this aspect type
    tolerance = TRANSIT_ORB_TOLERANCE.get(aspect_type, 3.0)

    # Get orbital period
    orbital_period = ORBITAL_PERIODS.get(transit_object)
    if not orbital_period:
        return None

    try:
        deg_per_day = 360 / (orbital_period * 365.25)
    except ZeroDivisionError:
        return None

    if deg_per_day <= 0:
        return None

    # Calculate window duration in days
    window_days = tolerance / deg_per_day
    start = (center - timedelta(days=window_days)).date()
    end = (center + timedelta(days=window_days)).date()

    return f"{start.isoformat()} to {end.isoformat()}"


def _build_return_event_entry(
    planet: str,
    cycle: Optional[int],
    keywords: list,
    significance: str,
    reference_datetime: Optional[datetime],
    age: Optional[float],
    status: str,
    years_until: float = 0.0,
    orb: Optional[float] = None,
    orb_status: Optional[str] = None,
    natal_position: Optional[float] = None,
    transit_position: Optional[float] = None
) -> Dict[str, Any]:
    tolerance = RETURN_ORB_TOLERANCE.get(planet, 2.0)
    date_range = _estimate_date_range(planet, tolerance, reference_datetime)
    exact_date = reference_datetime.strftime("%Y-%m-%d") if reference_datetime else None
    interpretation = _get_return_interpretation(planet, cycle)

    entry = {
        "event_type": _return_event_name(planet, cycle),
        "event_index": _return_event_index(planet, cycle),
        "description": interpretation,
        "natal_object": planet,
        "transiting_object": planet,
        "aspect_type": "Conjunction",
        "orb": round(abs(orb), 2) if orb is not None else None,
        "orb_status": orb_status,
        "exact_date": exact_date,
        "date_range": date_range,
        "age_at_event": round(age, 1) if age is not None else None,
        "years_until_event": round(max(years_until, 0.0), 1),
        "interpretation": interpretation,
        "significance_level": significance.lower() if significance else None,
        "significance": significance,
        "keywords": keywords or [],
        "status": status,
        "category": "return"
    }

    if natal_position is not None:
        entry["natal_position"] = natal_position
    if transit_position is not None:
        entry["transit_position"] = transit_position

    return entry


def _format_major_transit_event(
    event: Dict[str, Any],
    reference_datetime: Optional[datetime],
    status: str = "active"
) -> Dict[str, Any]:
    exact_date = reference_datetime.strftime("%Y-%m-%d") if reference_datetime else None

    # Calculate date range for the transit window
    date_range = _estimate_transit_date_range(
        transit_object=event.get("transit_object"),
        aspect_type=event.get("aspect_type"),
        center=reference_datetime
    )

    # Use event orb if present (from enrichment), otherwise use None for future events
    orb_value = event.get("orb")
    orb_status_value = event.get("orb_status")

    entry = {
        "event_type": event.get("name"),
        "event_index": event.get("type", "major_transit").upper(),
        "description": event.get("description"),
        "natal_object": event.get("natal_object"),
        "transiting_object": event.get("transit_object"),
        "aspect_type": event.get("aspect_type"),
        "orb": round(abs(orb_value), 2) if orb_value is not None else None,
        "orb_status": orb_status_value,
        "exact_date": exact_date,
        "date_range": date_range,
        "age_at_event": round(event.get("age"), 1) if event.get("age") else event.get("typical_age"),
        "years_until_event": 0.0 if status == "active" else event.get("years_until"),
        "interpretation": event.get("description"),
        "significance_level": event.get("significance", "").lower(),
        "significance": event.get("significance"),
        "keywords": event.get("keywords", []),
        "status": status,
        "category": "major_transit"
    }

    if event.get("natal_position") is not None:
        entry["natal_position"] = event.get("natal_position")
    if event.get("transit_position") is not None:
        entry["transit_position"] = event.get("transit_position")

    return entry


def _format_future_event(event: Dict[str, Any]) -> Dict[str, Any]:
    # Extract current orb if available (added by _enrich_future_events_with_orbs)
    current_orb = event.get("current_orb")
    orb_status = event.get("orb_status")

    if event.get("event_type") == "return":
        predicted_dt = None
        if event.get("predicted_date"):
            try:
                predicted_dt = datetime.fromisoformat(event["predicted_date"])
            except ValueError:
                predicted_dt = None
        return _build_return_event_entry(
            planet=event.get("planet"),
            cycle=event.get("cycle_number"),
            keywords=event.get("keywords", []),
            significance=event.get("significance"),
            reference_datetime=predicted_dt,
            age=event.get("predicted_age"),
            status="upcoming",
            years_until=event.get("years_until", 0.0),
            orb=current_orb,
            orb_status=orb_status
        )

    predicted_dt = None
    if event.get("predicted_date"):
        try:
            predicted_dt = datetime.fromisoformat(event["predicted_date"])
        except ValueError:
            predicted_dt = None

    future_event = _format_major_transit_event(
        {
            **event,
            "orb": current_orb,
            "orb_status": orb_status,
        },
        predicted_dt,
        status="upcoming"
    )
    # date_range is now calculated in _format_major_transit_event
    return future_event


def _build_summary_enhancements(
    current_events: list[Dict[str, Any]],
    future_timeline: list[Dict[str, Any]],
    reference_datetime: Optional[datetime] = None
) -> Dict[str, Any]:
    enhancements: Dict[str, Any] = {}

    enhancements["critical_events_count"] = sum(
        1 for event in current_events if event.get("significance") == "CRITICAL"
    )

    next_event_name = None
    next_event_years = None
    next_event_date = None

    if current_events:
        next_event_name = _return_event_name(
            current_events[0].get("planet"),
            current_events[0].get("cycle_number")
        ) if current_events[0].get("event_type") == "return" else current_events[0].get("name")
        next_event_years = 0.0
        if reference_datetime:
            next_event_date = reference_datetime.strftime("%Y-%m-%d")
    elif future_timeline:
        top = future_timeline[0]
        if top.get("event_type") == "return":
            next_event_name = _return_event_name(top.get("planet"), top.get("cycle_number"))
        else:
            next_event_name = top.get("name")
        next_event_years = top.get("years_until")
        next_event_date = top.get("predicted_date")

    enhancements["next_major_event"] = next_event_name
    enhancements["years_until_event"] = next_event_years
    enhancements["next_major_event_date"] = next_event_date

    enhancements["upcoming_events"] = [
        _return_event_name(evt.get("planet"), evt.get("cycle_number"))
        if evt.get("event_type") == "return" else evt.get("name")
        for evt in future_timeline[:5]
    ]

    return enhancements


def format_lifecycle_event_feed(
    lifecycle_data: Dict[str, Any],
    reference_datetime: datetime,
    additional_events: Optional[list] = None
) -> Dict[str, Any]:
    current_events = lifecycle_data.get("current_events", [])
    future_timeline = lifecycle_data.get("future_timeline", [])

    formatted_events: list[Dict[str, Any]] = []

    for event in current_events:
        if event.get("event_type") == "return":
            formatted_events.append(
                _build_return_event_entry(
                    planet=event.get("planet"),
                    cycle=event.get("cycle_number"),
                    keywords=event.get("keywords", []),
                    significance=event.get("significance"),
                    reference_datetime=reference_datetime,
                    age=event.get("age"),
                    status="active",
                    years_until=0.0,
                    orb=event.get("orb"),
                    orb_status=event.get("orb_status"),
                    natal_position=event.get("natal_position"),
                    transit_position=event.get("transit_position")
                )
            )
        else:
            formatted_events.append(
                _format_major_transit_event(event, reference_datetime, status="active")
            )

    for event in future_timeline:
        formatted_events.append(_format_future_event(event))

    if additional_events:
        formatted_events.extend(additional_events)

    summary = lifecycle_data.get("lifecycle_summary", {}).copy()
    summary.update(_build_summary_enhancements(current_events, future_timeline, reference_datetime))

    return {
        "events": formatted_events,
        "summary": summary
    }

"""
Lifecycle Events Master Detection

This module provides the main entry point for lifecycle events detection.
It orchestrates all subsystems (returns, transits, timeline) and assembles
the complete lifecycle events response.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from .returns import detect_all_returns
from .transits import detect_all_major_transits
from .timeline import build_future_timeline, get_lifecycle_stage

logger = logging.getLogger(__name__)


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

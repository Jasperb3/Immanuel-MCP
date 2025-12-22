"""
Future Lifecycle Event Timeline

This module generates predictions for upcoming planetary returns and major
life transits. It calculates when future events will occur based on orbital
periods and current planetary positions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from .constants import (
    ORBITAL_PERIODS,
    RETURN_SIGNIFICANCE,
    RETURN_KEYWORDS,
    MAJOR_LIFE_TRANSITS,
    TRACKED_RETURN_PLANETS
)
from .returns import get_return_significance

logger = logging.getLogger(__name__)


def predict_next_return(
    planet_name: str,
    current_age: float,
    birth_datetime: datetime
) -> Dict[str, Any]:
    """
    Predict the next occurrence of a planetary return.

    Args:
        planet_name: Name of planet
        current_age: Current age in years
        birth_datetime: Birth datetime

    Returns:
        Prediction dict:
        {
            "planet": "Saturn",
            "type": "saturn_return",
            "cycle_number": 2,
            "predicted_age": 58.5,
            "predicted_date": "2042-06-15",
            "years_until": 12.3,
            "significance": "CRITICAL",
            "keywords": ["maturity", "responsibility", ...]
        }
    """
    if planet_name not in ORBITAL_PERIODS:
        logger.warning(f"Unknown planet for prediction: {planet_name}")
        return None

    orbital_period = ORBITAL_PERIODS[planet_name]

    # Calculate next cycle number
    current_cycle = int(current_age / orbital_period)
    next_cycle = current_cycle + 1

    # Calculate predicted age and date
    predicted_age = next_cycle * orbital_period
    years_until = predicted_age - current_age

    # Calculate predicted date
    # BUG FIX: Must add predicted_age (total years from birth) to birth_datetime,
    # NOT years_until (which would give a date too close to birth)
    days_from_birth = predicted_age * 365.25
    predicted_datetime = birth_datetime + timedelta(days=days_from_birth)

    # Get significance
    significance = get_return_significance(planet_name, next_cycle)

    return {
        "planet": planet_name,
        "type": f"{planet_name.lower().replace(' ', '_')}_return",
        "cycle_number": next_cycle,
        "predicted_age": round(predicted_age, 1),
        "predicted_date": predicted_datetime.strftime("%Y-%m-%d"),
        "years_until": round(years_until, 1),
        "significance": significance,
        "keywords": RETURN_KEYWORDS.get(planet_name, [])
    }


def predict_major_transit(
    transit_config: Dict[str, Any],
    current_age: float,
    birth_datetime: datetime
) -> Optional[Dict[str, Any]]:
    """
    Predict when a major life transit will occur.

    Uses typical age from transit configuration. For transits that can occur
    multiple times (like squares), predicts the next occurrence.

    Args:
        transit_config: Transit definition from MAJOR_LIFE_TRANSITS
        current_age: Current age in years
        birth_datetime: Birth datetime

    Returns:
        Prediction dict or None if transit has already passed:
        {
            "name": "Uranus Opposition",
            "type": "uranus_opposition",
            "typical_age": 41,
            "age_range": [40, 43],
            "predicted_date": "2031-05-20",
            "years_until": 5.2,
            "significance": "CRITICAL",
            "keywords": ["midlife", "freedom", ...],
            "description": "Uranus opposes natal Uranus..."
        }
    """
    typical_age = transit_config["typical_age"]
    age_range = transit_config["age_range"]

    # Check if transit is in the future
    if current_age >= age_range[1]:
        # Transit has likely passed
        return None

    # Calculate predicted date (use typical age)
    years_until = typical_age - current_age

    if years_until < 0:
        # Currently in the transit window
        years_until = 0
        # Use current age to project from birth
        days_from_birth = current_age * 365.25
        predicted_datetime = birth_datetime + timedelta(days=days_from_birth)
    else:
        # BUG FIX: Must add typical_age (total years from birth) to birth_datetime,
        # NOT years_until
        days_from_birth = typical_age * 365.25
        predicted_datetime = birth_datetime + timedelta(days=days_from_birth)

    return {
        "name": transit_config["name"],
        "type": transit_config["name"].lower().replace(" ", "_"),
        "natal_object": transit_config["natal_object"],
        "transit_object": transit_config["transit_object"],
        "aspect_type": transit_config["aspect_type"],
        "typical_age": typical_age,
        "age_range": list(age_range),
        "predicted_date": predicted_datetime.strftime("%Y-%m-%d"),
        "years_until": round(years_until, 1),
        "significance": transit_config["significance"],
        "keywords": transit_config["keywords"],
        "description": transit_config["description"]
    }


def build_future_timeline(
    current_age: float,
    birth_datetime: datetime,
    years_ahead: int = 20,
    max_events: int = 10
) -> List[Dict[str, Any]]:
    """
    Build a timeline of predicted future lifecycle events.

    Combines predicted planetary returns and major life transits into a
    unified chronological timeline.

    Args:
        current_age: Current age in years
        birth_datetime: Birth datetime
        years_ahead: How many years to predict (default: 20)
        max_events: Maximum number of events to return (default: 10)

    Returns:
        List of predicted events sorted by date (soonest first):
        [
            {
                "event_type": "return" | "major_transit",
                "planet": "Saturn",  # For returns
                "name": "Uranus Opposition",  # For major transits
                "predicted_date": "2030-06-15",
                "years_until": 5.2,
                "significance": "CRITICAL",
                ...
            },
            ...
        ]

    Examples:
        >>> timeline = build_future_timeline(35.0, birth_dt, years_ahead=15)
        >>> timeline[0]["name"]
        "Pluto Square"
        >>> timeline[1]["planet"]
        "Saturn"
    """
    future_events = []
    cutoff_age = current_age + years_ahead

    # Predict planetary returns
    for planet_name in TRACKED_RETURN_PLANETS:
        try:
            prediction = predict_next_return(planet_name, current_age, birth_datetime)
            # Only include if predicted age is in the future AND within cutoff
            if prediction and prediction["years_until"] > 0 and prediction["predicted_age"] <= cutoff_age:
                prediction["event_type"] = "return"
                future_events.append(prediction)
        except Exception as e:
            logger.warning(f"Error predicting {planet_name} return: {e}")
            continue

    # Predict major life transits
    for transit_config in MAJOR_LIFE_TRANSITS:
        try:
            prediction = predict_major_transit(transit_config, current_age, birth_datetime)
            if prediction and prediction["years_until"] <= years_ahead:
                prediction["event_type"] = "major_transit"
                future_events.append(prediction)
        except Exception as e:
            logger.warning(f"Error predicting {transit_config.get('name')}: {e}")
            continue

    # Sort by years_until (soonest first), then by significance
    significance_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    future_events.sort(
        key=lambda e: (
            e["years_until"],
            significance_order.get(e["significance"], 4)
        )
    )

    # Limit to max_events
    return future_events[:max_events]


def get_lifecycle_stage(age: float) -> Dict[str, Any]:
    """
    Determine current lifecycle stage based on age.

    Args:
        age: Current age in years

    Returns:
        Lifecycle stage dict:
        {
            "stage_name": "Saturn Return",
            "description": "Karmic maturation",
            "age_range": [29, 31],
            "themes": ["responsibility", "maturity", "commitment"]
        }

    Examples:
        >>> get_lifecycle_stage(29.5)
        {"stage_name": "Saturn Return", ...}
        >>> get_lifecycle_stage(41.2)
        {"stage_name": "Uranus Opposition", ...}
    """
    # Define major lifecycle stages based on transits
    stages = [
        {
            "age_range": (0, 12),
            "stage_name": "Childhood",
            "description": "Foundation building and early development",
            "themes": ["learning", "growth", "discovery"]
        },
        {
            "age_range": (12, 18),
            "stage_name": "First Jupiter Return & Adolescence",
            "description": "Expansion of identity and coming of age",
            "themes": ["identity", "independence", "exploration"]
        },
        {
            "age_range": (18, 25),
            "stage_name": "Early Adulthood",
            "description": "Independence and self-discovery",
            "themes": ["freedom", "experimentation", "relationships"]
        },
        {
            "age_range": (25, 29),
            "stage_name": "Chiron Opposition Period",
            "description": "First major wound healing crisis",
            "themes": ["healing", "vulnerability", "teaching"]
        },
        {
            "age_range": (29, 31),
            "stage_name": "Saturn Return",
            "description": "Karmic maturation and life restructuring",
            "themes": ["responsibility", "maturity", "commitment"]
        },
        {
            "age_range": (31, 36),
            "stage_name": "Post-Saturn Return",
            "description": "Building authentic path",
            "themes": ["clarity", "purpose", "manifestation"]
        },
        {
            "age_range": (36, 38),
            "stage_name": "Pluto Square",
            "description": "Deep transformation and power recalibration",
            "themes": ["transformation", "power", "rebirth"]
        },
        {
            "age_range": (38, 41),
            "stage_name": "Neptune Square",
            "description": "Spiritual crisis or awakening",
            "themes": ["spirituality", "faith", "illusion"]
        },
        {
            "age_range": (41, 43),
            "stage_name": "Uranus Opposition",
            "description": "Midlife awakening and liberation",
            "themes": ["freedom", "authenticity", "revolution"]
        },
        {
            "age_range": (43, 50),
            "stage_name": "Mature Adulthood",
            "description": "Integration of wisdom",
            "themes": ["mastery", "teaching", "legacy"]
        },
        {
            "age_range": (50, 58),
            "stage_name": "Chiron Return Period",
            "description": "Emergence as wounded healer",
            "themes": ["healing", "wisdom", "service"]
        },
        {
            "age_range": (58, 60),
            "stage_name": "Second Saturn Return",
            "description": "Elder wisdom and life review",
            "themes": ["wisdom", "legacy", "completion"]
        },
        {
            "age_range": (60, 120),
            "stage_name": "Elder Years",
            "description": "Wisdom sharing and legacy building",
            "themes": ["teaching", "legacy", "integration"]
        }
    ]

    # Find matching stage
    for stage in stages:
        min_age, max_age = stage["age_range"]
        if min_age <= age < max_age:
            return {
                "stage_name": stage["stage_name"],
                "description": stage["description"],
                "age_range": [min_age, max_age],
                "themes": stage["themes"]
            }

    # Default for very old age
    return {
        "stage_name": "Elder Years",
        "description": "Wisdom sharing and legacy building",
        "age_range": [60, 120],
        "themes": ["teaching", "legacy", "integration"]
    }

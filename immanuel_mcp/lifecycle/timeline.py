"""
Future Lifecycle Event Timeline

This module generates predictions for upcoming planetary returns and major
life transits. Given the natal chart, every event is dated by an ephemeris
search for its actual perfections; the age arithmetic in predict_next_return
and predict_major_transit is only the fallback when no natal chart is
available.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from immanuel.const import calc as calc_const
from immanuel.tools import date as date_tools

from ..constants import PLANET_CONSTANTS
from ..utils.search import PASS_GAP_DAYS, find_exact_aspect_dates, group_passes
from .constants import (
    ORBITAL_PERIODS,
    RETURN_SIGNIFICANCE,
    RETURN_KEYWORDS,
    MAJOR_LIFE_TRANSITS,
    TRACKED_RETURN_PLANETS
)
from .returns import age_on, get_return_significance
from .transits import ASPECT_ANGLES

logger = logging.getLogger(__name__)

# The search starts this far before the reference date, so a pass sequence
# already under way is reported whole. A slow planet's transit sequence can
# span a couple of years; a return's never exceeds about one.
_TRANSIT_LOOKBACK_YEARS = 4.0
_RETURN_LOOKBACK_YEARS = 1.5

# Only the next return is wanted, so its search stops after 1.5 orbital
# periods rather than scanning the whole timeline horizon: Mars, scanned over
# 20 years, cost most of a chart call.
_RETURN_WINDOW_PERIODS = 1.5

# Generous cap: Mars, the fastest tracked body, perfects ~a dozen times in a
# 20-year window.
_MAX_HITS = 64


def _jd_to_datetime(jd: float) -> datetime:
    return date_tools.to_datetime(jd, lat=0.0, lon=0.0, time_zone="UTC").replace(tzinfo=None)


def find_next_pass(
    planet_index: int,
    natal_longitude: float,
    aspect: float,
    reference: datetime,
    years_ahead: float,
    lookback_years: float = _TRANSIT_LOOKBACK_YEARS,
) -> tuple:
    """
    The first pass sequence of `aspect` to `natal_longitude` that perfects on
    or after `reference`, within `years_ahead`. Every perfection of that
    sequence is returned, including ones up to `lookback_years` behind the
    reference date, with the first perfection on or after it:
    (passes, next_pass), or ([], None) if none falls inside the window.
    Both are chosen by Julian date, so a pass within rounding of the
    reference cannot be selected as a sequence yet missing as the next pass.

    The reference is treated as UTC, as in find_event_exact_dates: a
    sub-day error cannot move a perfection the search converges on.
    """
    reference_jd = date_tools.to_jd(reference, lat=0.0, lon=0.0, time_zone="UTC")
    lookback_days = lookback_years * 365.25
    hits = find_exact_aspect_dates(
        planet_index, natal_longitude, aspect,
        reference_jd - lookback_days, lookback_days + years_ahead * 365.25,
        max_hits=_MAX_HITS,
    )
    for group in group_passes(hits):
        if group[-1] >= reference_jd:
            next_jd = next(jd for jd in group if jd >= reference_jd)
            return [_jd_to_datetime(jd) for jd in group], _jd_to_datetime(next_jd)
    return [], None


def find_last_pass(
    planet_index: int,
    natal_longitude: float,
    aspect: float,
    reference: datetime,
    lookback_years: float,
) -> List[datetime]:
    """
    The latest pass sequence of `aspect` to `natal_longitude` that finished
    before `reference`, searched back `lookback_years`: its perfections, or
    [] if none. A sequence with a pass still ahead is current, not last, so
    the search runs PASS_GAP_DAYS beyond the reference to see it whole.
    """
    reference_jd = date_tools.to_jd(reference, lat=0.0, lon=0.0, time_zone="UTC")
    lookback_days = lookback_years * 365.25
    hits = find_exact_aspect_dates(
        planet_index, natal_longitude, aspect,
        reference_jd - lookback_days, lookback_days + PASS_GAP_DAYS,
        max_hits=_MAX_HITS,
    )
    finished = [group for group in group_passes(hits) if group[-1] < reference_jd]
    return [_jd_to_datetime(jd) for jd in finished[-1]] if finished else []


def _natal_longitude(natal_chart, object_name: str) -> Optional[float]:
    index = PLANET_CONSTANTS.get(object_name)
    natal_object = natal_chart.objects.get(index) if index is not None else None
    return natal_object.longitude.raw if natal_object is not None else None


def _ephemeris_dates(passes: List[datetime], first: datetime, reference: datetime,
                     birth_datetime: datetime) -> dict:
    """Fields shared by ephemeris-dated returns and transits. `first` is the
    sequence's first pass on or after the reference."""
    return {
        "predicted_date": first.strftime("%Y-%m-%d"),
        "predicted_age": round(age_on(first, birth_datetime), 1),
        "years_until": round((first - reference).days / 365.25, 1),
        "exact_date": first.strftime("%Y-%m-%d"),
        "exact_dates": [p.strftime("%Y-%m-%d") for p in passes],
        "prediction_basis": "ephemeris",
    }


def date_next_return(
    planet_name: str,
    natal_chart,
    birth_datetime: datetime,
    reference: datetime,
    years_ahead: float,
) -> Optional[Dict[str, Any]]:
    """
    The next return of `planet_name` from the ephemeris, or None when it does
    not perfect within `years_ahead`. Falls back to predict_next_return when
    the natal chart lacks the planet.
    """
    natal_longitude = _natal_longitude(natal_chart, planet_name)
    if natal_longitude is None or planet_name not in ORBITAL_PERIODS:
        current_age = (reference - birth_datetime).days / 365.25
        return predict_next_return(planet_name, current_age, birth_datetime)

    window = min(years_ahead, ORBITAL_PERIODS[planet_name] * _RETURN_WINDOW_PERIODS)
    passes, first = find_next_pass(PLANET_CONSTANTS[planet_name], natal_longitude,
                                   calc_const.CONJUNCTION, reference, window,
                                   lookback_years=_RETURN_LOOKBACK_YEARS)
    if not passes:
        return None
    dates = _ephemeris_dates(passes, first, reference, birth_datetime)
    cycle = max(1, round(dates["predicted_age"] / ORBITAL_PERIODS[planet_name]))
    return {
        "planet": planet_name,
        "type": f"{planet_name.lower().replace(' ', '_')}_return",
        "cycle_number": cycle,
        **dates,
        "significance": get_return_significance(planet_name, cycle),
        "keywords": RETURN_KEYWORDS.get(planet_name, []),
    }


def date_next_major_transit(
    transit_config: Dict[str, Any],
    natal_chart,
    birth_datetime: datetime,
    reference: datetime,
    years_ahead: float,
) -> Optional[Dict[str, Any]]:
    """
    The next occurrence of a major life transit from the ephemeris, or None
    when it does not perfect within `years_ahead`. Unlike
    predict_major_transit there is no age gate: the generic age_range is
    wrong for some cohorts (a 1984 Uranus Opposition perfects at 44.5).
    Falls back to predict_major_transit when the natal chart lacks the planet.
    """
    natal_longitude = _natal_longitude(natal_chart, transit_config["natal_object"])
    transit_index = PLANET_CONSTANTS.get(transit_config["transit_object"])
    aspect = ASPECT_ANGLES.get(transit_config["aspect_type"])
    if natal_longitude is None or transit_index is None or aspect is None:
        current_age = (reference - birth_datetime).days / 365.25
        return predict_major_transit(transit_config, current_age, birth_datetime)

    passes, first = find_next_pass(transit_index, natal_longitude, aspect, reference, years_ahead)
    if not passes:
        return None
    return {
        "name": transit_config["name"],
        "type": transit_config["name"].lower().replace(" ", "_"),
        "natal_object": transit_config["natal_object"],
        "transit_object": transit_config["transit_object"],
        "aspect_type": transit_config["aspect_type"],
        "typical_age": transit_config["typical_age"],
        "age_range": list(transit_config["age_range"]),
        **_ephemeris_dates(passes, first, reference, birth_datetime),
        "significance": transit_config["significance"],
        "keywords": transit_config["keywords"],
        "description": transit_config["description"],
    }


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
        # Mean-motion arithmetic, not an ephemeris search: actual returns
        # drift months around the mean (Jupiter especially) and retrograde
        # passes can produce several exact hits.
        "prediction_basis": "mean_orbital_period",
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
        # Based on the generic typical age, not this chart's ephemeris.
        # Actual timing varies by birth cohort - Pluto's eccentric orbit has
        # historically placed the Pluto square anywhere from the mid-30s to
        # much later in life.
        "prediction_basis": "typical_age",
        "years_until": round(years_until, 1),
        "significance": transit_config["significance"],
        "keywords": transit_config["keywords"],
        "description": transit_config["description"]
    }


def build_future_timeline(
    current_age: float,
    birth_datetime: datetime,
    years_ahead: int = 20,
    max_events: int = 10,
    natal_chart=None,
    reference_datetime: Optional[datetime] = None,
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

    if natal_chart is not None and reference_datetime is not None:
        # Ephemeris-dated: every event's date is a real perfection.
        for planet_name in TRACKED_RETURN_PLANETS:
            try:
                event = date_next_return(planet_name, natal_chart, birth_datetime,
                                         reference_datetime, years_ahead)
            except Exception as e:
                logger.warning(f"Error dating {planet_name} return: {e}")
                continue
            if event and 0 <= event["years_until"] <= years_ahead:
                event["event_type"] = "return"
                future_events.append(event)
        for transit_config in MAJOR_LIFE_TRANSITS:
            try:
                event = date_next_major_transit(transit_config, natal_chart, birth_datetime,
                                                reference_datetime, years_ahead)
            except Exception as e:
                logger.warning(f"Error dating {transit_config.get('name')}: {e}")
                continue
            # The horizon check matters for the arithmetic fallback, which
            # is not bounded by a search window.
            if event and 0 <= event["years_until"] <= years_ahead:
                event["event_type"] = "major_transit"
                future_events.append(event)
        return _sort_and_limit(future_events, max_events)

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

    return _sort_and_limit(future_events, max_events)


def _sort_and_limit(future_events: List[Dict[str, Any]], max_events: Optional[int]) -> List[Dict[str, Any]]:
    """Soonest first, then by significance; at most max_events (None: all)."""
    significance_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    future_events.sort(
        key=lambda e: (
            e["years_until"],
            significance_order.get(e["significance"], 4)
        )
    )
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

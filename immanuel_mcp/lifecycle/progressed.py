"""Progressed chart lifecycle detections."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from immanuel.const import chart as chart_const

from .constants import (
    PROGRESSED_MOON_INTERPRETATION,
    PROGRESSED_MOON_KEYWORDS,
)
from .returns import calculate_signed_orb, determine_orb_status

logger = logging.getLogger(__name__)


PROGRESSED_MOON_ORB = 2.0  # ±2° orb requirement
PROGRESSED_MOON_PERIOD_YEARS = 27.321661  # ~27.3 year cycle


def detect_progressed_moon_return(
    natal_chart,
    progressed_chart,
    birth_datetime: datetime,
    progression_datetime: datetime
) -> List[Dict[str, Any]]:
    """Detect whether the progressed Moon is conjunct the natal Moon."""

    try:
        natal_moon = natal_chart.objects.get(chart_const.MOON)
        progressed_moon = progressed_chart.objects.get(chart_const.MOON)
    except (AttributeError, KeyError) as exc:  # pragma: no cover - library safety
        logger.warning("Progressed Moon calculation failed: %s", exc)
        return []

    natal_pos = getattr(natal_moon.longitude, "raw", None)
    progressed_pos = getattr(progressed_moon.longitude, "raw", None)
    if natal_pos is None or progressed_pos is None:  # pragma: no cover - safety
        logger.warning("Progressed Moon missing longitude data")
        return []

    orb = calculate_signed_orb(natal_pos, progressed_pos)
    orb_status = determine_orb_status(orb, PROGRESSED_MOON_ORB)
    if orb_status == "inactive":
        return []

    age = (progression_datetime - birth_datetime).days / 365.25
    cycle_number = int(max(age, 0) / PROGRESSED_MOON_PERIOD_YEARS) + 1

    window_days = PROGRESSED_MOON_ORB / (360 / (PROGRESSED_MOON_PERIOD_YEARS * 365.25))
    date_range = None
    try:
        start = (progression_datetime - timedelta(days=window_days)).date()
        end = (progression_datetime + timedelta(days=window_days)).date()
        date_range = f"{start.isoformat()} to {end.isoformat()}"
    except Exception:  # pragma: no cover - defensive
        date_range = None

    return [{
        "event_type": "Progressed Moon Return",
        "event_index": f"PROGRESSED_MOON_RETURN_C{cycle_number}",
        "description": PROGRESSED_MOON_INTERPRETATION,
        "natal_object": "Moon",
        "transiting_object": "Progressed Moon",
        "aspect_type": "Conjunction",
        "natal_position": round(natal_pos, 2),
        "transit_position": round(progressed_pos, 2),
        "orb": round(abs(orb), 2),
        "orb_status": orb_status,
        "exact_date": progression_datetime.strftime("%Y-%m-%d"),
        "date_range": date_range,
        "age_at_event": round(age, 1),
        "years_until_event": 0.0,
        "interpretation": PROGRESSED_MOON_INTERPRETATION,
        "significance_level": "high",
        "significance": "HIGH",
        "keywords": PROGRESSED_MOON_KEYWORDS,
        "status": "active",
        "category": "progressed"
    }]

"""
Major Life Transit Detection

This module detects significant non-return transits that occur at predictable
ages in a person's life. These include:

- Uranus Opposition (age 41-42): Midlife awakening
- Neptune Square (age 39-40): Spiritual crisis/awakening
- Pluto Square (age 36-37): Deep transformation
- Chiron Opposition (age 25-26): Wounded healer emergence

These transits are mathematically predictable based on orbital periods and
represent major developmental thresholds in human life.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from immanuel.const import chart as chart_const

from .constants import MAJOR_LIFE_TRANSITS
from .returns import PLANET_CONSTANTS, calculate_signed_orb

logger = logging.getLogger(__name__)

# Orb tolerance for major transits (wider than returns)
TRANSIT_ORB_TOLERANCE = {
    "Opposition": 3.0,  # 180° ± 3°
    "Square": 2.5,      # 90° ± 2.5°
}


def calculate_aspect_orb(
    natal_pos: float,
    transit_pos: float,
    aspect_type: str
) -> Optional[float]:
    """
    Calculate orb to a specific aspect angle.

    Args:
        natal_pos: Natal position in degrees (0-360)
        transit_pos: Transit position in degrees (0-360)
        aspect_type: "Opposition" (180°) or "Square" (90°)

    Returns:
        Signed orb in degrees if aspect is forming, None if aspect type unknown

    Examples:
        >>> calculate_aspect_orb(10.0, 188.0, "Opposition")
        -2.0  # 2° short of exact opposition
        >>> calculate_aspect_orb(10.0, 101.0, "Square")
        1.0   # 1° past exact square
    """
    # Get target angle for aspect
    aspect_angles = {
        "Opposition": 180.0,
        "Square": 90.0,
    }

    if aspect_type not in aspect_angles:
        logger.warning(f"Unknown aspect type: {aspect_type}")
        return None

    target_angle = aspect_angles[aspect_type]

    # Calculate raw angular separation
    separation = abs(calculate_signed_orb(natal_pos, transit_pos))

    # For square, check both 90° and 270° (waning square)
    if aspect_type == "Square":
        # Distance from 90° square
        orb_90 = abs(separation - 90.0)
        # Distance from 270° square (same as 90° waning)
        orb_270 = abs(separation - 270.0)
        # Use whichever is closer
        orb = min(orb_90, orb_270)
        # Return signed orb (negative if approaching, positive if separating)
        # This is simplified - proper implementation would track transit motion
        return orb if separation > target_angle else -orb

    # For opposition (180°)
    orb = separation - target_angle

    return orb


def check_major_transit(
    transit_config: Dict[str, Any],
    natal_chart,
    transit_chart,
    birth_datetime: datetime,
    transit_datetime: datetime
) -> Optional[Dict[str, Any]]:
    """
    Check if a specific major life transit is active.

    Args:
        transit_config: Transit definition from MAJOR_LIFE_TRANSITS
        natal_chart: Immanuel natal chart object
        transit_chart: Immanuel transit chart object
        birth_datetime: Birth datetime
        transit_datetime: Transit datetime

    Returns:
        Transit data dict if active, None if not within orb:
        {
            "name": "Uranus Opposition",
            "type": "uranus_opposition",
            "natal_object": "Uranus",
            "transit_object": "Uranus",
            "aspect_type": "Opposition",
            "natal_position": 15.3,
            "transit_position": 195.8,
            "orb": 0.5,
            "orb_status": "exact",
            "significance": "CRITICAL",
            "keywords": ["midlife", "freedom", ...],
            "description": "Uranus opposes natal Uranus...",
            "age": 41.2,
            "typical_age": 41,
            "age_range": [40, 43],
            "status": "active"
        }
    """
    # Extract configuration
    natal_object_name = transit_config["natal_object"]
    transit_object_name = transit_config["transit_object"]
    aspect_type = transit_config["aspect_type"]

    # Get planet constants
    if natal_object_name not in PLANET_CONSTANTS:
        logger.warning(f"Unknown natal object: {natal_object_name}")
        return None

    if transit_object_name not in PLANET_CONSTANTS:
        logger.warning(f"Unknown transit object: {transit_object_name}")
        return None

    natal_planet_const = PLANET_CONSTANTS[natal_object_name]
    transit_planet_const = PLANET_CONSTANTS[transit_object_name]

    # Get planet objects
    try:
        natal_planet = natal_chart.objects.get(natal_planet_const)
        transit_planet = transit_chart.objects.get(transit_planet_const)
    except (AttributeError, KeyError) as e:
        logger.warning(f"Planet not found in chart: {e}")
        return None

    # Extract positions (longitude is an Angle object with .raw attribute)
    natal_pos = natal_planet.longitude.raw
    transit_pos = transit_planet.longitude.raw

    # Calculate aspect orb
    orb = calculate_aspect_orb(natal_pos, transit_pos, aspect_type)

    if orb is None:
        return None

    # Check if within tolerance
    tolerance = TRANSIT_ORB_TOLERANCE.get(aspect_type, 3.0)
    abs_orb = abs(orb)

    if abs_orb > tolerance:
        return None  # Not within orb

    # Determine orb status
    if abs_orb <= 0.5:
        orb_status = "exact"
    elif abs_orb <= (tolerance * 0.33):
        orb_status = "tight"
    elif abs_orb <= (tolerance * 0.66):
        orb_status = "moderate"
    else:
        orb_status = "loose"

    # Calculate age
    age = (transit_datetime - birth_datetime).days / 365.25

    # Build transit data
    transit_data = {
        "name": transit_config["name"],
        "type": transit_config["name"].lower().replace(" ", "_"),
        "natal_object": natal_object_name,
        "transit_object": transit_object_name,
        "aspect_type": aspect_type,
        "natal_position": round(natal_pos, 2),
        "transit_position": round(transit_pos, 2),
        "orb": round(orb, 2),
        "orb_status": orb_status,
        "significance": transit_config["significance"],
        "keywords": transit_config["keywords"],
        "description": transit_config["description"],
        "age": round(age, 1),
        "typical_age": transit_config["typical_age"],
        "age_range": list(transit_config["age_range"]),
        "status": "active"
    }

    return transit_data


def detect_all_major_transits(
    natal_chart,
    transit_chart,
    birth_datetime: datetime,
    transit_datetime: datetime
) -> List[Dict[str, Any]]:
    """
    Detect all active major life transits.

    Checks all transits defined in MAJOR_LIFE_TRANSITS constant.

    Args:
        natal_chart: Immanuel natal chart object
        transit_chart: Immanuel transit chart object
        birth_datetime: Birth datetime
        transit_datetime: Transit datetime

    Returns:
        List of active transit dicts, sorted by significance then orb

    Examples:
        >>> transits = detect_all_major_transits(natal, transit, birth_dt, transit_dt)
        >>> [t["name"] for t in transits]
        ["Uranus Opposition", "Neptune Square"]
    """
    active_transits = []

    for transit_config in MAJOR_LIFE_TRANSITS:
        try:
            transit_data = check_major_transit(
                transit_config,
                natal_chart,
                transit_chart,
                birth_datetime,
                transit_datetime
            )
            if transit_data:
                active_transits.append(transit_data)
        except Exception as e:
            logger.warning(
                f"Error checking {transit_config.get('name', 'unknown')}: {e}"
            )
            continue

    # Sort by significance (CRITICAL > HIGH > MODERATE) then by orb
    significance_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    active_transits.sort(
        key=lambda t: (
            significance_order.get(t["significance"], 4),
            abs(t["orb"])
        )
    )

    return active_transits

"""Dignity extraction and building"""

from typing import Any, Dict, Optional
from ..constants import CELESTIAL_BODIES

def extract_primary_dignity(dignities: Dict[str, Any]) -> Optional[str]:
    """
    Extract primary dignity as a simple string.

    Args:
        dignities: Dignities dict from immanuel

    Returns:
        Dignity string like "Ruler", "Exalted", "Detriment", "Fall", or combination
    """
    if not dignities:
        return None

    parts = []

    # Check for primary dignities in order of strength
    if dignities.get('ruler'):
        parts.append('Ruler')
    if dignities.get('exalted'):
        parts.append('Exalted')
    if dignities.get('detriment'):
        parts.append('Detriment')
    if dignities.get('fall'):
        parts.append('Fall')

    # Check for secondary dignities
    if dignities.get('triplicity_ruler'):
        parts.append('Triplicity Ruler')
    if dignities.get('term_ruler'):
        parts.append('Term Ruler')
    if dignities.get('face_ruler'):
        parts.append('Face Ruler')

    if dignities.get('peregrine'):
        parts.append('Peregrine')

    return ', '.join(parts) if parts else None


def build_optimized_transit_positions(transit_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build optimized transit positions using planet names as keys.

    Args:
        transit_data: Full transit chart data from ToJSON serializer

    Returns:
        Optimized dict with planet names as keys
    """
    optimized = {}

    for obj_key, obj_data in transit_data.get('objects', {}).items():
        if not isinstance(obj_data, dict):
            continue

        index = obj_data.get('index')
        if index not in CELESTIAL_BODIES:
            continue  # Skip objects not in our mapping

        name = CELESTIAL_BODIES[index]

        # Build optimized object
        optimized[name] = {
            'position': format_position(
                obj_data.get('sign_longitude', {}),
                obj_data.get('sign', {}).get('name', '')
            ),
            'declination': format_declination(obj_data.get('declination', {})),
            'retrograde': obj_data.get('movement', {}).get('retrograde', False),
            'out_of_bounds': obj_data.get('out_of_bounds', False),
            'house': obj_data.get('house', {}).get('number')
        }

    return optimized


def build_dignities_section(transit_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Build a separate dignities section with planet names as keys.

    Args:
        transit_data: Full transit chart data from ToJSON serializer

    Returns:
        Dict mapping planet names to dignity strings
    """
    dignities = {}

    for obj_key, obj_data in transit_data.get('objects', {}).items():
        if not isinstance(obj_data, dict):
            continue

        index = obj_data.get('index')
        if index not in CELESTIAL_BODIES:
            continue

        name = CELESTIAL_BODIES[index]
        dignity_str = extract_primary_dignity(obj_data.get('dignities', {}))

        if dignity_str:
            dignities[name] = dignity_str

    return dignities

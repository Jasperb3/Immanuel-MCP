"""Position formatting and optimization"""

from typing import Any, Dict
from ..constants import CELESTIAL_BODIES

def format_position(sign_longitude: Dict[str, Any], sign_name: str) -> str:
    """
    Create a compact position string from sign longitude and sign name.

    Args:
        sign_longitude: Sign longitude dict with 'formatted' field
        sign_name: Name of the zodiac sign

    Returns:
        Compact position string like "28°51' Sagittarius"
    """
    # Extract just degrees and minutes from formatted string (e.g., "28°51'07"" -> "28°51'")
    formatted = sign_longitude.get('formatted', '')
    # Remove seconds portion if present
    if '"' in formatted:
        parts = formatted.split('"')[0]  # Get everything before the seconds marker
        # Reconstruct without seconds
        formatted = parts.strip() + "'"

    return f"{formatted} {sign_name}"


def format_declination(declination: Dict[str, Any]) -> str:
    """
    Create a compact declination string.

    Args:
        declination: Declination dict with 'formatted' field

    Returns:
        Compact declination string like "-23°26'"
    """
    formatted = declination.get('formatted', '')
    # Remove seconds if present
    if '"' in formatted:
        parts = formatted.split('"')[0]
        formatted = parts.strip() + "'"
    return formatted


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

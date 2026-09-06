"""Position formatting and optimization"""

from typing import Any, Dict, Optional
from ..constants import CELESTIAL_BODIES

def format_position(sign_longitude: Dict[str, Any], sign_name: str) -> str:
    """
    Create a position string from sign longitude and sign name.

    Immanuel already formats these as D°M'S" (see immanuel.tools.convert),
    so the string is used as-is. An earlier version tried to trim the seconds
    by splitting on the seconds mark - which sits after the digits - and then
    re-appending a minutes mark, turning 12°21'42" into 12°21'42'.

    Args:
        sign_longitude: Sign longitude dict with 'formatted' field
        sign_name: Name of the zodiac sign

    Returns:
        Position string like "12°21'42\" Scorpio"
    """
    return f"{sign_longitude.get('formatted', '')} {sign_name}"


def format_declination(declination: Dict[str, Any]) -> str:
    """
    Create a declination string.

    Passed through from immanuel unchanged, for the same reason as
    format_position.

    Args:
        declination: Declination dict with 'formatted' field

    Returns:
        Declination string like "-23°26'19\""
    """
    return declination.get('formatted', '')


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

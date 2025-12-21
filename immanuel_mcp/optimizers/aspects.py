"""Aspect optimization"""

from typing import Any, Dict, List
from ..constants import CELESTIAL_BODIES
from ..pagination.helpers import classify_aspect_priority

def build_optimized_aspects(aspects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build optimized aspect list with planet names and simplified structure.

    Args:
        aspects: List of aspect dicts from the endpoint

    Returns:
        Optimized aspect list
    """
    optimized = []

    for aspect in aspects:
        if not isinstance(aspect, dict):
            continue

        # Get planet names from active/passive or object1/object2
        active_name = aspect.get('object1')
        passive_name = aspect.get('object2')

        if not active_name or not passive_name:
            # Fallback to numeric lookup if names not present
            active_id = aspect.get('active')
            passive_id = aspect.get('passive')
            active_name = CELESTIAL_BODIES.get(active_id, f"Unknown({active_id})")
            passive_name = CELESTIAL_BODIES.get(passive_id, f"Unknown({passive_id})")

        # Get movement as simple string
        movement = aspect.get('movement', {})
        if isinstance(movement, dict):
            movement_str = movement.get('formatted', 'Unknown')
        else:
            movement_str = str(movement)

        # Build optimized aspect
        optimized_aspect = {
            'planets': f"{active_name} → {passive_name}",
            'type': aspect.get('type'),
            'orb': round(abs(aspect.get('orb', 0)), 2),
            'movement': movement_str,
            'priority': classify_aspect_priority(aspect)
        }

        # Add interpretation if present
        if 'interpretation' in aspect:
            optimized_aspect['interpretation'] = aspect['interpretation']

        # Add keywords if present
        if 'keywords' in aspect:
            optimized_aspect['keywords'] = aspect['keywords']

        # Add nature if present
        if 'nature' in aspect:
            optimized_aspect['nature'] = aspect['nature']

        optimized.append(optimized_aspect)

    return optimized

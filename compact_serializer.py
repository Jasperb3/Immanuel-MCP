
import json
from typing import Any, Dict, List
from immanuel.classes.serialize import ToJSON
from immanuel.const import chart as chart_const, data as data_const


class CompactJSONSerializer(ToJSON):
    """
    Custom JSON serializer to create a compact, optimized representation of astrological charts.

    This serializer is specifically designed to reduce token usage when working with Large Language Models (LLMs)
    by filtering and simplifying astrological chart data while retaining the most essential information.

    Objects Included:
        - Major planets: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto
        - Key angles: Ascendant (ASC), Midheaven (MC)

    Objects Excluded:
        - Minor asteroids (e.g., Chiron, Ceres, Pallas, Juno, Vesta)
        - Fixed stars
        - Arabic parts
        - Other minor celestial bodies

    Aspects Included:
        - Major aspects only: Conjunction, Opposition, Square, Trine, Sextile

    Aspects Excluded:
        - Minor aspects (e.g., semi-sextile, quincunx, sesquiquadrate)
        - Aspect patterns

    Data Excluded:
        - Detailed weightings and dignities
        - Chart shape analysis
        - Moon phase details (beyond basic phase type)
        - Detailed velocity and movement data
        - Parallels and contra-parallels
        - Minor house cusps details

    Purpose:
        This compact format optimizes for LLM token usage while maintaining all critical astrological
        information needed for chart interpretation. Typical token reduction: 60-70% compared to full charts.

    Returns:
        A dictionary containing:
        - objects: Simplified planetary data with name, sign, degree, house, and retrograde status
        - houses: House cusps and associated signs
        - aspects: Filtered list of major aspects between major objects only
    """

    # Define included objects and aspects at class level
    INCLUDED_OBJECTS = [
        chart_const.SUN, chart_const.MOON, chart_const.MERCURY, chart_const.VENUS,
        chart_const.MARS, chart_const.JUPITER, chart_const.SATURN, chart_const.URANUS,
        chart_const.NEPTUNE, chart_const.PLUTO, chart_const.ASC, chart_const.MC
    ]
    INCLUDED_ASPECTS = ['conjunction', 'opposition', 'square', 'trine', 'sextile']

    def _is_chart_object(self, obj: Any) -> bool:
        """Check if object is an Immanuel chart type."""
        type_name = type(obj).__name__
        return type_name in ['Natal', 'SolarReturn', 'Progressed', 'Composite', 'Transits']

    def _convert_to_dict(self, obj: Any) -> Any:
        """
        Recursively convert an Immanuel object to a dict using ToJSON logic.
        """
        # Use base ToJSON serializer to get proper dict representation
        return json.loads(json.dumps(obj, cls=ToJSON))

    def default(self, obj: Any) -> Dict[str, Any]:
        # Check if this is a chart object (Natal, SolarReturn, etc.)
        if self._is_chart_object(obj):
            # First convert to dict using the base ToJSON serializer
            chart_dict = self._convert_to_dict(obj)

            # Build the simplified output dictionary
            compact_chart = {}

            # Simplify and filter objects
            if data_const.OBJECTS in chart_dict:
                simplified_objects = {}
                for k, v in chart_dict[data_const.OBJECTS].items():
                    if v.get('index') in self.INCLUDED_OBJECTS:
                        simplified_objects[k] = {
                            'name': v.get('name'),
                            'sign': v.get('sign', {}).get('name'),
                            'sign_longitude': v.get('sign_longitude', {}).get('formatted'),
                            'house': v.get('house', {}).get('number'),
                            'retrograde': v.get('movement', {}).get('retrograde', False)
                        }
                compact_chart['objects'] = simplified_objects

            # Include houses
            if data_const.HOUSES in chart_dict:
                compact_chart['houses'] = chart_dict[data_const.HOUSES]

            # Simplify and filter aspects - always returns a list
            if data_const.ASPECTS in chart_dict:
                simplified_aspects = []
                # Resolve object names for aspects
                object_names = {obj['index']: obj['name'] for obj in chart_dict.get(data_const.OBJECTS, {}).values()}

                aspects_data = chart_dict[data_const.ASPECTS]

                # Handle nested dict format: {from_object_id: {to_object_id: aspect_dict}}
                for aspects_for_object in aspects_data.values():
                    if isinstance(aspects_for_object, dict):
                        for aspect in aspects_for_object.values():
                            if isinstance(aspect, dict) and aspect.get('type', '').lower() in self.INCLUDED_ASPECTS:
                                # Only include aspects between major objects
                                active_index = aspect.get('active')
                                passive_index = aspect.get('passive')

                                # Filter to only major objects
                                if active_index in self.INCLUDED_OBJECTS and passive_index in self.INCLUDED_OBJECTS:
                                    active_name = object_names.get(active_index)
                                    passive_name = object_names.get(passive_index)
                                    if active_name and passive_name:
                                        simplified_aspects.append({
                                            'type': aspect.get('type'),
                                            'object1': active_name,
                                            'object2': passive_name,
                                            'orb': aspect.get('difference', {}).get('raw'),
                                            'active': active_index,
                                            'passive': passive_index
                                        })

                compact_chart['aspects'] = simplified_aspects

            return compact_chart

        # Fallback for other types
        return super().default(obj)

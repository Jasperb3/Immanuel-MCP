
import json
from immanuel.classes.serialize import ToJSON
from immanuel.const import chart as chart_const, data as data_const

class CompactJSONSerializer(ToJSON):
    """
    Custom JSON serializer to create a compact, but still useful, representation of a natal chart.
    It includes houses but removes other less critical top-level properties.
    """
    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            # The base serializer can convert the main chart object to a dict
            chart_dict = obj.to_dict()

            # 1. Define what to include
            included_objects = [
                chart_const.SUN, chart_const.MOON, chart_const.MERCURY, chart_const.VENUS,
                chart_const.MARS, chart_const.JUPITER, chart_const.SATURN, chart_const.URANUS,
                chart_const.NEPTUNE, chart_const.PLUTO, chart_const.ASC, chart_const.MC
            ]
            included_aspects = [
                'conjunction', 'opposition', 'square', 'trine', 'sextile'
            ]

            # 2. Build the simplified output dictionary
            compact_chart = {}

            # 3. Simplify and filter objects
            if data_const.OBJECTS in chart_dict:
                simplified_objects = {}
                for k, v in chart_dict[data_const.OBJECTS].items():
                    if v.get('index') in included_objects:
                        simplified_objects[k] = {
                            'name': v.get('name'),
                            'sign': v.get('sign', {}).get('name'),
                            'sign_longitude': v.get('sign_longitude', {}).get('formatted'),
                            'house': v.get('house', {}).get('number'),
                            'retrograde': v.get('movement', {}).get('retrograde', False)
                        }
                compact_chart['objects'] = simplified_objects

            # 4. Include houses as requested
            if data_const.HOUSES in chart_dict:
                compact_chart['houses'] = chart_dict[data_const.HOUSES]


            # 5. Simplify and filter aspects
            if data_const.ASPECTS in chart_dict:
                simplified_aspects = []
                # Resolve object names for aspects
                object_names = {obj['index']: obj['name'] for obj in chart_dict.get(data_const.OBJECTS, {}).values()}

                for aspects_for_object in chart_dict[data_const.ASPECTS].values():
                    for aspect in aspects_for_object.values():
                        if aspect.get('type', '').lower() in included_aspects:
                            active_name = object_names.get(aspect.get('active'))
                            passive_name = object_names.get(aspect.get('passive'))
                            if active_name and passive_name:
                                simplified_aspects.append({
                                    'type': aspect.get('type'),
                                    'object1': active_name,
                                    'object2': passive_name,
                                    'orb': aspect.get('difference', {}).get('raw')
                                })
                compact_chart['aspects'] = simplified_aspects

            return compact_chart

        # Fallback for other types
        return super().default(obj)

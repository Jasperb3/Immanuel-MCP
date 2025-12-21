#!/usr/bin/env python3
"""Compare ToJSON vs CompactJSONSerializer output formats."""

from immanuel import charts
from immanuel.classes.serialize import ToJSON
from compact_serializer import CompactJSONSerializer
import json


def compare_serializers():
    """Compare the structure produced by ToJSON vs CompactJSONSerializer."""
    print("\n[COMPARISON] Comparing ToJSON vs CompactJSONSerializer...")

    # Create test charts
    natal_subject = charts.Subject(
        date_time="1984-01-11 18:45:00",
        latitude=40.7128,
        longitude=-74.0060
    )
    transit_subject = charts.Subject(
        date_time="2024-12-20 12:00:00",
        latitude=40.7128,
        longitude=-74.0060
    )

    natal_chart = charts.Natal(natal_subject)
    transit_chart = charts.Natal(transit_subject, aspects_to=natal_chart)

    # Serialize with ToJSON
    print("\n[ToJSON Serializer]")
    full_data = json.loads(json.dumps(transit_chart, cls=ToJSON))
    print(f"  aspects type: {type(full_data.get('aspects'))}")
    if isinstance(full_data.get('aspects'), dict):
        print(f"  aspects keys (first 5): {list(full_data['aspects'].keys())[:5]}")
    elif isinstance(full_data.get('aspects'), list):
        print(f"  aspects count: {len(full_data['aspects'])}")

    # Serialize with CompactJSONSerializer
    print("\n[CompactJSONSerializer]")
    compact_data = json.loads(json.dumps(transit_chart, cls=CompactJSONSerializer))
    print(f"  aspects type: {type(compact_data.get('aspects'))}")
    if isinstance(compact_data.get('aspects'), dict):
        print(f"  aspects keys (first 5): {list(compact_data['aspects'].keys())[:5]}")
    elif isinstance(compact_data.get('aspects'), list):
        print(f"  aspects count: {len(compact_data['aspects'])}")

    print("\n[CONCLUSION]")
    if type(full_data.get('aspects')) != type(compact_data.get('aspects')):
        print("  [ISSUE FOUND] ToJSON and CompactJSONSerializer return different data structures!")
        print(f"  ToJSON returns: {type(full_data.get('aspects'))}")
        print(f"  CompactJSONSerializer returns: {type(compact_data.get('aspects'))}")
    else:
        print("  Both serializers return the same data structure type")


if __name__ == "__main__":
    compare_serializers()

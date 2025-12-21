#!/usr/bin/env python3
"""Inspect the structure of the full transit endpoint response."""

from immanuel_server import generate_transit_to_natal
import json


def inspect_response_structure():
    """Inspect what the full endpoint actually returns."""
    print("\n[INSPECTION] Checking full transit endpoint response structure...")

    result = generate_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    print(f"\n[INFO] Top-level keys: {list(result.keys())}")

    # Check natal_summary
    if "natal_summary" in result:
        print(f"[INFO] natal_summary keys: {list(result['natal_summary'].keys())}")

    # Check transit_positions structure
    if "transit_positions" in result:
        transit_pos = result["transit_positions"]
        print(f"[INFO] transit_positions type: {type(transit_pos)}")
        if isinstance(transit_pos, dict):
            print(f"[INFO] transit_positions keys: {list(transit_pos.keys())[:5]}...")  # First 5
            # Sample one position
            first_key = list(transit_pos.keys())[0] if transit_pos else None
            if first_key:
                first_obj = transit_pos[first_key]
                print(f"[INFO] Sample position ({first_key}) keys: {list(first_obj.keys()) if isinstance(first_obj, dict) else type(first_obj)}")

    # Check transit_to_natal_aspects structure
    if "transit_to_natal_aspects" in result:
        aspects = result["transit_to_natal_aspects"]
        print(f"[INFO] transit_to_natal_aspects type: {type(aspects)}")
        if isinstance(aspects, dict):
            print(f"[INFO] transit_to_natal_aspects keys: {list(aspects.keys())[:5]}...")
        elif isinstance(aspects, list):
            print(f"[INFO] transit_to_natal_aspects count: {len(aspects)}")
            if aspects:
                print(f"[INFO] Sample aspect keys: {list(aspects[0].keys()) if isinstance(aspects[0], dict) else type(aspects[0])}")

    # Size check
    json_str = json.dumps(result)
    print(f"\n[INFO] Total JSON size: {len(json_str) / 1024:.2f} KB")
    print(f"[INFO] natal_summary size: {len(json.dumps(result.get('natal_summary', {}))) / 1024:.2f} KB")
    print(f"[INFO] transit_positions size: {len(json.dumps(result.get('transit_positions', {}))) / 1024:.2f} KB")
    print(f"[INFO] transit_to_natal_aspects size: {len(json.dumps(result.get('transit_to_natal_aspects', {}))) / 1024:.2f} KB")


if __name__ == "__main__":
    inspect_response_structure()

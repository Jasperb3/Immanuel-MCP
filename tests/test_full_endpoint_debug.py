#!/usr/bin/env python3
"""
Debug test for generate_transit_to_natal full endpoint.
Testing the exact scenario provided by the user.
"""

import sys
import json
from immanuel_server import generate_transit_to_natal

print("=" * 80)
print("TESTING FULL TRANSIT_TO_NATAL ENDPOINT")
print("=" * 80)
print()

# User's exact test case
test_input = {
    "natal_date_time": "1984-01-11 18:45:00",
    "natal_latitude": "51n23",
    "natal_longitude": "0w05",
    "timezone": "Europe/London",
    "transit_date_time": "2025-12-20 12:00:00",
    "transit_latitude": "51n34",
    "transit_longitude": "0w09"
}

print("Test Input:")
for key, value in test_input.items():
    print(f"  {key}: {value}")
print()

print("Calling generate_transit_to_natal...")
print()

try:
    result = generate_transit_to_natal(**test_input)

    print("Result received!")
    print()

    # Check for error response
    if result.get("error"):
        print(f"ERROR: {result.get('message')}")
        print(f"Type: {result.get('type')}")
        sys.exit(1)

    # Analyze the response
    print("Response Structure:")
    print(f"  Keys: {list(result.keys())}")
    print()

    print("Natal Summary:")
    natal_summary = result.get("natal_summary", {})
    for key, value in natal_summary.items():
        print(f"  {key}: {value}")
    print()

    print("Transit Info:")
    print(f"  transit_date: {result.get('transit_date')}")
    print(f"  timezone: {result.get('timezone')}")
    print()

    print("Transit Positions:")
    transit_positions = result.get("transit_positions", {})
    print(f"  Total objects: {len(transit_positions)}")
    if transit_positions:
        # Show first object as example
        first_obj = list(transit_positions.values())[0]
        print(f"  Example object keys: {list(first_obj.keys())}")
        print(f"  Example: {first_obj.get('name')} in {first_obj.get('sign')}")
    print()

    print("Transit-to-Natal Aspects:")
    aspects = result.get("transit_to_natal_aspects", [])
    print(f"  Total aspects: {len(aspects)}")

    if isinstance(aspects, list) and aspects:
        print(f"  Aspects are a list: YES")
        first_aspect = aspects[0]
        print(f"  Example aspect keys: {list(first_aspect.keys())}")
        print(f"  Example: {first_aspect.get('object1')} {first_aspect.get('type')} {first_aspect.get('object2')}")
    elif isinstance(aspects, dict):
        print(f"  WARNING: Aspects are still a dict, not a list!")
        print(f"  Dict keys: {list(aspects.keys())[:5]}")
    else:
        print(f"  WARNING: Aspects are type {type(aspects)}")
    print()

    # Show detailed aspect info
    if aspects and isinstance(aspects, list):
        print("First Aspect Details:")
        first_aspect = aspects[0]
        for key, value in first_aspect.items():
            if key in ['active', 'passive', 'type', 'aspect', 'orb']:
                print(f"  {key}: {value}")
        print()

    # Test JSON serializability
    print("JSON Serialization Test:")
    try:
        json_str = json.dumps(result)
        size_kb = len(json_str) / 1024
        print(f"  [OK] Successfully serialized to JSON")
        print(f"  Size: {size_kb:.2f} KB")

        # Check for known problematic patterns
        if '"3000003"' in json_str:
            print(f"  WARNING: Found numeric string keys like '3000003' in JSON")
        if '{"3000003": {' in json_str:
            print(f"  WARNING: Found nested dict pattern with numeric keys!")

    except (TypeError, ValueError) as e:
        print(f"  [FAIL] JSON serialization failed: {e}")
        print(f"  This is likely the root cause!")
    print()

    # Summary
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()

    if result.get("transit_to_natal_aspects") and isinstance(result["transit_to_natal_aspects"], list):
        print("[SUCCESS] Full endpoint appears to be working correctly!")
    else:
        print("[FAILURE] Full endpoint has issues with aspect structure")

except Exception as e:
    print(f"EXCEPTION RAISED: {type(e).__name__}")
    print(f"Message: {str(e)}")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)

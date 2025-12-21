#!/usr/bin/env python3
"""Test the full transit_to_natal endpoint to diagnose the issue."""

import sys
import json
from immanuel_server import generate_transit_to_natal

# Test data (same as user's test)
natal_date = "1990-01-15 12:00:00"
natal_lat = "51n30"
natal_lon = "0w10"
transit_date = "2024-12-18 12:00:00"
transit_lat = "51n30"
transit_lon = "0w10"

print("Testing full endpoint: generate_transit_to_natal")
print("=" * 60)

try:
    # Test with default aspect_priority="all"
    print("\n[TEST 1] Testing with aspect_priority='all' (DEFAULT)")
    result1 = generate_transit_to_natal(
        natal_date_time=natal_date,
        natal_latitude=natal_lat,
        natal_longitude=natal_lon,
        transit_date_time=transit_date,
        transit_latitude=transit_lat,
        transit_longitude=transit_lon
        # aspect_priority defaults to "all"
    )

    json_str1 = json.dumps(result1)
    size_kb1 = len(json_str1) / 1024
    print(f"Result size with ALL aspects: {size_kb1:.2f} KB")
    print(f"Number of aspects: {len(result1.get('transit_to_natal_aspects', []))}")

    # Test with tight
    print("\n[TEST 2] Testing with aspect_priority='tight'")
    result = generate_transit_to_natal(
        natal_date_time=natal_date,
        natal_latitude=natal_lat,
        natal_longitude=natal_lon,
        transit_date_time=transit_date,
        transit_latitude=transit_lat,
        transit_longitude=transit_lon,
        aspect_priority='tight'
    )

    # Check if error
    if isinstance(result, dict) and result.get('error'):
        print(f"\n[ERROR] {result.get('message')}")
        print(f"Type: {result.get('type')}")
    else:
        # Success - check size
        json_str = json.dumps(result)
        size_kb = len(json_str) / 1024
        print(f"\n[SUCCESS]")
        print(f"Response size: {size_kb:.2f} KB")
        print(f"\nResult keys: {list(result.keys())}")
        print(f"Number of aspects: {len(result.get('transit_to_natal_aspects', []))}")

        # Show sample
        print(f"\nNatal summary: {result.get('natal_summary')}")
        print(f"Aspect summary: {result.get('aspect_summary')}")
        print(f"Pagination: {result.get('pagination')}")

        # Test JSON serialization
        try:
            json.dumps(result)
            print("\n[OK] Result is JSON serializable")
        except Exception as e:
            print(f"\n[FAIL] JSON serialization failed: {e}")

except Exception as e:
    print(f"\n[EXCEPTION] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

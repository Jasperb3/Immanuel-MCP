#!/usr/bin/env python3
"""
Test script to verify the three critical issues:
1. natal_summary fields returning "Unknown"
2. Decimal degree coordinate parsing
3. Error handling for format conversion
"""

import sys
import json
from immanuel import charts
from immanuel.const import chart as chart_const

# Test Issue #1: natal_summary returning "Unknown"
print("=" * 60)
print("TEST 1: Investigating natal_summary 'Unknown' issue")
print("=" * 60)

# Create a test natal chart
subject = charts.Subject(
    date_time='2000-01-01 12:00:00',
    latitude=32.71,
    longitude=-117.15
)
natal = charts.Natal(subject)

print("\nDirect object access (using chart constants):")
print(f"chart_const.SUN = {chart_const.SUN}")
print(f"chart_const.MOON = {chart_const.MOON}")
print(f"chart_const.ASC = {chart_const.ASC}")

print("\nAttempting to access objects:")
sun = natal.objects.get(chart_const.SUN)
moon = natal.objects.get(chart_const.MOON)
asc = natal.objects.get(chart_const.ASC)

print(f"Sun object: {sun}")
print(f"Moon object: {moon}")
print(f"Ascendant object: {asc}")

print("\nChecking what keys exist in natal.objects:")
print(f"natal.objects type: {type(natal.objects)}")
print(f"natal.objects keys: {list(natal.objects.keys()) if hasattr(natal.objects, 'keys') else 'N/A'}")

# Try alternative access methods
print("\nTrying alternative access methods:")
if hasattr(natal, 'objects'):
    print(f"natal.objects attributes: {dir(natal.objects)}")

    # Check if it's a dict-like object
    if hasattr(natal.objects, 'items'):
        print("\nAll objects in natal.objects:")
        for key, obj in natal.objects.items():
            print(f"  Key: {key}, Name: {getattr(obj, 'name', 'N/A')}, Type: {type(obj)}")

# Test Issue #2: Decimal coordinate parsing
print("\n" + "=" * 60)
print("TEST 2: Decimal degree coordinate parsing")
print("=" * 60)

from immanuel_server import parse_coordinate

test_coordinates = [
    # (input, is_latitude, expected_result, description)
    ("32.71", True, 32.71, "Decimal latitude (positive)"),
    ("-32.71", True, -32.71, "Decimal latitude (negative)"),
    ("117.15", False, 117.15, "Decimal longitude (positive)"),
    ("-117.15", False, -117.15, "Decimal longitude (negative)"),
    ("32n43", True, 32.71666667, "DMS latitude (north)"),
    ("32s43", True, -32.71666667, "DMS latitude (south)"),
    ("117w09", False, -117.15, "DMS longitude (west)"),
    ("117e09", False, 117.15, "DMS longitude (east)"),
]

print("\nTesting coordinate parsing:")
for coord_str, is_lat, expected, desc in test_coordinates:
    try:
        result = parse_coordinate(coord_str, is_latitude=is_lat)
        status = "✓ PASS" if abs(result - expected) < 0.01 else f"✗ FAIL (got {result})"
        print(f"{status}: {desc:40} '{coord_str}' -> {result:.6f}")
    except Exception as e:
        print(f"✗ ERROR: {desc:40} '{coord_str}' -> {e}")

# Test Issue #3: Error handling for invalid formats
print("\n" + "=" * 60)
print("TEST 3: Error handling for format conversion")
print("=" * 60)

invalid_coordinates = [
    ("invalid", True, "Invalid text"),
    ("999", True, "Out of range latitude"),
    ("abc123", False, "Mixed alphanumeric"),
    ("", True, "Empty string"),
]

print("\nTesting error handling:")
for coord_str, is_lat, desc in invalid_coordinates:
    try:
        result = parse_coordinate(coord_str, is_latitude=is_lat)
        print(f"✗ FAIL: {desc:40} '{coord_str}' -> Should have raised error but got {result}")
    except ValueError as e:
        print(f"✓ PASS: {desc:40} '{coord_str}' -> Raised ValueError: {str(e)[:60]}")
    except Exception as e:
        print(f"? UNKNOWN: {desc:40} '{coord_str}' -> Raised {type(e).__name__}: {str(e)[:60]}")

print("\n" + "=" * 60)
print("Testing complete!")
print("=" * 60)

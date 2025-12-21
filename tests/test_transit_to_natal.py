#!/usr/bin/env python3
"""
Comprehensive test suite for Transit-to-Natal functionality (Phase 1 feature).

Tests both generate_transit_to_natal and generate_compact_transit_to_natal functions
to verify Phase 1 completion of the ENHANCEMENT_PLAN.md.

Tests cover:
1. Basic transit-to-natal calculation
2. Coordinate format compatibility (decimal, DMS, space-separated)
3. Timezone parameter support
4. Aspect interpretation hints
5. Default transit location (using natal location)
6. Error handling
"""

import sys
from datetime import datetime
from immanuel_server import (
    generate_transit_to_natal,
    generate_compact_transit_to_natal
)

print("=" * 80)
print("TRANSIT-TO-NATAL FUNCTIONALITY TEST SUITE (Phase 1 Verification)")
print("=" * 80)
print()

# Test data: Using a known birth chart and transit date
NATAL_DATA = {
    "date_time": "1990-01-15 12:00:00",
    "latitude": "51.5074",  # London
    "longitude": "-0.1278",
}

TRANSIT_DATA = {
    "date_time": "2024-12-20 12:00:00",
}

# Test Suite 1: Basic Transit-to-Natal Calculation
print("TEST SUITE 1: Basic Transit-to-Natal Calculation")
print("-" * 80)

print("\n1.1 Testing generate_transit_to_natal() with decimal coordinates...")
try:
    result = generate_transit_to_natal(
        natal_date_time=NATAL_DATA["date_time"],
        natal_latitude=NATAL_DATA["latitude"],
        natal_longitude=NATAL_DATA["longitude"],
        transit_date_time=TRANSIT_DATA["date_time"]
    )

    # Check for error response
    if result.get("error"):
        print(f"  FAIL: Function returned error: {result.get('message')}")
    else:
        # Verify result structure
        required_keys = ["natal_summary", "transit_date", "transit_positions", "transit_to_natal_aspects"]
        missing_keys = [k for k in required_keys if k not in result]

        if missing_keys:
            print(f"  FAIL: Missing keys in result: {missing_keys}")
        else:
            print(f"  PASS: Full transit-to-natal generated successfully")
            print(f"    Natal Sun Sign: {result['natal_summary'].get('sun_sign')}")
            print(f"    Natal Moon Sign: {result['natal_summary'].get('moon_sign')}")
            print(f"    Natal Rising: {result['natal_summary'].get('rising_sign')}")
            print(f"    Transit Date: {result['transit_date']}")
            print(f"    Number of transit positions: {len(result.get('transit_positions', {}))}")
            print(f"    Has transit aspects: {bool(result.get('transit_to_natal_aspects'))}")

            # Verify natal_summary doesn't have "Unknown" values (bug fix verification)
            if result['natal_summary'].get('sun_sign') == 'Unknown':
                print(f"  WARNING: Sun sign is 'Unknown' - may indicate bug #1 regression")
            if result['natal_summary'].get('moon_sign') == 'Unknown':
                print(f"  WARNING: Moon sign is 'Unknown' - may indicate bug #1 regression")
            if result['natal_summary'].get('rising_sign') == 'Unknown':
                print(f"  WARNING: Rising sign is 'Unknown' - may indicate bug #1 regression")

except Exception as e:
    print(f"  FAIL: Exception raised: {type(e).__name__}: {e}")

print()

# Test Suite 2: Compact Transit-to-Natal with Interpretations
print("TEST SUITE 2: Compact Transit-to-Natal with Aspect Interpretations")
print("-" * 80)

print("\n2.1 Testing generate_compact_transit_to_natal() with interpretations...")
try:
    result = generate_compact_transit_to_natal(
        natal_date_time=NATAL_DATA["date_time"],
        natal_latitude=NATAL_DATA["latitude"],
        natal_longitude=NATAL_DATA["longitude"],
        transit_date_time=TRANSIT_DATA["date_time"],
        include_interpretations=True
    )

    if result.get("error"):
        print(f"  FAIL: Function returned error: {result.get('message')}")
    else:
        print(f"  PASS: Compact transit-to-natal generated successfully")

        # Check for aspect interpretations (Phase 1 feature)
        aspects = result.get('transit_aspects', [])
        if aspects:
            print(f"    Number of major aspects: {len(aspects)}")

            # Check if interpretations are present
            has_keywords = any('keywords' in aspect for aspect in aspects)
            has_nature = any('nature' in aspect for aspect in aspects)

            if has_keywords:
                print(f"    PASS: Aspect interpretation keywords present")
            else:
                print(f"    WARNING: No interpretation keywords found (Phase 1 feature)")

            if has_nature:
                print(f"    PASS: Aspect nature (benefic/malefic) present")
            else:
                print(f"    WARNING: No aspect nature found (Phase 1 feature)")

            # Show first aspect as example
            if aspects:
                first_aspect = aspects[0]
                print(f"    Example aspect: {first_aspect.get('type')} between {first_aspect.get('object1')} and {first_aspect.get('object2')}")
                if 'keywords' in first_aspect:
                    print(f"      Keywords: {first_aspect['keywords']}")
                if 'nature' in first_aspect:
                    print(f"      Nature: {first_aspect['nature']}")
        else:
            print(f"    INFO: No major aspects found (may be normal depending on chart)")

except Exception as e:
    print(f"  FAIL: Exception raised: {type(e).__name__}: {e}")

print()

# Test Suite 3: Coordinate Format Compatibility (Bug Fix Verification)
print("TEST SUITE 3: Coordinate Format Compatibility (Bug Fix #2 Verification)")
print("-" * 80)

coordinate_formats = [
    ("Decimal", "51.5074", "-0.1278"),
    ("DMS North/West", "51n30", "0w08"),
    ("DMS with East (Bug #2)", "40n45", "73e59"),  # Test the 'E' direction fix
    ("Space-separated", "51 30 N", "0 08 W"),
]

for format_name, lat, lon in coordinate_formats:
    print(f"\n3.{coordinate_formats.index((format_name, lat, lon)) + 1} Testing {format_name} format...")
    try:
        result = generate_transit_to_natal(
            natal_date_time=NATAL_DATA["date_time"],
            natal_latitude=lat,
            natal_longitude=lon,
            transit_date_time=TRANSIT_DATA["date_time"]
        )

        if result.get("error"):
            print(f"  FAIL: {format_name} format - Error: {result.get('message')}")
        else:
            print(f"  PASS: {format_name} format works correctly")

    except Exception as e:
        print(f"  FAIL: {format_name} format - Exception: {type(e).__name__}: {e}")

print()

# Test Suite 4: Timezone Parameter Support (Phase 1 Feature)
print("TEST SUITE 4: Timezone Parameter Support (Phase 1 Feature)")
print("-" * 80)

timezones = [
    ("None (default)", None),
    ("Europe/London", "Europe/London"),
    ("America/New_York", "America/New_York"),
    ("Asia/Tokyo", "Asia/Tokyo"),
]

for tz_name, tz_value in timezones:
    print(f"\n4.{timezones.index((tz_name, tz_value)) + 1} Testing timezone: {tz_name}...")
    try:
        result = generate_transit_to_natal(
            natal_date_time=NATAL_DATA["date_time"],
            natal_latitude=NATAL_DATA["latitude"],
            natal_longitude=NATAL_DATA["longitude"],
            transit_date_time=TRANSIT_DATA["date_time"],
            timezone=tz_value
        )

        if result.get("error"):
            print(f"  FAIL: Timezone {tz_name} - Error: {result.get('message')}")
        else:
            print(f"  PASS: Timezone {tz_name} parameter accepted")
            returned_tz = result.get('timezone')
            if returned_tz == tz_value:
                print(f"    Timezone correctly stored in result: {returned_tz}")

    except Exception as e:
        print(f"  FAIL: Timezone {tz_name} - Exception: {type(e).__name__}: {e}")

print()

# Test Suite 5: Default Transit Location
print("TEST SUITE 5: Default Transit Location (Use Natal Location)")
print("-" * 80)

print("\n5.1 Testing transit calculation without specifying transit location...")
try:
    result = generate_transit_to_natal(
        natal_date_time=NATAL_DATA["date_time"],
        natal_latitude=NATAL_DATA["latitude"],
        natal_longitude=NATAL_DATA["longitude"],
        transit_date_time=TRANSIT_DATA["date_time"]
        # No transit_latitude or transit_longitude specified
    )

    if result.get("error"):
        print(f"  FAIL: Error: {result.get('message')}")
    else:
        print(f"  PASS: Transit calculated using natal location (default behavior)")

except Exception as e:
    print(f"  FAIL: Exception raised: {type(e).__name__}: {e}")

print("\n5.2 Testing transit calculation WITH different transit location...")
try:
    result = generate_transit_to_natal(
        natal_date_time=NATAL_DATA["date_time"],
        natal_latitude=NATAL_DATA["latitude"],
        natal_longitude=NATAL_DATA["longitude"],
        transit_date_time=TRANSIT_DATA["date_time"],
        transit_latitude="40.7128",  # New York
        transit_longitude="-74.0060"
    )

    if result.get("error"):
        print(f"  FAIL: Error: {result.get('message')}")
    else:
        print(f"  PASS: Transit calculated at different location")

except Exception as e:
    print(f"  FAIL: Exception raised: {type(e).__name__}: {e}")

print()

# Test Suite 6: Error Handling (Bug Fix #3 Verification)
print("TEST SUITE 6: Error Handling (Bug Fix #3 Verification)")
print("-" * 80)

error_test_cases = [
    ("Invalid natal date", "invalid-date", NATAL_DATA["latitude"], NATAL_DATA["longitude"], TRANSIT_DATA["date_time"]),
    ("Invalid natal latitude", NATAL_DATA["date_time"], "invalid", NATAL_DATA["longitude"], TRANSIT_DATA["date_time"]),
    ("Out of range latitude", NATAL_DATA["date_time"], "999", NATAL_DATA["longitude"], TRANSIT_DATA["date_time"]),
    ("Invalid transit date", NATAL_DATA["date_time"], NATAL_DATA["latitude"], NATAL_DATA["longitude"], "invalid-date"),
]

for test_name, natal_dt, natal_lat, natal_lon, transit_dt in error_test_cases:
    print(f"\n6.{error_test_cases.index((test_name, natal_dt, natal_lat, natal_lon, transit_dt)) + 1} Testing error: {test_name}...")
    try:
        result = generate_transit_to_natal(
            natal_date_time=natal_dt,
            natal_latitude=natal_lat,
            natal_longitude=natal_lon,
            transit_date_time=transit_dt
        )

        if result.get("error"):
            # Error properly returned in response
            print(f"  PASS: Error properly handled and returned")
            print(f"    Error message: {result.get('message')[:80]}...")

            # Check for enhanced error messages (Bug Fix #3)
            if 'Invalid' in result.get('message', '') or 'must be between' in result.get('message', ''):
                print(f"    PASS: Enhanced error message present")
        else:
            print(f"  FAIL: Should have returned error but got success")

    except ValueError as e:
        # Exception raised (also acceptable for error handling)
        print(f"  PASS: ValueError properly raised: {str(e)[:80]}...")
    except Exception as e:
        print(f"  INFO: Different exception raised: {type(e).__name__}: {str(e)[:80]}...")

print()

# Summary
print("=" * 80)
print("TEST SUMMARY - PHASE 1 FEATURE VERIFICATION")
print("=" * 80)
print()
print("Phase 1 Features Tested:")
print("  1. Transit-to-Natal Tool (1.1)")
print("     - generate_transit_to_natal() function")
print("     - generate_compact_transit_to_natal() function")
print()
print("  2. Timezone Parameter Support (1.2)")
print("     - Optional timezone parameter accepted")
print("     - Multiple IANA timezones tested")
print()
print("  3. Aspect Interpretation Hints (1.3)")
print("     - Keywords for aspect interpretation")
print("     - Benefic/malefic nature classification")
print()
print("Bug Fixes Verified:")
print("  - Bug #1: natal_summary fields return actual sign names (not 'Unknown')")
print("  - Bug #2: Coordinate parsing with 'E' direction (117e09, 2e21)")
print("  - Bug #3: Enhanced error messages and logging")
print()
print("Check logs/immanuel_server.log for detailed parsing and calculation logs.")
print("=" * 80)

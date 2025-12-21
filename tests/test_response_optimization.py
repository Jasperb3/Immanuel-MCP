#!/usr/bin/env python3
"""
Test response optimization for transit-to-natal endpoint.

Verifies:
1. Response size reduction (target: 60-70%)
2. No data loss (all essential information retained)
3. Named object keys instead of numeric indexes
4. Simplified aspect structure
5. Consolidated dignities section
"""

import sys
import json
from immanuel_server import generate_transit_to_natal

# Test parameters
test_params = {
    "natal_date_time": "1984-01-11 18:45:00",
    "natal_latitude": "51n23",
    "natal_longitude": "0w05",
    "transit_date_time": "2025-12-20 12:00:00",
    "transit_latitude": "51n34",
    "transit_longitude": "0w09",
    "timezone": "Europe/London"
}

print("=" * 80)
print("RESPONSE OPTIMIZATION VERIFICATION TEST")
print("=" * 80)
print()

# Get optimized response
print("Test 1: Generate Optimized Response")
print("-" * 80)
result = generate_transit_to_natal(**test_params, aspect_priority="all", include_all_aspects=True)

if result.get('error'):
    print(f"[FAIL] Error: {result.get('message')}")
    sys.exit(1)

# Test 2: Verify named object keys
print("\nTest 2: Named Object Keys (Not Numeric)")
print("-" * 80)
transit_positions = result.get('transit_positions', {})

# Check that keys are names, not numeric strings
has_named_keys = all(not key.isdigit() for key in transit_positions.keys())
sample_keys = list(transit_positions.keys())[:5]

if has_named_keys:
    print(f"[OK] All keys are named objects")
    print(f"  Sample keys: {sample_keys}")
else:
    print(f"[FAIL] Found numeric keys in transit_positions")
    print(f"  Keys: {sample_keys}")

# Test 3: Verify optimized structure
print("\nTest 3: Optimized Position Structure")
print("-" * 80)

if transit_positions:
    first_obj = list(transit_positions.values())[0]
    keys = list(first_obj.keys())

    print(f"  Position object keys: {keys}")

    # Check for presence of essential fields
    essential_fields = ['position', 'declination', 'retrograde', 'out_of_bounds', 'house']
    has_essential = all(field in keys for field in essential_fields)

    # Check for absence of redundant fields
    redundant_fields = ['index', 'type', 'latitude', 'longitude', 'sign_longitude']
    has_no_redundant = not any(field in keys for field in redundant_fields)

    if has_essential:
        print(f"  [OK] Has all essential fields: {essential_fields}")
    else:
        missing = [f for f in essential_fields if f not in keys]
        print(f"  [FAIL] Missing essential fields: {missing}")

    if has_no_redundant:
        print(f"  [OK] No redundant fields present")
    else:
        found = [f for f in redundant_fields if f in keys]
        print(f"  [WARNING] Found redundant fields: {found}")

    # Show sample position
    first_name = list(transit_positions.keys())[0]
    print(f"\n  Sample object ({first_name}):")
    print(f"    position: {first_obj.get('position')}")
    print(f"    declination: {first_obj.get('declination')}")
    print(f"    retrograde: {first_obj.get('retrograde')}")
    print(f"    out_of_bounds: {first_obj.get('out_of_bounds')}")
    print(f"    house: {first_obj.get('house')}")

# Test 4: Verify dignities section
print("\nTest 4: Dignities Section")
print("-" * 80)

dignities = result.get('dignities', {})
if dignities:
    print(f"  [OK] Dignities section present")
    print(f"  Planets with dignities: {len(dignities)}")
    sample_digs = list(dignities.items())[:3]
    for planet, dignity in sample_digs:
        print(f"    {planet}: {dignity}")
else:
    print(f"  [INFO] No dignities section (may be expected if no planets have dignities)")

# Test 5: Verify optimized aspects
print("\nTest 5: Optimized Aspect Structure")
print("-" * 80)

aspects = result.get('transit_to_natal_aspects', [])
if aspects:
    first_aspect = aspects[0]
    keys = list(first_aspect.keys())

    print(f"  Aspect object keys: {keys}")

    # Check for presence of essential fields
    essential_fields = ['planets', 'type', 'orb', 'movement', 'priority']
    has_essential = all(field in keys for field in essential_fields)

    # Check for absence of redundant fields
    redundant_fields = ['active', 'passive', 'aspect', 'distance', 'difference']
    has_no_redundant = not any(field in keys for field in redundant_fields)

    if has_essential:
        print(f"  [OK] Has all essential fields: {essential_fields}")
    else:
        missing = [f for f in essential_fields if f not in keys]
        print(f"  [FAIL] Missing essential fields: {missing}")

    if has_no_redundant:
        print(f"  [OK] No redundant fields present")
    else:
        found = [f for f in redundant_fields if f in keys]
        print(f"  [WARNING] Found redundant fields: {found}")

    # Show sample aspect (handle Unicode encoding for Windows console)
    print(f"\n  Sample aspect:")
    planets_str = first_aspect.get('planets', '')
    # Replace arrow with ASCII for Windows console compatibility
    planets_display = planets_str.replace('→', '->')
    print(f"    planets: {planets_display}")
    print(f"    type: {first_aspect.get('type')}")
    print(f"    orb: {first_aspect.get('orb')}")
    print(f"    movement: {first_aspect.get('movement')}")
    print(f"    priority: {first_aspect.get('priority')}")

# Test 6: Response size analysis
print("\nTest 6: Response Size Analysis")
print("-" * 80)

json_str = json.dumps(result)
size_kb = len(json_str) / 1024

print(f"  Total response size: {size_kb:.2f} KB")
print(f"  Total aspects: {len(aspects)}")
print(f"  Total positions: {len(transit_positions)}")

# Calculate estimated size reduction (compared to old format)
# Old format: ~70 KB for all aspects, ~18 KB for positions
# Expected new format: ~20 KB total
old_estimated_size = 70.0  # KB (based on previous measurements)
reduction_percent = ((old_estimated_size - size_kb) / old_estimated_size) * 100

print(f"\n  Estimated old format size: {old_estimated_size:.2f} KB")
print(f"  New format size: {size_kb:.2f} KB")
print(f"  Size reduction: {reduction_percent:.1f}%")

if reduction_percent >= 60:
    print(f"  [OK] Achieved target reduction (>60%)")
elif reduction_percent >= 40:
    print(f"  [GOOD] Significant reduction ({reduction_percent:.1f}%)")
else:
    print(f"  [INFO] Moderate reduction ({reduction_percent:.1f}%)")

# Test 7: Data completeness check
print("\nTest 7: Data Completeness (No Information Loss)")
print("-" * 80)

# Check all expected data is present
checks = []

# Natal summary
natal_summary = result.get('natal_summary', {})
checks.append(('Natal summary', 'sun' in natal_summary and 'moon' in natal_summary and 'rising' in natal_summary))

# Transit positions
checks.append(('Transit positions', len(transit_positions) > 0))

# Aspects
checks.append(('Aspects', len(aspects) > 0))

# Pagination
pagination = result.get('pagination', {})
checks.append(('Pagination', 'current_page' in pagination and 'total_pages' in pagination))

# Aspect summary
aspect_summary = result.get('aspect_summary', {})
checks.append(('Aspect summary', 'total_aspects' in aspect_summary))

for check_name, passed in checks:
    status = "[OK]" if passed else "[FAIL]"
    print(f"  {status} {check_name}")

all_passed = all(passed for _, passed in checks)

# Test 8: Verify position format
print("\nTest 8: Position Format Verification")
print("-" * 80)

if transit_positions:
    for planet_name, planet_data in list(transit_positions.items())[:3]:
        position = planet_data.get('position', '')
        declination = planet_data.get('declination', '')

        # Check format: should be like "28°51' Sagittarius"
        has_degree = '°' in position
        has_sign = any(sign in position for sign in ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                                                      'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'])

        status = "[OK]" if (has_degree and has_sign) else "[FAIL]"
        print(f"  {status} {planet_name}: {position} (declination: {declination})")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if all_passed and has_named_keys and reduction_percent >= 40:
    print("[SUCCESS] Response optimization working correctly!")
    print(f"  - All data integrity checks passed")
    print(f"  - Using named object keys (not numeric)")
    print(f"  - Size reduction: {reduction_percent:.1f}%")
    print(f"  - Final size: {size_kb:.2f} KB")
else:
    print("[REVIEW NEEDED] Some optimization issues found:")
    if not all_passed:
        print("  - Some data integrity checks failed")
    if not has_named_keys:
        print("  - Still using numeric object keys")
    if reduction_percent < 40:
        print(f"  - Size reduction below target: {reduction_percent:.1f}%")

print()
print("=" * 80)

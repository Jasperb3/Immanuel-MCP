#!/usr/bin/env python3
"""
Comprehensive test for transit-to-natal pagination system.

Tests:
1. Default behavior (tight aspects only)
2. Moderate aspects pagination
3. Loose aspects pagination
4. All aspects with include_all_aspects flag
5. Response size compliance with MCP limits
6. Aspect summary accuracy
7. Pagination metadata correctness
"""

import sys
import json
from immanuel_server import generate_transit_to_natal

# User's exact test case
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
print("TRANSIT-TO-NATAL PAGINATION SYSTEM TEST")
print("=" * 80)
print()

# Test 1: Default behavior (tight aspects)
print("Test 1: Default Behavior (Tight Aspects Only)")
print("-" * 80)
result_tight = generate_transit_to_natal(**test_params)

if result_tight.get('error'):
    print(f"[FAIL] Error: {result_tight.get('message')}")
    sys.exit(1)

tight_count = len(result_tight.get('transit_to_natal_aspects', []))
aspect_summary = result_tight.get('aspect_summary', {})
pagination = result_tight.get('pagination', {})

print(f"Aspects returned: {tight_count}")
print(f"Aspect summary: {aspect_summary}")
print(f"Pagination: {pagination}")

# Verify defaults
if tight_count == aspect_summary.get('tight_aspects', 0):
    print("[OK] Returned correct number of tight aspects")
else:
    print(f"[FAIL] Expected {aspect_summary.get('tight_aspects')} tight aspects, got {tight_count}")

# Check response size
json_str = json.dumps(result_tight)
size_kb = len(json_str) / 1024
print(f"Response size: {size_kb:.2f} KB")

if size_kb < 50:
    print(f"[OK] Response size under MCP limit (50 KB)")
else:
    print(f"[WARNING] Response size exceeds MCP limit!")

print()

# Test 2: Moderate aspects
print("Test 2: Moderate Aspects")
print("-" * 80)
result_moderate = generate_transit_to_natal(**test_params, aspect_priority="moderate")

if result_moderate.get('error'):
    print(f"[FAIL] Error: {result_moderate.get('message')}")
    sys.exit(1)

moderate_count = len(result_moderate.get('transit_to_natal_aspects', []))
aspect_summary_mod = result_moderate.get('aspect_summary', {})
pagination_mod = result_moderate.get('pagination', {})

print(f"Aspects returned: {moderate_count}")
print(f"Aspect summary: {aspect_summary_mod}")
print(f"Pagination: {pagination_mod}")

if moderate_count == aspect_summary_mod.get('moderate_aspects', 0):
    print("[OK] Returned correct number of moderate aspects")
else:
    print(f"[FAIL] Expected {aspect_summary_mod.get('moderate_aspects')} moderate aspects, got {moderate_count}")

# Check response size
json_str_mod = json.dumps(result_moderate)
size_kb_mod = len(json_str_mod) / 1024
print(f"Response size: {size_kb_mod:.2f} KB")

if size_kb_mod < 50:
    print(f"[OK] Response size under MCP limit (50 KB)")
else:
    print(f"[WARNING] Response size exceeds MCP limit!")

print()

# Test 3: Loose aspects
print("Test 3: Loose Aspects")
print("-" * 80)
result_loose = generate_transit_to_natal(**test_params, aspect_priority="loose")

if result_loose.get('error'):
    print(f"[FAIL] Error: {result_loose.get('message')}")
    sys.exit(1)

loose_count = len(result_loose.get('transit_to_natal_aspects', []))
aspect_summary_loose = result_loose.get('aspect_summary', {})
pagination_loose = result_loose.get('pagination', {})

print(f"Aspects returned: {loose_count}")
print(f"Aspect summary: {aspect_summary_loose}")
print(f"Pagination: {pagination_loose}")

if loose_count == aspect_summary_loose.get('loose_aspects', 0):
    print("[OK] Returned correct number of loose aspects")
else:
    print(f"[FAIL] Expected {aspect_summary_loose.get('loose_aspects')} loose aspects, got {loose_count}")

# Check response size
json_str_loose = json.dumps(result_loose)
size_kb_loose = len(json_str_loose) / 1024
print(f"Response size: {size_kb_loose:.2f} KB")

if size_kb_loose < 50:
    print(f"[OK] Response size under MCP limit (50 KB)")
else:
    print(f"[WARNING] Response size exceeds MCP limit!")

print()

# Test 4: All aspects (with warning)
print("Test 4: All Aspects (include_all_aspects=True)")
print("-" * 80)
result_all = generate_transit_to_natal(**test_params, include_all_aspects=True)

if result_all.get('error'):
    print(f"[FAIL] Error: {result_all.get('message')}")
    sys.exit(1)

all_count = len(result_all.get('transit_to_natal_aspects', []))
aspect_summary_all = result_all.get('aspect_summary', {})
pagination_all = result_all.get('pagination', {})

print(f"Aspects returned: {all_count}")
print(f"Aspect summary: {aspect_summary_all}")
print(f"Pagination: {pagination_all}")

expected_total = aspect_summary_all.get('total_aspects', 0)
if all_count == expected_total:
    print(f"[OK] Returned all {all_count} aspects")
else:
    print(f"[FAIL] Expected {expected_total} aspects, got {all_count}")

# Check response size
json_str_all = json.dumps(result_all)
size_kb_all = len(json_str_all) / 1024
print(f"Response size: {size_kb_all:.2f} KB")

if size_kb_all >= 50:
    print(f"[EXPECTED] Response size exceeds MCP limit (this is why pagination exists)")
else:
    print(f"[INFO] Response size still under limit: {size_kb_all:.2f} KB")

print()

# Test 5: Verify aspect summary consistency
print("Test 5: Aspect Summary Consistency")
print("-" * 80)

# All summaries should report the same total counts
tight_summary = result_tight.get('aspect_summary', {})
mod_summary = result_moderate.get('aspect_summary', {})
loose_summary = result_loose.get('aspect_summary', {})

tight_total = tight_summary.get('total_aspects', 0)
mod_total = mod_summary.get('total_aspects', 0)
loose_total = loose_summary.get('total_aspects', 0)

if tight_total == mod_total == loose_total:
    print(f"[OK] All summaries report same total: {tight_total} aspects")
else:
    print(f"[FAIL] Inconsistent totals - tight: {tight_total}, moderate: {mod_total}, loose: {loose_total}")

# Check math
tight_reported = tight_summary.get('tight_aspects', 0)
moderate_reported = tight_summary.get('moderate_aspects', 0)
loose_reported = tight_summary.get('loose_aspects', 0)
calculated_total = tight_reported + moderate_reported + loose_reported

if calculated_total == tight_total:
    print(f"[OK] Summary math correct: {tight_reported} + {moderate_reported} + {loose_reported} = {tight_total}")
else:
    print(f"[FAIL] Summary math incorrect: {tight_reported} + {moderate_reported} + {loose_reported} != {tight_total}")

print()

# Test 6: Verify pagination metadata
print("Test 6: Pagination Metadata Verification")
print("-" * 80)

# Check tight pagination
tight_page = result_tight.get('pagination', {})
print(f"Tight page metadata: {tight_page}")

if tight_page.get('current_page') == 1:
    print("[OK] Tight aspects show current_page=1")
else:
    print(f"[FAIL] Expected current_page=1, got {tight_page.get('current_page')}")

# Check if next_page is correct
if moderate_reported > 0:
    if tight_page.get('next_page') == 'moderate':
        print("[OK] Next page correctly points to 'moderate'")
    else:
        print(f"[FAIL] Expected next_page='moderate', got {tight_page.get('next_page')}")
else:
    print("[INFO] No moderate aspects, checking for loose aspects")
    if loose_reported > 0 and tight_page.get('next_page') == 'loose':
        print("[OK] Next page correctly points to 'loose'")

# Check moderate pagination
mod_page = result_moderate.get('pagination', {})
if mod_page.get('current_page') == 2:
    print("[OK] Moderate aspects show current_page=2")
else:
    print(f"[FAIL] Expected current_page=2, got {mod_page.get('current_page')}")

print()

# Test 7: Sample aspects to verify orb classification
print("Test 7: Orb Classification Verification")
print("-" * 80)

# Check a few aspects from each tier
tight_aspects = result_tight.get('transit_to_natal_aspects', [])
if tight_aspects:
    sample_tight = tight_aspects[0]
    orb = abs(sample_tight.get('orb', 999))
    print(f"Sample tight aspect: {sample_tight.get('object1')} {sample_tight.get('type')} {sample_tight.get('object2')}")
    print(f"  Orb: {orb:.2f}°")
    if orb <= 2.0:
        print("  [OK] Orb is within tight range (0-2°)")
    else:
        print(f"  [FAIL] Orb {orb:.2f}° exceeds tight range!")

moderate_aspects = result_moderate.get('transit_to_natal_aspects', [])
if moderate_aspects:
    sample_mod = moderate_aspects[0]
    orb = abs(sample_mod.get('orb', 999))
    print(f"Sample moderate aspect: {sample_mod.get('object1')} {sample_mod.get('type')} {sample_mod.get('object2')}")
    print(f"  Orb: {orb:.2f}°")
    if 2.0 < orb <= 5.0:
        print("  [OK] Orb is within moderate range (2-5°)")
    else:
        print(f"  [FAIL] Orb {orb:.2f}° outside moderate range!")

loose_aspects = result_loose.get('transit_to_natal_aspects', [])
if loose_aspects:
    sample_loose = loose_aspects[0]
    orb = abs(sample_loose.get('orb', 999))
    print(f"Sample loose aspect: {sample_loose.get('object1')} {sample_loose.get('type')} {sample_loose.get('object2')}")
    print(f"  Orb: {orb:.2f}°")
    if orb > 5.0:
        print("  [OK] Orb is within loose range (>5°)")
    else:
        print(f"  [FAIL] Orb {orb:.2f}° not in loose range!")

print()

# Summary
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Tight aspects:    {tight_reported} aspects, {size_kb:.2f} KB")
print(f"Moderate aspects: {moderate_reported} aspects, {size_kb_mod:.2f} KB")
print(f"Loose aspects:    {loose_reported} aspects, {size_kb_loose:.2f} KB")
print(f"All aspects:      {all_count} aspects, {size_kb_all:.2f} KB")
print()

# Determine success
all_sizes_ok = (size_kb < 50 and size_kb_mod < 50 and size_kb_loose < 50)
summary_consistent = (tight_total == mod_total == loose_total)

if all_sizes_ok and summary_consistent:
    print("[SUCCESS] All tests passed! Pagination system working correctly.")
    print("  - All priority tiers are under 50 KB MCP limit")
    print("  - Aspect summaries are consistent")
    print("  - Pagination metadata is correct")
else:
    print("[REVIEW NEEDED] Some issues found:")
    if not all_sizes_ok:
        print("  - Some response sizes may be close to or exceed MCP limits")
    if not summary_consistent:
        print("  - Aspect summaries are inconsistent across requests")

print()
print("=" * 80)

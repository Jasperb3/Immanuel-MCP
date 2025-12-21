#!/usr/bin/env python3
"""Test for JSON compatibility issues in full endpoint response."""

from immanuel_server import generate_transit_to_natal
import json
import sys

test_params = {
    "natal_date_time": "1984-01-11 18:45:00",
    "natal_latitude": "51n23",
    "natal_longitude": "0w05",
    "transit_date_time": "2025-12-20 12:00:00",
    "transit_latitude": "51n34",
    "transit_longitude": "0w09",
    "timezone": "Europe/London"
}

print("Testing Full Endpoint JSON Compatibility")
print("=" * 80)

result = generate_transit_to_natal(**test_params)

# Test 1: Basic JSON serializability
print("\nTest 1: Basic JSON Serialization")
try:
    json_str = json.dumps(result)
    print(f"  [OK] Serializes to JSON: {len(json_str) / 1024:.2f} KB")
except Exception as e:
    print(f"  [FAIL] Cannot serialize: {e}")
    sys.exit(1)

# Test 2: Can we deserialize and re-serialize?
print("\nTest 2: Round-trip Serialization")
try:
    parsed = json.loads(json_str)
    json_str2 = json.dumps(parsed)
    print(f"  [OK] Round-trip successful")
except Exception as e:
    print(f"  [FAIL] Round-trip failed: {e}")

# Test 3: Check for problematic nested structures
print("\nTest 3: Checking for Deeply Nested Structures")

def check_depth(obj, current_depth=0, max_depth=0, path="root"):
    if current_depth > max_depth:
        max_depth = current_depth

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}"
            max_depth = max(max_depth, check_depth(value, current_depth + 1, max_depth, new_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            max_depth = max(max_depth, check_depth(item, current_depth + 1, max_depth, new_path))

    return max_depth

max_nesting = check_depth(result)
print(f"  Maximum nesting depth: {max_nesting}")
if max_nesting > 10:
    print(f"  [WARNING] Very deep nesting (MCP might have limits)")
else:
    print(f"  [OK] Nesting depth is reasonable")

# Test 4: Check for NaN or Infinity values
print("\nTest 4: Checking for NaN/Infinity Values")

def find_bad_numbers(obj, path="root"):
    bad_values = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}"
            bad_values.extend(find_bad_numbers(value, new_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            bad_values.extend(find_bad_numbers(item, new_path))
    elif isinstance(obj, float):
        import math
        if math.isnan(obj) or math.isinf(obj):
            bad_values.append((path, obj))

    return bad_values

bad_nums = find_bad_numbers(result)
if bad_nums:
    print(f"  [WARNING] Found {len(bad_nums)} NaN/Infinity values:")
    for path, value in bad_nums[:5]:
        print(f"    {path}: {value}")
else:
    print(f"  [OK] No NaN or Infinity values")

# Test 5: Check response size
print("\nTest 5: Response Size Analysis")
size_bytes = sys.getsizeof(json_str)
size_kb = len(json_str) / 1024
print(f"  JSON string size: {size_kb:.2f} KB ({size_bytes} bytes)")
print(f"  Aspects count: {len(result.get('transit_to_natal_aspects', []))}")
print(f"  Objects count: {len(result.get('transit_positions', {}))} ")

if size_kb > 500:
    print(f"  [WARNING] Response is very large (might exceed MCP limits)")
elif size_kb > 100:
    print(f"  [CAUTION] Response is moderately large")
else:
    print(f"  [OK] Response size is reasonable")

# Test 6: Check for specific MCP-incompatible patterns
print("\nTest 6: Checking for MCP-Incompatible Patterns")

issues = []

# Check for dict keys that are numbers-as-strings
if result.get('transit_positions'):
    if any(key.isdigit() for key in result['transit_positions'].keys()):
        issues.append("Numeric string keys in transit_positions")

# Check aspects structure
aspects = result.get('transit_to_natal_aspects', [])
if aspects:
    if not all('object1' in asp and 'object2' in asp for asp in aspects):
        issues.append("Some aspects missing object1/object2 fields")

if issues:
    print(f"  [WARNING] Found {len(issues)} potential issues:")
    for issue in issues:
        print(f"    - {issue}")
else:
    print(f"  [OK] No obvious MCP-incompatible patterns")

print("\n" + "=" * 80)
print("SUMMARY:")
print("  If all tests passed, the issue is likely MCP-specific (size limits, timeouts, etc.)")
print("  If tests failed, there are data structure issues to fix")
print("=" * 80)

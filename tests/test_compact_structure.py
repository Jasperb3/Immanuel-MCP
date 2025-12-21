#!/usr/bin/env python3
"""Compare compact vs full endpoint structure."""

from immanuel_server import generate_compact_transit_to_natal, generate_transit_to_natal
import json

print("Comparing Compact vs Full Endpoint Structures")
print("=" * 80)

# Same test data
test_params = {
    "natal_date_time": "1984-01-11 18:45:00",
    "natal_latitude": "51n23",
    "natal_longitude": "0w05",
    "transit_date_time": "2025-12-20 12:00:00",
    "transit_latitude": "51n34",
    "transit_longitude": "0w09",
    "timezone": "Europe/London"
}

print("\nCalling COMPACT endpoint...")
compact = generate_compact_transit_to_natal(**test_params)

print("\nCalling FULL endpoint...")
full = generate_transit_to_natal(**test_params)

print("\n" + "=" * 80)
print("COMPACT transit_positions:")
print(f"  Type: {type(compact.get('transit_positions'))}")
if compact.get('transit_positions'):
    print(f"  Keys sample: {list(compact['transit_positions'].keys())[:3]}")
    first_obj = list(compact['transit_positions'].values())[0]
    print(f"  First object keys: {list(first_obj.keys())}")

print("\nFULL transit_positions:")
print(f"  Type: {type(full.get('transit_positions'))}")
if full.get('transit_positions'):
    print(f"  Keys sample: {list(full['transit_positions'].keys())[:3]}")
    first_obj = list(full['transit_positions'].values())[0]
    print(f"  First object keys: {list(first_obj.keys())[:5]}...")

print("\n" + "=" * 80)
print("COMPACT aspects:")
compact_aspects = compact.get('transit_to_natal_aspects', [])
print(f"  Type: {type(compact_aspects)}")
print(f"  Count: {len(compact_aspects)}")
if compact_aspects:
    print(f"  First aspect keys: {list(compact_aspects[0].keys())}")

print("\nFULL aspects:")
full_aspects = full.get('transit_to_natal_aspects', [])
print(f"  Type: {type(full_aspects)}")
print(f"  Count: {len(full_aspects)}")
if full_aspects:
    print(f"  First aspect keys: {list(full_aspects[0].keys())[:5]}...")

# Test serialization size
print("\n" + "=" * 80)
compact_json = json.dumps(compact)
full_json = json.dumps(full)

print("JSON Sizes:")
print(f"  Compact: {len(compact_json) / 1024:.2f} KB")
print(f"  Full:    {len(full_json) / 1024:.2f} KB")

# Check for numeric string keys
has_numeric_keys_compact = any(key.isdigit() for key in compact.get('transit_positions', {}).keys())
has_numeric_keys_full = any(key.isdigit() for key in full.get('transit_positions', {}).keys())

print("\nNumeric String Keys in transit_positions:")
print(f"  Compact: {'YES - PROBLEM!' if has_numeric_keys_compact else 'No'}")
print(f"  Full:    {'YES - PROBLEM!' if has_numeric_keys_full else 'No'}")

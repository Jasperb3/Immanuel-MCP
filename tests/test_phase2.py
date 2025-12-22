#!/usr/bin/env python3
"""
Comprehensive Phase 2 Testing
- Test compact transit-to-natal function
- Test lifecycle events integration
"""

import sys
import json
sys.path.insert(0, '/mnt/c/Users/BJJ/Documents/MCP/astro-mcp')

from immanuel_server import generate_compact_transit_to_natal, generate_transit_to_natal

print("=" * 70)
print("PHASE 2 COMPREHENSIVE TESTING")
print("=" * 70)

# Test parameters - using someone in their Saturn Return age
test_params = {
    "natal_date_time": "1995-01-15 14:30:00",  # Age ~30 in 2025 (Saturn Return age)
    "natal_latitude": "51.5074",
    "natal_longitude": "-0.1278",
    "transit_date_time": "2025-12-22 10:00:00",
    "timezone": "Europe/London"
}

print("\n" + "=" * 70)
print("TEST 1: Compact Transit-to-Natal with Lifecycle Events")
print("=" * 70)

try:
    result = generate_compact_transit_to_natal(**test_params, include_lifecycle_events=True)
    
    if 'error' in result:
        print(f"\nERROR: {result['message']}")
    else:
        print("\nSUCCESS: Function executed")
        print(f"Result keys: {list(result.keys())}")
        
        # Check structure
        print(f"\nNatal Summary: {result.get('natal_summary', {})}")
        print(f"Transit Date: {result.get('transit_date')}")
        print(f"Transit Positions Count: {len(result.get('transit_positions', {}))}")
        print(f"Aspects Count: {len(result.get('transit_to_natal_aspects', []))}")
        
        # Check lifecycle events
        lifecycle_events = result.get('lifecycle_events')
        lifecycle_summary = result.get('lifecycle_summary')
        if lifecycle_events and lifecycle_summary:
            print("\n LIFECYCLE EVENTS DETECTED")
            print(f"  Age: {lifecycle_summary.get('current_age')}")
            stage = lifecycle_summary.get('current_stage', {}).get('stage_name')
            print(f"  Current Stage: {stage}")
            print(f"  Active Events: {lifecycle_summary.get('active_event_count')}")
            print(f"  Highest Significance: {lifecycle_summary.get('highest_significance')}")

            print(f"  Next Event: {lifecycle_summary.get('next_major_event')}")
            print(f"  Years Until Next: {lifecycle_summary.get('years_until_event')}")

            print(f"\n  Events Returned ({len(lifecycle_events)} total, showing first 3):")
            for event in lifecycle_events[:3]:
                print(f"    - {event.get('event_type')} ({event.get('status')})")
                print(f"      Significance: {event.get('significance')}, Orb: {event.get('orb')}")
        else:
            print("\n  WARNING: No lifecycle events detected")
        
        # Check response size
        json_str = json.dumps(result)
        size_bytes = len(json_str.encode('utf-8'))
        size_kb = size_bytes / 1024
        print(f"\n Response size: {size_bytes} bytes ({size_kb:.2f} KB)")
        
        if size_kb < 50:
            print(f"   PASS: Size under MCP 50 KB limit")
        else:
            print(f"   WARNING: Size exceeds MCP 50 KB limit!")
        
except Exception as e:
    print(f"\n EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("TEST 2: Full Transit-to-Natal with Lifecycle Events")
print("=" * 70)

try:
    result = generate_transit_to_natal(
        **test_params,
        aspect_priority="tight",
        include_lifecycle_events=True
    )
    
    if 'error' in result:
        print(f"\nERROR: {result['message']}")
    else:
        print("\nSUCCESS: Function executed")
        
        # Check lifecycle events
        lifecycle_events = result.get('lifecycle_events')
        lifecycle_summary = result.get('lifecycle_summary')
        if lifecycle_events and lifecycle_summary:
            print("\n LIFECYCLE EVENTS DETECTED")
            print(f"  Active Events: {lifecycle_summary.get('active_event_count')}")
            print(f"  Highest Significance: {lifecycle_summary.get('highest_significance')}")
        else:
            print("\n  WARNING: No lifecycle events in full version")
        
        # Check response size
        json_str = json.dumps(result)
        size_kb = len(json_str.encode('utf-8')) / 1024
        print(f"\n Response size: {size_kb:.2f} KB")
        
except Exception as e:
    print(f"\n EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("TEST 3: Compact Transit WITHOUT Lifecycle Events (backwards compatibility)")
print("=" * 70)

try:
    result = generate_compact_transit_to_natal(
        **test_params,
        include_lifecycle_events=False
    )
    
    if 'error' in result:
        print(f"\nERROR: {result['message']}")
    else:
        print("\nSUCCESS: Function executed")
        lifecycle_state = result.get('lifecycle_events')
        print(f"Lifecycle events value: {lifecycle_state}")
        if lifecycle_state is None:
            print("   PASS: Lifecycle events correctly excluded")
        else:
            print("   WARNING: Lifecycle events present when disabled")
        
except Exception as e:
    print(f"\n EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("PHASE 2 TESTING COMPLETE")
print("=" * 70)

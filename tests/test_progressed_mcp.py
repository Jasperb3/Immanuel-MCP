#!/usr/bin/env python3
"""Test progressed chart lifecycle events via MCP functions."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from immanuel_server import generate_compact_progressed_chart, generate_progressed_chart

print("=" * 80)
print("TEST: Progressed Chart Lifecycle Events (MCP Functions)")
print("=" * 80)
print()

# Test 1: Compact Progressed Chart
print("TEST 1: Compact Progressed Chart")
print("-" * 40)
try:
    result = generate_compact_progressed_chart(
        date_time="1990-01-15 12:00:00",
        latitude="51.5074",
        longitude="-0.1278",
        progression_date_time="2024-12-22 12:00:00"
    )

    lifecycle_events = result.get("lifecycle_events")
    lifecycle_summary = result.get("lifecycle_summary")

    if lifecycle_events is not None:
        print(f"[OK] lifecycle_events is populated")
        print(f"     Event count: {len(lifecycle_events)}")
        if len(lifecycle_events) > 0:
            print(f"\n     First 3 events:")
            for i, event in enumerate(lifecycle_events[:3], 1):
                print(f"       {i}. {event.get('event_type')} - {event.get('exact_date')}")
    else:
        print(f"[FAIL] lifecycle_events is null")

    if lifecycle_summary is not None:
        print(f"[OK] lifecycle_summary is populated")
        print(f"     Current age: {lifecycle_summary.get('current_age')}")
        print(f"     Next event: {lifecycle_summary.get('next_major_event')}")
    else:
        print(f"[FAIL] lifecycle_summary is null")

except Exception as e:
    print(f"[FAIL] Compact progressed test error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: Full Progressed Chart
print("TEST 2: Full Progressed Chart")
print("-" * 40)
try:
    result = generate_progressed_chart(
        date_time="1990-01-15 12:00:00",
        latitude="51.5074",
        longitude="-0.1278",
        progression_date_time="2024-12-22 12:00:00"
    )

    lifecycle_events = result.get("lifecycle_events")
    lifecycle_summary = result.get("lifecycle_summary")

    if lifecycle_events is not None:
        print(f"[OK] lifecycle_events is populated")
        print(f"     Event count: {len(lifecycle_events)}")
        if len(lifecycle_events) > 0:
            print(f"\n     First 3 events:")
            for i, event in enumerate(lifecycle_events[:3], 1):
                print(f"       {i}. {event.get('event_type')} - {event.get('exact_date')}")
    else:
        print(f"[FAIL] lifecycle_events is null")

    if lifecycle_summary is not None:
        print(f"[OK] lifecycle_summary is populated")
        print(f"     Current age: {lifecycle_summary.get('current_age')}")
        print(f"     Next event: {lifecycle_summary.get('next_major_event')}")
    else:
        print(f"[FAIL] lifecycle_summary is null")

except Exception as e:
    print(f"[FAIL] Full progressed test error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Tests Complete")
print("=" * 80)

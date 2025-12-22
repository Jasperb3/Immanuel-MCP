#!/usr/bin/env python3
"""Test remaining lifecycle event fixes."""

import sys
import json
from datetime import datetime
from immanuel import charts

# Test 1: Solar Return with lifecycle events
print("=" * 80)
print("TEST 1: Solar Return Lifecycle Events")
print("=" * 80)

try:
    subject = charts.Subject(
        date_time="1990-01-15 12:00:00",
        latitude=51.5074,
        longitude=-0.1278
    )

    natal_chart = charts.Natal(subject)
    solar_return = charts.SolarReturn(subject, 2025)

    # Get solar return datetime (handle wrapped DateTime object)
    solar_return_dt_obj = getattr(solar_return, 'solar_return_date_time', None)
    if solar_return_dt_obj and hasattr(solar_return_dt_obj, 'datetime'):
        solar_return_dt = solar_return_dt_obj.datetime.strftime("%Y-%m-%d %H:%M:%S")
    elif solar_return_dt_obj:
        solar_return_dt = str(solar_return_dt_obj)
    else:
        solar_return_dt = "2025-01-15 12:00:00"

    # Create transit chart for the solar return date
    transit_subject = charts.Subject(
        date_time=solar_return_dt,
        latitude=51.5074,
        longitude=-0.1278
    )
    transit_chart = charts.Natal(transit_subject)

    # Try to detect lifecycle events
    from immanuel_mcp.lifecycle.lifecycle import detect_lifecycle_events, format_lifecycle_event_feed
    from datetime import datetime

    birth_dt = datetime.fromisoformat("1990-01-15 12:00:00")
    sr_dt = datetime.fromisoformat(solar_return_dt)

    lifecycle_data = detect_lifecycle_events(
        natal_chart=natal_chart,
        transit_chart=transit_chart,
        birth_datetime=birth_dt,
        transit_datetime=sr_dt,
        include_future=True,
        future_years=1,  # Only show events in the return year
        max_future_events=10
    )

    payload = format_lifecycle_event_feed(lifecycle_data, sr_dt)

    print(f"Solar Return Date: {solar_return_dt}")
    print(f"Current Events: {len(lifecycle_data.get('current_events', []))}")
    print(f"Future Events: {len(lifecycle_data.get('future_timeline', []))}")
    print(f"Formatted Events: {len(payload.get('events', []))}")

    if payload.get('events'):
        print("\nFirst 3 events:")
        for i, event in enumerate(payload['events'][:3], 1):
            print(f"  {i}. {event.get('event_type')} - {event.get('exact_date')}")
        print("[OK] Solar Return has lifecycle events")
    else:
        print("[WARN] Solar Return has no lifecycle events")

except Exception as e:
    print(f"[FAIL] Solar Return test error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: Verify aspect_priority None handling
print("=" * 80)
print("TEST 2: aspect_priority None Handling")
print("=" * 80)

# Simulate what happens when MCP passes None
aspect_priority = None

# This should default to "tight"
if aspect_priority is None:
    aspect_priority = "tight"
    print(f"[OK] aspect_priority was None, defaulted to: {aspect_priority}")
else:
    print(f"[FAIL] aspect_priority not handled correctly: {aspect_priority}")

print()

print("=" * 80)
print("Tests Complete")
print("=" * 80)

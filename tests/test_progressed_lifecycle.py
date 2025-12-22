#!/usr/bin/env python3
"""Test progressed chart lifecycle events."""

from datetime import datetime
from immanuel import charts
from immanuel_mcp.lifecycle.lifecycle import detect_lifecycle_events, format_lifecycle_event_feed

print("=" * 80)
print("TEST: Progressed Chart Lifecycle Events")
print("=" * 80)

try:
    # Birth chart
    subject = charts.Subject(
        date_time="1990-01-15 12:00:00",
        latitude=51.5074,
        longitude=-0.1278
    )
    natal_chart = charts.Natal(subject)

    # Progressed chart to 2025
    progression_date = "2025-01-15 12:00:00"
    progressed = charts.Progressed(subject, progression_date)

    # Create transit chart for the progression date
    transit_subject = charts.Subject(
        date_time=progression_date,
        latitude=51.5074,
        longitude=-0.1278
    )
    transit_chart = charts.Natal(transit_subject)

    # Detect lifecycle events
    birth_dt = datetime.fromisoformat("1990-01-15 12:00:00")
    progression_dt = datetime.fromisoformat(progression_date)

    lifecycle_data = detect_lifecycle_events(
        natal_chart=natal_chart,
        transit_chart=transit_chart,
        birth_datetime=birth_dt,
        transit_datetime=progression_dt,
        include_future=True,
        future_years=10,
        max_future_events=10
    )

    payload = format_lifecycle_event_feed(lifecycle_data, progression_dt)

    print(f"Progression Date: {progression_date}")
    print(f"Current Events: {len(lifecycle_data.get('current_events', []))}")
    print(f"Future Events: {len(lifecycle_data.get('future_timeline', []))}")
    print(f"Formatted Events: {len(payload.get('events', []))}")

    if payload.get('events'):
        print("\nFirst 3 events:")
        for i, event in enumerate(payload['events'][:3], 1):
            print(f"  {i}. {event.get('event_type')} - {event.get('exact_date')}")
        print("[OK] Progressed chart has lifecycle events")
    else:
        print("[WARN] Progressed chart has no lifecycle events")

except Exception as e:
    print(f"[FAIL] Progressed test error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Test Complete")
print("=" * 80)

#!/usr/bin/env python3
"""Simple test for progressed chart lifecycle events fix."""

from datetime import datetime
from immanuel import charts
from immanuel_mcp.lifecycle.lifecycle import detect_lifecycle_events, format_lifecycle_event_feed
from immanuel_server import parse_datetime_value

print("=" * 80)
print("TEST: Progressed Chart DateTime Extraction")
print("=" * 80)
print()

# Create a progressed chart
subject = charts.Subject(
    date_time="1990-01-15 12:00:00",
    latitude=51.5074,
    longitude=-0.1278
)
progressed = charts.Progressed(subject, "2024-12-22 12:00:00")

# Test the datetime extraction logic (same as in immanuel_server.py)
print("Testing DateTime extraction...")
progression_dt_obj = getattr(progressed, 'progression_date_time', None)
print(f"Raw object type: {type(progression_dt_obj)}")
print(f"Raw object value: {progression_dt_obj}")

if progression_dt_obj and hasattr(progression_dt_obj, 'datetime'):
    progression_dt_value = progression_dt_obj.datetime.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[OK] Extracted datetime string: {progression_dt_value}")
else:
    progression_dt_value = str(progression_dt_obj)
    print(f"[WARN] Fallback to str: {progression_dt_value}")

# Test that parse_datetime_value can handle it
print()
print("Testing parse_datetime_value...")
try:
    parsed_dt = parse_datetime_value(progression_dt_value)
    print(f"[OK] Successfully parsed: {parsed_dt}")
except Exception as e:
    print(f"[FAIL] Parse error: {e}")

print()
print("=" * 80)
print("Test Complete")
print("=" * 80)

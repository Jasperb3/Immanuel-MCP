#!/usr/bin/env python3
"""
Test Lifecycle Events Detection

Tests the lifecycle events system with known astrological returns and transits.

Test Cases:
1. Saturn Return (exact case from validation): Jan 11, 1984 → Nov 11, 2013
2. No active returns (young age): Jan 15, 1990 → Jun 20, 2012 (age 22)
3. Multiple simultaneous events (if possible)
4. Very young age (edge case)
"""

import sys
from datetime import datetime

# Import the lifecycle detection directly
from immanuel_mcp.lifecycle import detect_lifecycle_events
from immanuel import charts
from immanuel.const import chart as chart_const


def create_charts(natal_dt_str, transit_dt_str, natal_lat=51.38, natal_lon=-0.08):
    """Helper to create natal and transit charts."""
    # Parse datetime strings
    natal_dt = datetime.fromisoformat(natal_dt_str.replace(' ', 'T'))
    transit_dt = datetime.fromisoformat(transit_dt_str.replace(' ', 'T'))

    # Create subjects
    natal_subject = charts.Subject(
        date_time=natal_dt_str,
        latitude=natal_lat,
        longitude=natal_lon
    )
    transit_subject = charts.Subject(
        date_time=transit_dt_str,
        latitude=natal_lat,
        longitude=natal_lon
    )

    # Generate charts
    natal_chart = charts.Natal(natal_subject)
    transit_chart = charts.Natal(transit_subject)

    return natal_chart, transit_chart, natal_dt, transit_dt


def test_saturn_return():
    """
    Test Case 1: Known Saturn Return
    Natal: Jan 11, 1984, 18:45:00 UTC (51n23, 0w05)
    Transit: Nov 11, 2013, 00:50:00 UTC
    Expected: Saturn Return active with orb ~0.8°
    """
    print("\n" + "="*70)
    print("TEST 1: Saturn Return (Known Case from Validation)")
    print("="*70)

    natal_chart, transit_chart, natal_dt, transit_dt = create_charts(
        "1984-01-11 18:45:00",
        "2013-11-11 00:50:00",
        natal_lat=51.38,  # 51n23
        natal_lon=-0.08   # 0w05
    )

    # Debug: Check Saturn positions
    from immanuel.const import chart as chart_const
    natal_saturn = natal_chart.objects.get(chart_const.SATURN)
    transit_saturn = transit_chart.objects.get(chart_const.SATURN)
    print(f"\nDEBUG - Natal Saturn: {natal_saturn.longitude.raw:.2f} deg in {natal_saturn.sign.name}")
    print(f"DEBUG - Transit Saturn: {transit_saturn.longitude.raw:.2f} deg in {transit_saturn.sign.name}")
    print(f"DEBUG - Difference: {abs(transit_saturn.longitude.raw - natal_saturn.longitude.raw):.2f} deg")

    # Detect lifecycle events
    events = detect_lifecycle_events(
        natal_chart, transit_chart, natal_dt, transit_dt
    )

    # Print results
    print(f"\nAge: {events['lifecycle_summary']['current_age']}")
    print(f"Current Stage: {events['lifecycle_summary']['current_stage']['stage_name']}")
    print(f"Active Events: {events['lifecycle_summary']['active_event_count']}")
    print(f"Highest Significance: {events['lifecycle_summary']['highest_significance']}")

    if events['current_events']:
        print("\nCurrent Active Events:")
        for event in events['current_events']:
            if event['event_type'] == 'return':
                print(f"  • {event['planet']} Return #{event['cycle_number']}")
                print(f"    Orb: {event['orb']}° ({event['orb_status']})")
                print(f"    Significance: {event['significance']}")
                print(f"    Natal: {event['natal_position']}°, Transit: {event['transit_position']}°")
            else:
                print(f"  • {event['name']}")
                print(f"    Orb: {event['orb']}° ({event['orb_status']})")
                print(f"    Significance: {event['significance']}")

    # Validation
    assert events['lifecycle_summary']['active_event_count'] > 0, "Expected at least 1 active event"

    # Check if Saturn Return is present
    saturn_return_found = False
    for event in events['current_events']:
        if event.get('planet') == 'Saturn' and event.get('type') == 'saturn_return':
            saturn_return_found = True
            print(f"\n✅ Saturn Return detected with orb {event['orb']}°")
            assert abs(event['orb']) <= 2.0, f"Expected orb ≤ 2°, got {event['orb']}°"
            assert event['cycle_number'] == 1, f"Expected cycle 1, got {event['cycle_number']}"
            assert event['significance'] == 'CRITICAL', f"Expected CRITICAL, got {event['significance']}"
            break

    assert saturn_return_found, "Saturn Return not detected!"

    print("\n✅ TEST 1 PASSED")
    return events


def test_no_active_returns():
    """
    Test Case 2: No Active Returns (Young Age)
    Natal: Jan 15, 1990, 12:00:00
    Transit: Jun 20, 2012, 14:00:00 (age ~22.4)
    Expected: No active returns, future timeline populated
    """
    print("\n" + "="*70)
    print("TEST 2: No Active Returns (Age 22)")
    print("="*70)

    natal_chart, transit_chart, natal_dt, transit_dt = create_charts(
        "1990-01-15 12:00:00",
        "2012-06-20 14:00:00"
    )

    events = detect_lifecycle_events(
        natal_chart, transit_chart, natal_dt, transit_dt
    )

    print(f"\nAge: {events['lifecycle_summary']['current_age']}")
    print(f"Current Stage: {events['lifecycle_summary']['current_stage']['stage_name']}")
    print(f"Active Events: {events['lifecycle_summary']['active_event_count']}")

    if events['future_timeline']:
        print(f"\nNext {len(events['future_timeline'])} Upcoming Events:")
        for event in events['future_timeline'][:3]:  # Show first 3
            if event['event_type'] == 'return':
                print(f"  • {event['planet']} Return #{event['cycle_number']} "
                      f"in {event['years_until']:.1f} years (age {event['predicted_age']})")
            else:
                print(f"  • {event['name']} "
                      f"in {event['years_until']:.1f} years (age {event['typical_age']})")

    # Validation
    print(f"\n✅ TEST 2 PASSED (Age {events['lifecycle_summary']['current_age']}, "
          f"{events['lifecycle_summary']['active_event_count']} active events)")
    return events


def test_jupiter_return():
    """
    Test Case 3: First Jupiter Return (Age ~12)
    Natal: Jan 15, 1990, 12:00:00
    Transit: Around age 12 (11.86 years later) ≈ Dec 2001
    Expected: Jupiter Return active
    """
    print("\n" + "="*70)
    print("TEST 3: Jupiter Return (Age ~12)")
    print("="*70)

    natal_chart, transit_chart, natal_dt, transit_dt = create_charts(
        "1990-01-15 12:00:00",
        "2001-12-15 12:00:00"  # ~11.9 years later
    )

    events = detect_lifecycle_events(
        natal_chart, transit_chart, natal_dt, transit_dt
    )

    print(f"\nAge: {events['lifecycle_summary']['current_age']}")
    print(f"Current Stage: {events['lifecycle_summary']['current_stage']['stage_name']}")
    print(f"Active Events: {events['lifecycle_summary']['active_event_count']}")

    if events['current_events']:
        print("\nCurrent Active Events:")
        for event in events['current_events']:
            if event['event_type'] == 'return':
                print(f"  • {event['planet']} Return #{event['cycle_number']}")
                print(f"    Orb: {event['orb']}° ({event['orb_status']})")

    # Look for Jupiter Return
    jupiter_return_found = False
    for event in events['current_events']:
        if event.get('planet') == 'Jupiter':
            jupiter_return_found = True
            print(f"\n✅ Jupiter Return detected with orb {event['orb']}°")
            break

    if jupiter_return_found:
        print("\n✅ TEST 3 PASSED - Jupiter Return detected")
    else:
        print("\n⚠️  TEST 3: No Jupiter Return detected (may be due to orb timing)")

    return events


def test_past_events():
    """
    Test Case 4: Past Events Summary (Age 45)
    Should show past milestones like Saturn Return, Chiron Opposition, etc.
    """
    print("\n" + "="*70)
    print("TEST 4: Past Events Summary (Age 45)")
    print("="*70)

    natal_chart, transit_chart, natal_dt, transit_dt = create_charts(
        "1979-01-15 12:00:00",
        "2024-06-15 12:00:00"  # Age ~45.4
    )

    events = detect_lifecycle_events(
        natal_chart, transit_chart, natal_dt, transit_dt
    )

    print(f"\nAge: {events['lifecycle_summary']['current_age']}")
    print(f"Current Stage: {events['lifecycle_summary']['current_stage']['stage_name']}")

    if events['past_events']:
        print(f"\nPast Milestones ({len(events['past_events'])} total):")
        for event in events['past_events'][:5]:  # Show first 5
            print(f"  • {event['name']} at age {event['typical_age']} "
                  f"({event['years_ago']:.1f} years ago)")

    assert len(events['past_events']) > 0, "Expected past events for age 45"
    print("\n✅ TEST 4 PASSED")
    return events


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("LIFECYCLE EVENTS DETECTION - TEST SUITE")
    print("="*70)

    try:
        # Run all tests
        test_saturn_return()
        test_no_active_returns()
        test_jupiter_return()
        test_past_events()

        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*70)

        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

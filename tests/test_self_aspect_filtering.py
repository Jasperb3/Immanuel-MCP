#!/usr/bin/env python3
"""Test that self-aspects are filtered out of transit-to-natal results."""

from immanuel_server import (
    generate_transit_to_natal,
    generate_compact_transit_to_natal,
    normalize_aspects_to_list
)


def test_no_self_aspects_in_full_endpoint():
    """Verify full endpoint filters out self-aspects."""
    result = generate_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    assert result.get("error") is not True

    # Get all aspects (should already be a list after Task 1 fix)
    aspects = result.get("transit_to_natal_aspects", [])

    # Check for self-aspects (using 'active' and 'passive' fields)
    self_aspects = [
        asp for asp in aspects
        if asp.get('active') == asp.get('passive')
    ]

    assert len(self_aspects) == 0, f"Found {len(self_aspects)} self-aspects: {self_aspects}"
    print(f"PASS: Full endpoint - No self-aspects found in {len(aspects)} total aspects")


def test_no_self_aspects_in_compact_endpoint():
    """Verify compact endpoint filters out self-aspects."""
    result = generate_compact_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    assert result.get("error") is not True

    # Get aspects (compact returns list directly)
    aspects = result.get("transit_to_natal_aspects", [])

    # Check for self-aspects (using 'active' and 'passive' fields)
    self_aspects = [
        asp for asp in aspects
        if asp.get('active') == asp.get('passive')
    ]

    assert len(self_aspects) == 0, f"Found {len(self_aspects)} self-aspects: {self_aspects}"
    print(f"PASS: Compact endpoint - No self-aspects found in {len(aspects)} total aspects")


def test_self_aspect_filtering_with_all_object_types():
    """Test that self-aspect filtering works for planets, asteroids, points, nodes."""
    result = generate_compact_transit_to_natal(
        natal_date_time="2000-01-01 00:00:00",
        natal_latitude="0.0",
        natal_longitude="0.0",
        transit_date_time="2024-12-20 12:00:00"
    )

    assert result.get("error") is not True
    aspects = result.get("transit_to_natal_aspects", [])

    # Verify no object aspects itself (using 'active' and 'passive' fields)
    for aspect in aspects:
        active = aspect.get('active')
        passive = aspect.get('passive')
        assert active != passive, f"Self-aspect found: {active} {aspect.get('type')} {passive}"

    print(f"PASS: All {len(aspects)} aspects are between different objects")


if __name__ == "__main__":
    print("Testing self-aspect filtering...")
    test_no_self_aspects_in_full_endpoint()
    test_no_self_aspects_in_compact_endpoint()
    test_self_aspect_filtering_with_all_object_types()
    print("PASS: All self-aspect filtering tests passed!")

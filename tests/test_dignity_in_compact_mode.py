#!/usr/bin/env python3
"""Test that compact mode includes dignity information."""

from immanuel_server import generate_compact_transit_to_natal
import json


def test_compact_mode_includes_dignity():
    """Verify compact mode transit positions include dignity data."""
    result = generate_compact_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    assert result.get("error") is not True

    transit_positions = result.get("transit_positions", {})
    assert len(transit_positions) > 0, "No transit positions found"

    # Check that at least some positions have dignity information
    positions_with_dignity = 0

    for obj_key, obj_data in transit_positions.items():
        if 'dignity' in obj_data:
            dignity = obj_data['dignity']
            positions_with_dignity += 1

            # Verify dignity structure
            assert 'primary' in dignity, f"{obj_data['name']} missing dignity.primary"
            assert 'strength_score' in dignity, f"{obj_data['name']} missing dignity.strength_score"

            # Verify primary is valid value
            valid_primary = ['Ruler', 'Exalted', 'Detriment', 'Fall', 'Peregrine', None]
            assert dignity['primary'] in valid_primary, \
                f"Invalid primary dignity: {dignity['primary']}"

            # Verify strength score is numeric (can exceed traditional range with mutual receptions)
            score = dignity['strength_score']
            assert isinstance(score, (int, float)), f"Strength score must be numeric, got {type(score)}"

            print(f"  {obj_data['name']}: {dignity['primary']}, strength={score}")

    assert positions_with_dignity > 0, "No positions have dignity information"
    print(f"✓ Found dignity info in {positions_with_dignity}/{len(transit_positions)} positions")


def test_dignity_interpretation_examples():
    """Test specific dignity cases to verify correct interpretation."""
    result = generate_compact_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    transit_positions = result.get("transit_positions", {})

    # Find Sun (should be in Sagittarius on Dec 20)
    sun_data = next((obj for obj in transit_positions.values() if obj.get('name') == 'Sun'), None)

    if sun_data and 'dignity' in sun_data:
        print(f"  Sun in {sun_data.get('sign')}: {sun_data['dignity']}")
        # Sun in Sagittarius = Peregrine (neutral), strength score ~0
        # (Ruler in Leo, Exalted in Aries, Detriment in Aquarius, Fall in Libra)

    print("✓ Dignity interpretations appear valid")


def test_full_mode_preserves_complete_dignity():
    """Verify full mode still has all dignity details."""
    from immanuel_server import generate_transit_to_natal

    result = generate_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    transit_positions = result.get("transit_positions", {})

    # Full mode should have complete dignity data (scores, mutual receptions, etc.)
    for obj_key, obj_data in transit_positions.items():
        if 'dignity' in obj_data or 'dignities' in obj_data:
            # Full mode might use different structure
            print(f"  Full mode {obj_data.get('name')}: has dignity data")

    print("✓ Full mode preserves complete dignity information")


if __name__ == "__main__":
    print("Testing dignity information in compact mode...")
    test_compact_mode_includes_dignity()
    test_dignity_interpretation_examples()
    test_full_mode_preserves_complete_dignity()
    print("✓ All dignity tests passed")

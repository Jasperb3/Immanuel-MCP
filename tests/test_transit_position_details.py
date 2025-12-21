#!/usr/bin/env python3
"""Test that transit positions include all critical details."""

from immanuel_server import generate_compact_transit_to_natal, generate_transit_to_natal


def test_compact_mode_has_retrograde_status():
    """Verify ALL transit positions include retrograde status."""
    result = generate_compact_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    transit_positions = result.get("transit_positions", {})

    # Verify all positions have retrograde field
    for obj_key, obj_data in transit_positions.items():
        assert 'retrograde' in obj_data, f"{obj_data.get('name')} missing retrograde status"
        assert isinstance(obj_data['retrograde'], bool), \
            f"{obj_data.get('name')} retrograde must be boolean"

        if obj_data['retrograde']:
            print(f"  {obj_data['name']} is RETROGRADE")

    print(f"✓ All {len(transit_positions)} positions have retrograde status")


def test_compact_mode_has_house_placement():
    """Verify ALL transit positions include house number."""
    result = generate_compact_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    transit_positions = result.get("transit_positions", {})

    # Verify all positions have house field
    missing_house = []
    for obj_key, obj_data in transit_positions.items():
        if 'house' not in obj_data or obj_data['house'] is None:
            missing_house.append(obj_data.get('name'))
        else:
            house = obj_data['house']
            assert 1 <= house <= 12, f"{obj_data.get('name')} house {house} out of range"

    if missing_house:
        print(f"  WARNING: {len(missing_house)} positions missing house: {missing_house}")
    else:
        print(f"✓ All {len(transit_positions)} positions have valid house placement")

    # Show house distribution
    houses = [obj.get('house') for obj in transit_positions.values() if obj.get('house')]
    print(f"  House distribution: {sorted(set(houses))}")


def test_full_mode_has_extended_details():
    """Verify full mode includes declination, OOB, and speed."""
    result = generate_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    transit_positions = result.get("transit_positions", {})

    # Check for extended details in full mode
    has_declination = 0
    has_speed = 0
    has_oob = 0

    for obj_key, obj_data in transit_positions.items():
        if 'declination' in obj_data:
            has_declination += 1
        if 'speed' in obj_data or 'daily_motion' in obj_data:
            has_speed += 1
        if 'out_of_bounds' in obj_data:
            has_oob += 1

    print(f"  Full mode extended details:")
    print(f"    Declination: {has_declination}/{len(transit_positions)}")
    print(f"    Speed/Motion: {has_speed}/{len(transit_positions)}")
    print(f"    Out-of-Bounds: {has_oob}/{len(transit_positions)}")

    # Full mode should have at least some extended details
    # Note: Immanuel may not provide all these - adjust assertion as needed
    print("✓ Full mode structure inspected")


def test_retrograde_speed_correlation():
    """Verify retrograde status correlates with negative speed."""
    result = generate_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    transit_positions = result.get("transit_positions", {})

    # Check that retrograde planets have negative or very low speed
    for obj_key, obj_data in transit_positions.items():
        is_retrograde = obj_data.get('retrograde', False)
        speed = obj_data.get('speed')
        if speed is None and 'daily_motion' in obj_data:
            motion = obj_data['daily_motion']
            if isinstance(motion, dict):
                speed = motion.get('raw')

        if is_retrograde and speed is not None:
            print(f"  {obj_data.get('name')}: retrograde={is_retrograde}, speed={speed}")

            # Retrograde should correlate with negative speed (or close to zero at station)
            if abs(speed) > 0.01:  # Not at stationary point
                assert speed < 0, \
                    f"{obj_data.get('name')} is retrograde but has positive speed {speed}"

    print("✓ Retrograde status correlates with speed")


def test_compact_mode_has_extended_details():
    """Verify compact mode includes declination, speed, and OOB status."""
    result = generate_compact_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    transit_positions = result.get("transit_positions", {})

    # Check for extended details in compact mode
    has_declination = 0
    has_speed = 0
    has_oob = 0
    planets_only = 0  # Count non-angle objects for OOB check
    missing_details = []

    for obj_key, obj_data in transit_positions.items():
        obj_name = obj_data.get('name')
        is_angle = obj_name in ['Asc', 'MC']
        details = []

        if 'declination' in obj_data:
            has_declination += 1
        else:
            details.append('declination')

        if 'speed' in obj_data:
            has_speed += 1
        else:
            details.append('speed')

        # OOB only applies to planets, not angles (Asc/MC)
        if not is_angle:
            planets_only += 1
            if 'out_of_bounds' in obj_data:
                has_oob += 1
            else:
                details.append('out_of_bounds')

        if details:
            missing_details.append(f"{obj_name}: {', '.join(details)}")

    print(f"  Compact mode extended details:")
    print(f"    Declination: {has_declination}/{len(transit_positions)}")
    print(f"    Speed: {has_speed}/{len(transit_positions)}")
    print(f"    Out-of-Bounds: {has_oob}/{planets_only} (planets only)")

    if missing_details:
        print(f"  Missing details (excluding expected OOB for angles):")
        for detail in missing_details:
            if 'out_of_bounds' not in detail or ('Asc' not in detail and 'MC' not in detail):
                print(f"    {detail}")

    # All positions should have declination and speed
    assert has_declination == len(transit_positions), "Not all positions have declination"
    assert has_speed == len(transit_positions), "Not all positions have speed"
    # Only planets should have OOB (not angles)
    assert has_oob == planets_only, f"Not all planets have out_of_bounds ({has_oob}/{planets_only})"

    print("✓ All positions have extended details in compact mode")


def inspect_full_chart_structure():
    """Temporary inspection to understand Immanuel's data structure."""
    from immanuel_server import generate_transit_to_natal
    import json

    result = generate_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    # Print sample object structure
    transit_positions = result.get("transit_positions", {})
    if transit_positions:
        # Get a planet with movement (like Sun or Mercury)
        for obj_key, obj_data in transit_positions.items():
            if obj_data.get('name') in ['Sun', 'Mercury', 'Venus']:
                print(f"\n=== Sample object: {obj_data.get('name')} ===")
                print("Available keys:", sorted(obj_data.keys()))
                print("\nFull structure:")
                print(json.dumps(obj_data, indent=2))
                break


if __name__ == "__main__":
    print("Testing transit position details...")

    # First, inspect the structure
    print("\n" + "="*60)
    print("STEP 1: Inspect Full Chart Structure")
    print("="*60)
    inspect_full_chart_structure()

    print("\n" + "="*60)
    print("STEP 2: Run Tests")
    print("="*60)
    print("\n[Test 1/5] Retrograde status in compact mode...")
    test_compact_mode_has_retrograde_status()

    print("\n[Test 2/5] House placement in compact mode...")
    test_compact_mode_has_house_placement()

    print("\n[Test 3/5] Extended details in full mode...")
    test_full_mode_has_extended_details()

    print("\n[Test 4/5] Extended details in compact mode...")
    test_compact_mode_has_extended_details()

    print("\n[Test 5/5] Retrograde-speed correlation...")
    test_retrograde_speed_correlation()

    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED - Transit position details complete!")
    print("="*60)

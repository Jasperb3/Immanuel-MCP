#!/usr/bin/env python3
"""Test to reproduce and verify fix for silent failure in full transit endpoint."""

from immanuel_server import generate_transit_to_natal
import json
import sys


def test_full_transit_endpoint_returns_valid_data():
    """Test that full endpoint returns complete data structure without silent failure."""
    print("\n[TEST 1] Testing full endpoint returns valid data...")

    result = generate_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    # Should not be error response
    assert result.get("error") is not True, f"Endpoint returned error: {result.get('message')}"

    # Should have all required keys
    required_keys = ["natal_summary", "transit_date", "transit_positions", "transit_to_natal_aspects"]
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"

    # CRITICAL: Verify aspects are returned as a list (not dict) for MCP compatibility
    aspects = result.get("transit_to_natal_aspects")
    assert isinstance(aspects, list), f"transit_to_natal_aspects must be a list, got {type(aspects)}"
    print(f"  [OK] Aspects correctly returned as list with {len(aspects)} items")

    # Deep check for JSON serializability (MCP requirement)
    # This catches nested non-serializable objects that simple json.dumps might miss
    try:
        json_str = json.dumps(result)
        # Verify we can deserialize it back
        reparsed = json.loads(json_str)
        assert reparsed == result, "Result changed after JSON round-trip"
        print(f"  [OK] JSON serialization verified")
    except (TypeError, ValueError) as e:
        print(f"  [FAIL] Result not JSON serializable: {e}")
        print(f"  [DEBUG] Result type: {type(result)}")
        print(f"  [DEBUG] Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        # Check each top-level key
        for key, value in result.items():
            try:
                json.dumps(value)
                print(f"  [DEBUG] Key '{key}' is serializable")
            except Exception as ke:
                print(f"  [DEBUG] Key '{key}' is NOT serializable: {ke}")
                print(f"  [DEBUG] Value type: {type(value)}")
        raise

    # Transit positions should be populated
    assert len(result["transit_positions"]) > 0, "Transit positions empty"

    print(f"  [PASS] Full endpoint returns valid data with {len(result['transit_positions'])} transit positions")


def test_full_transit_endpoint_handles_large_response():
    """Test that full endpoint can handle large response payloads."""
    print("\n[TEST 2] Testing full endpoint handles large response...")

    result = generate_transit_to_natal(
        natal_date_time="1990-06-15 03:30:00",
        natal_latitude="51.5074",
        natal_longitude="-0.1278",
        transit_date_time="2024-12-20 18:00:00",
        timezone="Europe/London"
    )

    assert result.get("error") is not True, f"Endpoint returned error: {result.get('message')}"

    # Check response size
    json_str = json.dumps(result)
    size_kb = len(json_str) / 1024
    print(f"  [INFO] Response size: {size_kb:.2f} KB")

    # MCP should handle responses up to several MB, but warn if excessive
    if size_kb > 500:
        print(f"  [WARNING] Response size {size_kb:.2f} KB may be excessive for MCP")

    assert size_kb < 2048, "Response exceeds reasonable size limit (2MB)"
    print(f"  [PASS] Response size is within acceptable limits")


if __name__ == "__main__":
    print("Testing full transit endpoint for silent failures...")
    test_full_transit_endpoint_returns_valid_data()
    test_full_transit_endpoint_handles_large_response()
    print("[SUCCESS] All tests passed")

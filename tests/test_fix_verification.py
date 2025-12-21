#!/usr/bin/env python3
"""Verify the fix for the full transit-to-natal endpoint."""

from immanuel_server import generate_transit_to_natal
import json


def test_aspects_are_list_not_dict():
    """
    Verify that transit_to_natal_aspects is returned as a list, not a dict.

    This was the root cause of MCP silent failures. ToJSON serializer returns
    aspects as a dict with numeric string keys, which MCP transport cannot handle
    properly. Converting to list resolves the issue.
    """
    print("\n[FIX VERIFICATION] Testing aspects are returned as list...")

    result = generate_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )

    # Verify no error
    assert not result.get("error"), f"Function returned error: {result.get('message')}"

    # Get aspects
    aspects = result.get("transit_to_natal_aspects")

    # CRITICAL: Must be a list
    if isinstance(aspects, dict):
        print(f"  [FAIL] Aspects returned as dict - MCP will fail!")
        print(f"  [INFO] Dict keys: {list(aspects.keys())[:5]}")
        assert False, "transit_to_natal_aspects is dict, should be list"

    if isinstance(aspects, list):
        print(f"  [PASS] Aspects correctly returned as list")
        print(f"  [INFO] Aspect count: {len(aspects)}")

        # Verify each aspect is a dict with expected keys
        if aspects:
            first_aspect = aspects[0]
            print(f"  [INFO] Sample aspect keys: {list(first_aspect.keys())}")
            assert isinstance(first_aspect, dict), "Aspect items should be dicts"
    else:
        print(f"  [FAIL] Unexpected type for aspects: {type(aspects)}")
        assert False, f"Expected list, got {type(aspects)}"

    # Verify JSON serializability
    try:
        json_str = json.dumps(result)
        print(f"  [PASS] Result is JSON serializable ({len(json_str)/1024:.2f} KB)")
    except Exception as e:
        print(f"  [FAIL] Result not JSON serializable: {e}")
        raise

    print("\n[SUCCESS] Fix verified - endpoint should work in MCP now")


if __name__ == "__main__":
    test_aspects_are_list_not_dict()

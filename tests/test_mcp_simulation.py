#!/usr/bin/env python3
"""Simulate how FastMCP would process the full transit endpoint response."""

from immanuel_server import generate_transit_to_natal
import json
import time


def simulate_mcp_call():
    """Simulate FastMCP's handling of the tool call and response."""
    print("\n[MCP SIMULATION] Testing how FastMCP would process the response...")

    start_time = time.time()

    # 1. Call the tool (as MCP would)
    print("[STEP 1] Calling tool...")
    call_start = time.time()
    result = generate_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00"
    )
    call_duration = time.time() - call_start
    print(f"  Tool call took: {call_duration:.3f}s")

    # 2. Verify it's not an error
    if result.get("error"):
        print(f"  [ERROR] Tool returned error: {result.get('message')}")
        return

    # 3. FastMCP would serialize the result for transport
    print("[STEP 2] Serializing result for MCP transport...")
    serialize_start = time.time()
    try:
        # This is what FastMCP does internally
        json_result = json.dumps(result, ensure_ascii=False, indent=None)
        serialize_duration = time.time() - serialize_start
        print(f"  Serialization took: {serialize_duration:.3f}s")
        print(f"  JSON size: {len(json_result) / 1024:.2f} KB")
    except Exception as e:
        print(f"  [ERROR] Serialization failed: {e}")
        return

    # 4. MCP client would deserialize
    print("[STEP 3] Deserializing (as MCP client would)...")
    deserialize_start = time.time()
    try:
        reparsed = json.loads(json_result)
        deserialize_duration = time.time() - deserialize_start
        print(f"  Deserialization took: {deserialize_duration:.3f}s")
    except Exception as e:
        print(f"  [ERROR] Deserialization failed: {e}")
        return

    # 5. Verify data integrity
    print("[STEP 4] Verifying data integrity...")
    if reparsed == result:
        print("  [OK] Data integrity verified")
    else:
        print("  [WARNING] Data changed during round-trip")

    total_duration = time.time() - start_time
    print(f"\n[SUMMARY] Total MCP simulation took: {total_duration:.3f}s")

    if total_duration > 2.0:
        print("[WARNING] Operation took > 2s, may cause MCP timeout issues")
    else:
        print("[OK] Operation completed within acceptable time")


if __name__ == "__main__":
    simulate_mcp_call()

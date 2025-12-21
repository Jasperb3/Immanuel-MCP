#!/usr/bin/env python3
"""Test lunar return chart generation."""

import sys
import json

print("Testing Lunar Return Chart Generation...")
print()

# Test importing the lunar return module
try:
    from immanuel_mcp.charts import lunar_return
    print("[OK] Lunar return module imported successfully")
except Exception as e:
    print(f"[FAIL] Failed to import lunar return module: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test generating a lunar return chart
try:
    print("[TEST] Generating lunar return chart for January 2025...")
    print("       Birth: 1990-01-15 14:30:00 at 32.71, -117.15")

    result = lunar_return.generate_lunar_return_chart(
        date_time="1990-01-15 14:30:00",
        latitude="32.71",
        longitude="-117.15",
        return_year=2025,
        return_month=1,
        timezone="America/Los_Angeles"
    )

    if result.get('error'):
        print(f"[FAIL] Chart generation returned error: {result.get('message')}")
        sys.exit(1)

    # Check for lunar_return_info
    if 'lunar_return_info' not in result:
        print("[FAIL] Result missing lunar_return_info")
        sys.exit(1)

    info = result['lunar_return_info']
    print(f"[OK] Lunar return chart generated!")
    print(f"     Return date: {info['return_date']}")
    print(f"     Natal Moon longitude: {info['natal_moon_longitude']:.2f} degrees")

except Exception as e:
    print(f"[FAIL] Error generating lunar return chart: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test generating compact lunar return chart
try:
    print()
    print("[TEST] Generating compact lunar return chart...")

    result = lunar_return.generate_compact_lunar_return_chart(
        date_time="1990-01-15 14:30:00",
        latitude="32.71",
        longitude="-117.15",
        return_year=2025,
        return_month=1,
        timezone="America/Los_Angeles"
    )

    if result.get('error'):
        print(f"[FAIL] Compact chart generation returned error: {result.get('message')}")
        sys.exit(1)

    # Calculate response size
    result_json = json.dumps(result)
    size_kb = len(result_json) / 1024

    print(f"[OK] Compact lunar return chart generated!")
    print(f"     Response size: {size_kb:.2f} KB")

    if size_kb > 50:
        print(f"[WARN] Response size exceeds MCP limit (50 KB)")

except Exception as e:
    print(f"[FAIL] Error generating compact lunar return chart: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("[SUCCESS] All lunar return tests passed!")

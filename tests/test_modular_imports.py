#!/usr/bin/env python3
"""Test script to verify modular structure imports correctly."""

import sys

print("Testing immanuel_mcp package imports...")
print()

# Test package import
try:
    import immanuel_mcp
    print("[OK] Package import successful")
    print(f"     Version: {immanuel_mcp.__version__}")
except Exception as e:
    print(f"[FAIL] Package import failed: {e}")
    sys.exit(1)

# Test MCP server import
try:
    from immanuel_mcp import mcp
    print("[OK] MCP server import successful")
except Exception as e:
    print(f"[FAIL] MCP server import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test constants import
try:
    from immanuel_mcp import CELESTIAL_BODIES
    print(f"[OK] CELESTIAL_BODIES import successful ({len(CELESTIAL_BODIES)} bodies)")
except Exception as e:
    print(f"[FAIL] CELESTIAL_BODIES import failed: {e}")
    sys.exit(1)

# Test chart function imports (via legacy bridge)
try:
    from immanuel_mcp.charts._legacy_import import generate_natal_chart
    print("[OK] Chart function imports successful")
except Exception as e:
    print(f"[FAIL] Chart function imports failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("[SUCCESS] All modular structure imports working correctly!")

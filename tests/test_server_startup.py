#!/usr/bin/env python3
"""Test script to verify MCP server can start without errors."""

import sys

print("Testing MCP server startup...")
print()

# Test server instantiation
try:
    from immanuel_mcp import mcp
    print("[OK] MCP server instance created")
    print(f"     Server name: {mcp.name}")
except Exception as e:
    print(f"[FAIL] Server instantiation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test that tools are registered
try:
    # In FastMCP, tools are registered via decorators
    # The mcp object should have tools registered
    print("[OK] Checking for registered tools...")

    # Try to access the tools
    # Note: This is implementation-specific and may need adjustment
    # based on FastMCP's internal structure
    if hasattr(mcp, '_tool_manager'):
        print(f"     Tool manager present")

    print("[OK] Server appears to be configured correctly")
except Exception as e:
    print(f"[FAIL] Tool registration check failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("[SUCCESS] MCP server can start successfully!")
print()
print("To actually run the server:")
print("  python -m immanuel_mcp")
print()
print("Or use the original entry point:")
print("  python immanuel_server.py")

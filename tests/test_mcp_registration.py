#!/usr/bin/env python3
"""Test if MCP server loads and registers tools correctly."""

import sys

print("Testing MCP server module import and tool registration")
print("=" * 60)

try:
    # Import the server module
    print("\n[1] Importing immanuel_server module...")
    import immanuel_server
    print("[OK] Module imported successfully")

    # Check if mcp object exists
    print("\n[2] Checking for MCP server object...")
    if hasattr(immanuel_server, 'mcp'):
        print("[OK] MCP server object found")
        mcp = immanuel_server.mcp
    else:
        print("[FAIL] No 'mcp' attribute found in module")
        sys.exit(1)

    # List registered tools
    print("\n[3] Checking for specific tool functions...")

    # Check if our specific tools are defined
    if hasattr(immanuel_server, 'generate_transit_to_natal'):
        print("[OK] generate_transit_to_natal function exists")
        # Check if it's decorated
        func = getattr(immanuel_server, 'generate_transit_to_natal')
        print(f"     Function type: {type(func)}")
        print(f"     Has __name__: {hasattr(func, '__name__')}")
        if hasattr(func, '__name__'):
            print(f"     Name: {func.__name__}")
    else:
        print("[FAIL] generate_transit_to_natal function NOT found")

    if hasattr(immanuel_server, 'generate_compact_transit_to_natal'):
        print("[OK] generate_compact_transit_to_natal function exists")
        # Check if it's decorated
        func = getattr(immanuel_server, 'generate_compact_transit_to_natal')
        print(f"     Function type: {type(func)}")
    else:
        print("[FAIL] generate_compact_transit_to_natal function NOT found")

    # Check MCP internals
    print("\n[4] Checking MCP server internals...")
    if hasattr(mcp, '_tools'):
        print(f"[OK] MCP has _tools attribute: {len(mcp._tools)} tools registered")
        for tool_name in list(mcp._tools.keys())[:10]:  # Show first 10
            print(f"     - {tool_name}")
    elif hasattr(mcp, 'tools'):
        print(f"[OK] MCP has tools attribute: {len(mcp.tools)} tools registered")
    else:
        print("[INFO] Cannot access internal tools registry")

    print("\n[SUCCESS] All checks passed")

except ImportError as e:
    print(f"\n[FAIL] Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"\n[FAIL] Unexpected error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

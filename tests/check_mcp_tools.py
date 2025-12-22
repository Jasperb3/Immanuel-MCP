#!/usr/bin/env python3
"""Check which functions are registered as MCP tools"""

import sys
sys.path.insert(0, '/mnt/c/Users/BJJ/Documents/MCP/astro-mcp')

from immanuel_server import mcp

print("=" * 70)
print("MCP TOOL REGISTRATION CHECK")
print("=" * 70)

# Get all registered tools
try:
    # Access the mcp server's tools
    print("\nChecking MCP server object...")
    print(f"MCP type: {type(mcp)}")
    print(f"MCP attributes: {[a for a in dir(mcp) if not a.startswith('_')]}")
    
    # Try to list tools
    if hasattr(mcp, 'list_tools'):
        tools = mcp.list_tools()
        print(f"\nTotal tools registered: {len(tools)}")
        
        # Look for our transit functions
        transit_tools = [t for t in tools if 'transit' in t.get('name', '').lower()]
        print(f"\nTransit-related tools ({len(transit_tools)}):")
        for tool in transit_tools:
            print(f"  - {tool.get('name')}")
    
    # Check if generate_compact_transit_to_natal exists
    compact_transit_exists = any(
        'compact_transit_to_natal' in t.get('name', '') 
        for t in (mcp.list_tools() if hasattr(mcp, 'list_tools') else [])
    )
    print(f"\ngenerate_compact_transit_to_natal registered: {compact_transit_exists}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

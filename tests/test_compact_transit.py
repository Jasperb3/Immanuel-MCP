#!/usr/bin/env python3
"""Test the compact transit-to-natal function directly"""

import sys
import json
sys.path.insert(0, '/mnt/c/Users/BJJ/Documents/MCP/astro-mcp')

from immanuel_server import generate_compact_transit_to_natal

print("=" * 70)
print("TESTING generate_compact_transit_to_natal")
print("=" * 70)

try:
    result = generate_compact_transit_to_natal(
        natal_date_time="1990-05-15 14:30:00",
        natal_latitude="51.5074",
        natal_longitude="-0.1278",
        transit_date_time="2025-12-22 10:00:00",
        timezone="Europe/London"
    )
    
    if 'error' in result:
        print(f"\nERROR: {result['message']}")
        print(f"Type: {result['type']}")
    else:
        print(f"\nSUCCESS: Function executed")
        print(f"Result keys: {list(result.keys())}")
        
        # Check structure
        print(f"\nNatal Summary: {result.get('natal_summary', {})}")
        print(f"Transit Date: {result.get('transit_date')}")
        print(f"Transit Positions Count: {len(result.get('transit_positions', {}))}")
        print(f"Aspects Count: {len(result.get('transit_to_natal_aspects', []))}")
        
        # Check response size
        json_str = json.dumps(result)
        size_bytes = len(json_str.encode('utf-8'))
        size_kb = size_bytes / 1024
        print(f"\nResponse size: {size_bytes} bytes ({size_kb:.2f} KB)")
        
        # Check first aspect structure
        aspects = result.get('transit_to_natal_aspects', [])
        if aspects:
            print(f"\nFirst aspect structure:")
            print(f"Keys: {list(aspects[0].keys())}")
            print(f"Example: {json.dumps(aspects[0], indent=2)}")
            
except Exception as e:
    print(f"\nEXCEPTION: {e}")
    import traceback
    traceback.print_exc()

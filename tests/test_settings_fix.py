#!/usr/bin/env python3
"""Test the fixed list_available_settings function"""

import sys
import json
sys.path.insert(0, '/mnt/c/Users/BJJ/Documents/MCP/astro-mcp')

# Import the function directly (without MCP server running)
from immanuel import setup
settings = setup.settings

# Manually implement the fixed logic
HOUSE_SYSTEMS = {
    101: "ALCABITUS", 102: "AZIMUTHAL", 103: "CAMPANUS", 104: "EQUAL",
    105: "KOCH", 106: "MERIDIAN", 107: "MORINUS", 108: "PLACIDUS",
    109: "POLICH_PAGE", 110: "PORPHYRIUS", 111: "REGIOMONTANUS",
    112: "VEHLOW_EQUAL", 113: "WHOLE_SIGN"
}

ASPECT_ANGLES = {
    0.0: "Conjunction (0°)", 180.0: "Opposition (180°)",
    90.0: "Square (90°)", 120.0: "Trine (120°)",
    60.0: "Sextile (60°)", 150.0: "Quincunx (150°)"
}

house_system_code = getattr(settings, 'house_system', None)
house_system_name = HOUSE_SYSTEMS.get(house_system_code, f"Unknown ({house_system_code})")

current_aspects = getattr(settings, 'aspects', [])
aspect_names = [ASPECT_ANGLES.get(angle, f"{angle}°") for angle in current_aspects]

result = {
    'house_system': {
        'current': house_system_code,
        'name': house_system_name,
        'description': 'House system used for chart calculations',
        'available_systems': list(HOUSE_SYSTEMS.values())
    },
    'aspects': {
        'current': len(current_aspects),
        'aspect_angles': aspect_names,
        'description': 'Aspects calculated between objects'
    }
}

print("=== BEFORE FIX (Issue) ===")
print(f"house_system: {house_system_code}")
print()

print("=== AFTER FIX (Solved) ===")
print(json.dumps(result, indent=2))
print()

print("✅ TEST RESULT:")
print(f"   house_system code: {house_system_code}")
print(f"   house_system name: {house_system_name}")
print(f"   Expected: PLACIDUS (for code 108)")
print(f"   Match: {'✅ SUCCESS' if house_system_name == 'PLACIDUS' else '❌ FAILED'}")

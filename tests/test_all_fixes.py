#!/usr/bin/env python3
"""
Comprehensive Test Suite for All Bug Fixes
Tests issues #2, #3, and #4
"""

import sys
import json
from datetime import datetime
sys.path.insert(0, '/mnt/c/Users/BJJ/Documents/MCP/astro-mcp')

from immanuel_server import (
    generate_compact_progressed_chart,
    generate_compact_solar_return_chart,
    list_available_settings
)

print("=" * 70)
print("COMPREHENSIVE TEST SUITE FOR ALL BUG FIXES")
print("=" * 70)

# Test Issue #2: Duplicate Aspects in Progressed Charts
print("\n[TEST 1] Issue #2: Duplicate Aspects in Progressed Charts")
print("-" * 70)
try:
    result = generate_compact_progressed_chart(
        date_time="1990-05-15 14:30:00",
        latitude="51.5074",
        longitude="-0.1278",
        progression_date_time="2025-12-22 10:00:00",
        timezone="Europe/London",
        include_interpretations=False  # Don't need interpretations for this test
    )
    
    if 'error' in result:
        print(f"ERROR: {result['message']}")
    else:
        aspects = result.get('aspects', [])
        total_aspects = len(aspects)
        
        # Check for duplicates
        seen = set()
        duplicates = []
        for asp in aspects:
            key = tuple(sorted([asp['object1'], asp['object2']])) + (asp['type'],)
            if key in seen:
                duplicates.append(f"{asp['object1']}-{asp['object2']} ({asp['type']})")
            seen.add(key)
        
        print(f"Total aspects: {total_aspects}")
        print(f"Duplicate aspects found: {len(duplicates)}")
        if duplicates:
            print(f"Duplicates: {', '.join(duplicates[:5])}")
            print("FAILED: Duplicates still present")
        else:
            print("SUCCESS: No duplicates found")
            
except Exception as e:
    print(f"ERROR: {e}")

# Test Issue #3: Interpretations in Progressed Charts
print("\n[TEST 2] Issue #3: Interpretations in Progressed Charts")
print("-" * 70)
try:
    result = generate_compact_progressed_chart(
        date_time="1990-05-15 14:30:00",
        latitude="51.5074",
        longitude="-0.1278",
        progression_date_time="2025-12-22 10:00:00",
        timezone="Europe/London",
        include_interpretations=True
    )
    
    if 'error' in result:
        print(f"ERROR: {result['message']}")
    else:
        aspects = result.get('aspects', [])
        if not aspects:
            print("WARNING: No aspects found")
        else:
            first_aspect = aspects[0]
            has_keywords = 'keywords' in first_aspect
            has_nature = 'nature' in first_aspect
            has_interpretation = 'interpretation' in first_aspect
            
            print(f"First aspect keys: {list(first_aspect.keys())}")
            print(f"Has 'keywords': {has_keywords}")
            print(f"Has 'nature': {has_nature}")
            print(f"Has 'interpretation': {has_interpretation}")
            
            if has_keywords and has_nature and has_interpretation:
                print("SUCCESS: Interpretations added to progressed chart")
            else:
                print("FAILED: Missing interpretation fields")
                
except Exception as e:
    print(f"ERROR: {e}")

# Test Issue #3: Interpretations in Solar Return Charts
print("\n[TEST 3] Issue #3: Interpretations in Solar Return Charts")
print("-" * 70)
try:
    result = generate_compact_solar_return_chart(
        date_time="1990-05-15 14:30:00",
        latitude="51.5074",
        longitude="-0.1278",
        return_year=2025,
        timezone="Europe/London",
        include_interpretations=True
    )
    
    if 'error' in result:
        print(f"ERROR: {result['message']}")
    else:
        aspects = result.get('aspects', [])
        if not aspects:
            print("WARNING: No aspects found")
        else:
            first_aspect = aspects[0]
            has_keywords = 'keywords' in first_aspect
            has_nature = 'nature' in first_aspect
            has_interpretation = 'interpretation' in first_aspect
            
            print(f"First aspect keys: {list(first_aspect.keys())}")
            print(f"Has 'keywords': {has_keywords}")
            print(f"Has 'nature': {has_nature}")
            print(f"Has 'interpretation': {has_interpretation}")
            
            if has_keywords and has_nature and has_interpretation:
                print("SUCCESS: Interpretations added to solar return chart")
            else:
                print("FAILED: Missing interpretation fields")
                
except Exception as e:
    print(f"ERROR: {e}")

# Test Issue #4: Settings Readable Names
print("\n[TEST 4] Issue #4: Settings Readable Names")
print("-" * 70)
try:
    result = list_available_settings()
    
    if 'error' in result:
        print(f"ERROR: {result['message']}")
    else:
        settings = result.get('settings', {})
        house_system = settings.get('house_system', {})
        
        print(f"House system code: {house_system.get('current')}")
        print(f"House system name: {house_system.get('name')}")
        print(f"Has 'available_systems': {'available_systems' in house_system}")
        
        aspects = settings.get('aspects', {})
        print(f"Aspect angles: {aspects.get('aspect_angles', [])}")
        
        if house_system.get('name') and 'available_systems' in house_system:
            print("SUCCESS: Settings now show readable names")
        else:
            print("FAILED: Missing readable names")
            
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 70)
print("TEST SUITE COMPLETE")
print("=" * 70)

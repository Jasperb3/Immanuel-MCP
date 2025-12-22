#!/usr/bin/env python3
"""Check current Immanuel settings values"""

from immanuel import setup
settings = setup.settings

print("=== CURRENT SETTINGS ===")
print(f"house_system: {settings.house_system} (type: {type(settings.house_system).__name__})")
print(f"locale: {settings.locale}")
print(f"\nobjects ({len(settings.objects)} total):")
for i, obj in enumerate(settings.objects[:10], 1):
    print(f"  {i}. {obj} (type: {type(obj).__name__})")
if len(settings.objects) > 10:
    print(f"  ... and {len(settings.objects) - 10} more")
    
print(f"\naspects ({len(settings.aspects)} total):")
for i, asp in enumerate(settings.aspects[:10], 1):
    print(f"  {i}. {asp} (type: {type(asp).__name__})")
if len(settings.aspects) > 10:
    print(f"  ... and {len(settings.aspects) - 10} more")

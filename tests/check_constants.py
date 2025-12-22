#!/usr/bin/env python3
"""
Check Immanuel Constants
Quick script to see what the actual constant values are for house systems, etc.
"""

from immanuel.const import chart as chart_const
from immanuel.const import calc as calc_const

print("=== HOUSE SYSTEMS ===")
house_attrs = [attr for attr in dir(chart_const) if not attr.startswith('_')]
for attr in house_attrs:
    val = getattr(chart_const, attr, None)
    if isinstance(val, int) and 100 <= val <= 120:  # House systems are in this range
        print(f"{attr}: {val}")

print("\n=== ASPECTS ===")
aspect_attrs = [attr for attr in dir(calc_const) if not attr.startswith('_')]
for attr in aspect_attrs:
    val = getattr(calc_const, attr, None)
    if isinstance(val, int) and val < 50:  # Aspects are smaller numbers
        print(f"{attr}: {val}")

print("\n=== CELESTIAL OBJECTS (sample) ===")
object_attrs = [attr for attr in dir(chart_const) if not attr.startswith('_')]
for attr in object_attrs[:20]:  # Just show first 20
    val = getattr(chart_const, attr, None)
    if isinstance(val, int) and val < 100:
        print(f"{attr}: {val}")

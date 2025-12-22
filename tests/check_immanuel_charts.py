#!/usr/bin/env python3
"""Check available chart types in Immanuel library."""

from immanuel import charts

print("Available chart types in Immanuel:")
print()

chart_types = [attr for attr in dir(charts) if not attr.startswith('_') and attr[0].isupper()]
for chart_type in sorted(chart_types):
    print(f"  - {chart_type}")

print()
if 'LunarReturn' in chart_types:
    print("[OK] LunarReturn is available!")
else:
    print("[INFO] LunarReturn is NOT available - will need to implement custom logic")

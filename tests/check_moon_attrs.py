#!/usr/bin/env python3
"""Check Moon object attributes in Immanuel."""

from immanuel import charts

subject = charts.Subject('1990-01-15 14:30:00', 32.71, -117.15)
natal = charts.Natal(subject)
moon = natal.objects.get(4000002)

print("Moon object type:", type(moon))
print()

# Check longitude object
print("Longitude object:", moon.longitude)
print("Longitude type:", type(moon.longitude))
print()

# Check if longitude has numeric value
if hasattr(moon.longitude, '__dict__'):
    print("Longitude attributes:")
    for key, value in moon.longitude.__dict__.items():
        print(f"  {key}: {value}")
print()

# Try to get raw value
print("All Moon attributes (including private):")
for attr in sorted(dir(moon)):
    if 'lon' in attr.lower():
        try:
            value = getattr(moon, attr)
            print(f"  {attr}: {value} (type: {type(value)})")
        except Exception as e:
            print(f"  {attr}: Error - {e}")

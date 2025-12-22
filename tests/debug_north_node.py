#!/usr/bin/env python3
"""Debug North Node orb calculation."""

from datetime import datetime
from immanuel import charts
from immanuel.const import chart as chart_const

# Test case
birth_date = "1990-01-15 12:00:00"
analysis_date = "2024-12-22 12:00:00"
lat = 51.5074
lon = -0.1278

# Create charts
natal_subject = charts.Subject(
    date_time=birth_date,
    latitude=lat,
    longitude=lon
)
natal_chart = charts.Natal(natal_subject)

transit_subject = charts.Subject(
    date_time=analysis_date,
    latitude=lat,
    longitude=lon
)
transit_chart = charts.Natal(transit_subject)

# Try to access North Node
print("Checking North Node access...")
try:
    natal_node = natal_chart.objects.get(chart_const.NORTH_NODE)
    print(f"Natal North Node: {natal_node}")
    print(f"  Longitude: {natal_node.longitude}")
    print(f"  Longitude.raw: {natal_node.longitude.raw}")
except Exception as e:
    print(f"ERROR accessing natal North Node: {e}")
    import traceback
    traceback.print_exc()

print()

try:
    transit_node = transit_chart.objects.get(chart_const.NORTH_NODE)
    print(f"Transit North Node: {transit_node}")
    print(f"  Longitude: {transit_node.longitude}")
    print(f"  Longitude.raw: {transit_node.longitude.raw}")
except Exception as e:
    print(f"ERROR accessing transit North Node: {e}")
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3
"""Deep inspection of aspect structure."""

from immanuel_server import generate_transit_to_natal
import json


result = generate_transit_to_natal(
    natal_date_time="1984-01-11 18:45:00",
    natal_latitude="40.7128",
    natal_longitude="-74.0060",
    transit_date_time="2024-12-20 12:00:00"
)

aspects = result.get("transit_to_natal_aspects")

print(f"Type: {type(aspects)}")
print(f"Length: {len(aspects)}")

if aspects:
    first = aspects[0]
    print(f"\nFirst aspect:")
    print(json.dumps(first, indent=2))

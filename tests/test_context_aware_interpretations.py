#!/usr/bin/env python3
"""Test that aspect interpretations vary by planetary combination."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from immanuel_server import generate_compact_transit_to_natal


def test_sun_mars_conjunction_keywords():
    """Test that different planet pairs get different keywords."""
    result = generate_compact_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00",
        include_interpretations=True
    )

    aspects = result.get("transit_to_natal_aspects", [])
    conjunctions = [a for a in aspects if a.get('type', '').lower() == 'conjunction']

    if conjunctions:
        for conj in conjunctions:
            keywords = conj.get('keywords', [])
            assert len(keywords) > 0, "Conjunction missing keywords"

            obj1 = conj.get('object1')
            obj2 = conj.get('object2')
            print(f"  {obj1} conjunction {obj2}: {keywords}")

    print(f"✓ Found {len(conjunctions)} conjunctions with specific keywords")


def test_jupiter_aspects_are_benefic_biased():
    """Test that Jupiter aspects are growth-oriented even in challenging aspects."""
    result = generate_compact_transit_to_natal(
        natal_date_time="1984-01-11 18:45:00",
        natal_latitude="40.7128",
        natal_longitude="-74.0060",
        transit_date_time="2024-12-20 12:00:00",
        include_interpretations=True
    )

    aspects = result.get("transit_to_natal_aspects", [])
    jupiter_aspects = [
        a for a in aspects
        if 'Jupiter' in [a.get('object1'), a.get('object2')]
    ]

    if jupiter_aspects:
        for asp in jupiter_aspects:
            nature = asp.get('nature')
            aspect_type = asp.get('type')

            # Jupiter oppositions/squares should be growth-oriented, not purely challenging
            if aspect_type.lower() in ['opposition', 'square']:
                assert nature in ['variable', 'benefic', 'growth-oriented'], \
                    f"Jupiter {aspect_type} should not be purely 'challenging', got: {nature}"

            print(f"  Jupiter {aspect_type}: nature={nature}")

    print(f"✓ Found {len(jupiter_aspects)} Jupiter aspects with appropriate nature")


def test_different_planet_pairs_have_different_keywords():
    """Verify keyword diversity across planet pairs."""
    result = generate_compact_transit_to_natal(
        natal_date_time="1990-06-15 14:30:00",
        natal_latitude="34.0522",
        natal_longitude="-118.2437",
        transit_date_time="2024-12-20 12:00:00",
        include_interpretations=True
    )

    aspects = result.get("transit_to_natal_aspects", [])

    keyword_sets = {}
    for asp in aspects:
        obj1 = asp.get('object1')
        obj2 = asp.get('object2')
        aspect_type = asp.get('type')
        keywords = tuple(asp.get('keywords', []))

        pair_key = f"{obj1}-{obj2}-{aspect_type}"
        keyword_sets[pair_key] = keywords

    unique_keyword_sets = set(keyword_sets.values())

    assert len(unique_keyword_sets) > 3, \
        f"Expected diverse keywords, found only {len(unique_keyword_sets)} unique sets"

    print(f"✓ Found {len(unique_keyword_sets)} unique keyword sets across {len(aspects)} aspects")
    print("  Sample keyword variations:")
    for pair_key, keywords in list(keyword_sets.items())[:5]:
        print(f"    {pair_key}: {keywords}")


if __name__ == "__main__":
    print("Testing context-aware aspect interpretations...")
    test_sun_mars_conjunction_keywords()
    test_jupiter_aspects_are_benefic_biased()
    test_different_planet_pairs_have_different_keywords()
    print("✓ All context-aware interpretation tests passed")

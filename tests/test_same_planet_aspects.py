#!/usr/bin/env python3
"""
Same-planet cross-chart aspects are kept everywhere.

In a chart built against another chart, active == passive means the same
planet in both charts: transit Saturn conjunct natal Saturn (the Saturn
Return), the Uranus opposition, the Pluto square, Sun-Sun synastry. An
earlier change filtered these out as "self-aspects", so the most significant
transits vanished from transit-to-natal (always in the full tool, and in the
compact one whenever include_interpretations was on, its default). A single
chart never aspects an object to itself, so there is nothing to filter.
"""

import pytest
from immanuel.const import chart as chart_const

import immanuel_server

NATAL = ("1990-01-15 14:30:00", "32.71", "-117.15")
TZ = "America/Los_Angeles"
SATURN_RETURN = "2019-12-01 12:00:00"   # transit Saturn 0.7 deg from natal Saturn


def _same_planet(aspects):
    return {(a["active"], a["type"]) for a in aspects if a["active"] == a["passive"]}


@pytest.mark.parametrize("include_interpretations", [True, False])
def test_compact_transit_to_natal_keeps_the_saturn_return(include_interpretations):
    result = immanuel_server.generate_compact_transit_to_natal(
        *NATAL, SATURN_RETURN, timezone=TZ, include_interpretations=include_interpretations)
    assert result["status"] == "success", result.get("message")
    assert (chart_const.SATURN, "Conjunction") in _same_planet(result["transit_to_natal_aspects"])


def test_compact_results_do_not_depend_on_interpretations():
    pairs = {}
    for flag in (True, False):
        aspects = immanuel_server.generate_compact_transit_to_natal(
            *NATAL, SATURN_RETURN, timezone=TZ, include_interpretations=flag
        )["transit_to_natal_aspects"]
        pairs[flag] = sorted((a["active"], a["passive"], a["type"]) for a in aspects)
    assert pairs[True] == pairs[False]


def test_full_transit_to_natal_keeps_the_saturn_return():
    # Default tier ("tight", 0-2 deg): exactly where a 0.7 deg return belongs.
    result = immanuel_server.generate_transit_to_natal(*NATAL, SATURN_RETURN, timezone=TZ)
    assert result["status"] == "success", result.get("message")
    labels = {(a["planets"], a["type"]) for a in result["transit_to_natal_aspects"]}
    assert ("transit Saturn → natal Saturn", "Conjunction") in labels


@pytest.mark.parametrize("include_interpretations", [True, False])
def test_compact_synastry_keeps_same_planet_aspects(include_interpretations):
    # Two people born six months apart: Sun opposite Sun.
    result = immanuel_server.generate_compact_synastry_aspects(
        "1990-01-15 14:30:00", "32.71", "-117.15", "1990-07-15 14:30:00", "32.71", "-117.15",
        TZ, TZ, include_interpretations=include_interpretations)
    assert result["status"] == "success", result.get("message")
    assert (chart_const.SUN, "Opposition") in _same_planet(result["aspects"])

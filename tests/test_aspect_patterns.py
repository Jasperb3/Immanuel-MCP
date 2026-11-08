#!/usr/bin/env python3
"""
Aspect patterns are built from the planets and Chiron only, and never across
two charts.

immanuel's pattern search runs over every aspect in a chart, so angles and
points (Asc, MC, Part of Fortune, Lilith) became pattern vertices. Its
vertices are clusters of conjunct objects whose aspects are pooled, so the
patterns are recomputed from planet-only aspects rather than filtered after
the fact.

Charts built against another chart are a different problem: transit and
natal objects share indices (both Suns are 4000001), so the search merges
the two charts' objects into the same vertices. No tool output exposes those
patterns today; serialize_full_chart nulls them so none ever does.
"""

import json

import pytest
from immanuel import charts
from immanuel.const import chart as chart_const

import immanuel_server
from immanuel_mcp.charts import lunar_return
from immanuel_mcp.serializers import PATTERN_OBJECTS, serialize_full_chart
from immanuel_mcp.utils.subjects import create_subject

LONDON = ("1984-03-12 12:00:00", "51n30", "0w07")
LONDON_TZ = "Europe/London"
SAN_DIEGO = ("1984-01-01 12:00:00", "32.71", "-117.15")
SAN_DIEGO_TZ = "America/Los_Angeles"


def _vertices(patterns):
    return [set(vertex) for kind in patterns.values() for pattern in kind for vertex in pattern]


def _as_sets(pattern):
    return {frozenset(vertex) for vertex in pattern}


def test_pattern_objects_are_the_planets_and_chiron():
    assert PATTERN_OBJECTS == {
        chart_const.SUN, chart_const.MOON, chart_const.MERCURY, chart_const.VENUS,
        chart_const.MARS, chart_const.JUPITER, chart_const.SATURN, chart_const.URANUS,
        chart_const.NEPTUNE, chart_const.PLUTO, chart_const.CHIRON}


def test_natal_patterns_use_planets_only_and_keep_planet_patterns():
    result = immanuel_server.generate_natal_chart(*LONDON, timezone=LONDON_TZ)
    patterns = result["aspect_patterns"]
    assert all(vertex <= PATTERN_OBJECTS for vertex in _vertices(patterns)), patterns
    # immanuel's own T-square here was already all-planet: Saturn+Mars, Venus,
    # Chiron. It must survive the recomputation unchanged.
    assert {frozenset({chart_const.SATURN, chart_const.MARS}),
            frozenset({chart_const.VENUS}),
            frozenset({chart_const.CHIRON})} in [_as_sets(p) for p in patterns["t_square"]]
    # Every pattern type is still present as a key.
    assert set(patterns) == {"t_square", "grand_trine", "yod", "grand_cross", "kite",
                             "mystic_rectangle", "cradle", "grand_sextile", "grand_quintile"}


SINGLE_CHART_TOOLS = {
    "solar_return": lambda: immanuel_server.generate_solar_return_chart(
        *SAN_DIEGO, 2026, timezone=SAN_DIEGO_TZ),
    "progressed": lambda: immanuel_server.generate_progressed_chart(
        *SAN_DIEGO, "2026-11-08 12:00:00", timezone=SAN_DIEGO_TZ),
    "lunar_return": lambda: lunar_return.generate_lunar_return_chart(
        *SAN_DIEGO, 2026, 11, timezone=SAN_DIEGO_TZ),
    "composite": lambda: immanuel_server.generate_composite_chart(
        *SAN_DIEGO, *LONDON, SAN_DIEGO_TZ, LONDON_TZ),
    "transit": lambda: immanuel_server.generate_transit_chart("32.71", "-117.15"),
}


@pytest.mark.parametrize("tool", sorted(SINGLE_CHART_TOOLS))
def test_every_full_chart_tool_uses_planet_only_patterns(tool):
    result = SINGLE_CHART_TOOLS[tool]()
    assert result["status"] == "success", result.get("message")
    assert all(vertex <= PATTERN_OBJECTS for vertex in _vertices(result["aspect_patterns"]))


def test_charts_built_against_another_chart_get_no_patterns():
    natal = charts.Natal(create_subject(*SAN_DIEGO, SAN_DIEGO_TZ))
    transit = charts.Natal(create_subject("2026-11-08 12:00:00", "32.71", "-117.15", "UTC"),
                           aspects_to=natal)
    assert serialize_full_chart(transit)["aspect_patterns"] is None
    assert serialize_full_chart(natal)["aspect_patterns"] is not None


@pytest.mark.parametrize("build", [
    lambda: immanuel_server.generate_transit_to_natal(
        *SAN_DIEGO, "2026-11-08 12:00:00", timezone=SAN_DIEGO_TZ, aspect_priority="all"),
    lambda: immanuel_server.generate_synastry_aspects(
        *SAN_DIEGO, *LONDON, SAN_DIEGO_TZ, LONDON_TZ),
], ids=["transit_to_natal", "synastry"])
def test_cross_chart_outputs_carry_no_patterns(build):
    result = build()
    assert result["status"] == "success", result.get("message")
    assert "aspect_patterns" not in json.dumps(result)

#!/usr/bin/env python3
"""
Charts inside the polar circles.

immanuel hard-codes Placidus for the Part of Fortune Ascendant
(tools/part.py) and the diurnal check (tools/condition.py). Inside the polar
circles the Swiss Ephemeris falls back to Porphyry and pysweph raises that
warning as swisseph.Error, so every chart failed, Whole Sign included.
immanuel_mcp.compat.polar retries those calls with Porphyry. The Ascendant
and MC don't depend on the house system, so nothing else changes.
"""

import inspect

import pytest
import swisseph as swe
from immanuel import charts
from immanuel.tools import sweph

import immanuel_server
from immanuel_mcp.charts import lunar_return
from immanuel_mcp.compat import polar
from immanuel_mcp.utils.subjects import create_subject

TROMSO = ("1988-12-21 09:00:00", "69n39", "18e57")
TROMSO_TZ = "Europe/Oslo"
LAT, LON = 69.65, 18.95
ARCSEC = 1 / 3600
FALLBACK_NAME = "Porphyry (polar fallback from Placidus)"

TOOLS = {
    "natal": lambda **kw: immanuel_server.generate_natal_chart(*TROMSO, TROMSO_TZ, **kw),
    "compact_natal": lambda **kw: immanuel_server.generate_compact_natal_chart(*TROMSO, TROMSO_TZ, **kw),
    "summary": lambda **kw: immanuel_server.get_chart_summary(*TROMSO, TROMSO_TZ, **kw),
    "positions": lambda **kw: immanuel_server.get_planetary_positions(*TROMSO, TROMSO_TZ, **kw),
    "transit_to_natal": lambda **kw: immanuel_server.generate_transit_to_natal(
        *TROMSO, "2026-11-08 12:00:00", timezone=TROMSO_TZ, **kw),
    "compact_transit_to_natal": lambda **kw: immanuel_server.generate_compact_transit_to_natal(
        *TROMSO, "2026-11-08 12:00:00", timezone=TROMSO_TZ, **kw),
    "solar_return": lambda **kw: immanuel_server.generate_solar_return_chart(*TROMSO, 2026, TROMSO_TZ, **kw),
    "compact_solar_return": lambda **kw: immanuel_server.generate_compact_solar_return_chart(
        *TROMSO, 2026, TROMSO_TZ, **kw),
    "lunar_return": lambda **kw: lunar_return.generate_lunar_return_chart(*TROMSO, 2026, 11, TROMSO_TZ, **kw),
    "compact_lunar_return": lambda **kw: lunar_return.generate_compact_lunar_return_chart(
        *TROMSO, 2026, 11, TROMSO_TZ, **kw),
    "progressed": lambda **kw: immanuel_server.generate_progressed_chart(
        *TROMSO, "2026-11-08 12:00:00", TROMSO_TZ, **kw),
    "compact_progressed": lambda **kw: immanuel_server.generate_compact_progressed_chart(
        *TROMSO, "2026-11-08 12:00:00", TROMSO_TZ, **kw),
}


def _natal():
    return charts.Natal(create_subject(*TROMSO, TROMSO_TZ))


def _porphyry(chart):
    jd = chart._native.julian_date
    return swe.houses_ex2(jd, LAT, LON, b"O")


def _close(a, b):
    return abs(swe.difdeg2n(a, b)) < ARCSEC


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_every_chart_tool_succeeds_inside_the_polar_circle(tool):
    result = TOOLS[tool]()
    assert result.get("status") == "success", result.get("message")
    assert result["applied_settings"]["house_system"] == FALLBACK_NAME
    assert any("polar circle" in w for w in result["warnings"]), result.get("warnings")


def test_angles_match_the_swiss_ephemeris():
    chart = _natal()
    cusps, ascmc, _, _ = _porphyry(chart)
    assert _close(chart.objects[sweph_const("ASC")].longitude.raw, ascmc[0])
    assert _close(chart.objects[sweph_const("MC")].longitude.raw, ascmc[1])


def sweph_const(name):
    from immanuel.const import chart as chart_const
    return getattr(chart_const, name)


def test_default_placidus_gives_porphyry_cusps_and_a_warning():
    chart = _natal()
    cusps, _, _, _ = _porphyry(chart)
    houses = list(chart.houses.values())
    assert len(houses) == 12
    for house, cusp in zip(houses, cusps[1:]):  # pysweph: slot 0 is unused
        assert _close(house.longitude.raw, cusp)
    result = TOOLS["natal"]()
    assert result["applied_settings"]["house_system"] == FALLBACK_NAME
    assert len(result["warnings"]) == 1
    assert "Placidus" in result["warnings"][0] and "Porphyry" in result["warnings"][0]


def test_whole_sign_gets_whole_sign_and_no_warning():
    result = TOOLS["natal"](house_system="WHOLE_SIGN")
    assert result["status"] == "success", result.get("message")
    assert result["applied_settings"]["house_system"] == "Whole Sign"
    assert "warnings" not in result
    for house in result["houses"].values():
        assert house["longitude"]["raw"] % 30 == pytest.approx(0, abs=1e-9)


def test_the_shim_is_a_no_op_outside_the_polar_circle():
    jd = 2448026.958  # 1990-05-15 11:00 UT
    assert sweph.swe.houses_ex2(jd, 51.5, -0.12, b"P") == swe.houses_ex2(jd, 51.5, -0.12, b"P")
    result = immanuel_server.generate_natal_chart(
        "1990-05-15 12:00:00", "51n30", "0w07", "Europe/London")
    assert "warnings" not in result
    assert result["applied_settings"]["house_system"] == "Placidus"


def test_other_swisseph_errors_still_raise():
    def failing(*args):
        raise swe.Error("swisseph.houses_ex2: something else")
    with pytest.raises(swe.Error, match="something else"):
        polar._polar_safe(failing)(2448026.958, 51.5, -0.12, b"P")


def test_the_shim_matches_the_immanuel_it_was_written_for():
    """Fails if immanuel changes the calls the shim wraps."""
    assert polar.installed()
    assert sweph.swe is polar.PROXY
    source = inspect.getsource(sweph.angles_houses_vertex)
    assert "swe.houses_ex2(" in source and "swe.houses_armc_ex2(" in source
    assert list(inspect.signature(sweph.angles_houses_vertex).parameters) == [
        "lat", "house_system", "first_house_lon", "jd", "lon", "armc", "armc_obliquity"]
    assert sweph._SWE[sweph_const("PORPHYRIUS")] == b"O"

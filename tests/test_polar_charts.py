#!/usr/bin/env python3
"""
Charts inside the polar circles.

immanuel 1.6/1.7 hard-coded Placidus for the Part of Fortune Ascendant and
the diurnal check, so every polar chart failed, Whole Sign included. 1.8
uses Equal houses there (theriftlab/immanuel-python#32) and raises a
ValueError only when the chart's own system is Placidus or Koch, whose
houses the Swiss Ephemeris cannot cast there. immanuel_mcp.compat.polar
retries those with Porphyry, so the default (Placidus) still builds.
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


def _natal_without_shim(monkeypatch, house_system):
    monkeypatch.setattr(sweph, "swe", swe)
    config = charts.Config()
    config.house_system = house_system
    subject = charts.Subject(TROMSO[0], LAT, LON, timezone=TROMSO_TZ)
    return charts.Natal(subject, config=config)


def test_immanuel_builds_polar_whole_sign_without_the_shim(monkeypatch):
    """Fixed upstream in 1.8: no internal Placidus call any more."""
    natal = _natal_without_shim(monkeypatch, sweph_const("WHOLE_SIGN"))
    assert natal.diurnal is not None


@pytest.mark.parametrize("system", ["PLACIDUS", "KOCH"])
def test_immanuel_refuses_polar_placidus_and_koch_without_the_shim(monkeypatch, system):
    """Why the shim stays: 1.8 raises for these, and Placidus is the default."""
    with pytest.raises(ValueError, match="cannot be calculated at latitude"):
        _natal_without_shim(monkeypatch, sweph_const(system))


def test_the_shim_matches_the_immanuel_it_was_written_for():
    """Fails if immanuel changes the calls the shim wraps."""
    assert polar.installed()
    assert sweph.swe is polar.PROXY
    source = inspect.getsource(sweph.angles_houses_vertex)
    assert "swe.houses_ex2(" in source and "swe.houses_armc_ex2(" in source
    assert list(inspect.signature(sweph.angles_houses_vertex).parameters) == [
        "lat", "house_system", "first_house_lon", "jd", "lon", "armc", "armc_obliquity"]
    assert sweph._SWE[sweph_const("PORPHYRIUS")] == b"O"


# --- the top-level house_system names the cusps actually used (0.10.5) ------
# immanuel serialises the configured system, so a default chart at Tromsø
# read "house_system": "Placidus" beside Porphyry cusps, an applied_settings
# of "Porphyry (polar fallback from Placidus)" and a warning saying so. It
# now reads "Porphyrius", immanuel's own name for the system, which is what a
# chart asking for it reads and what house_system= accepts back.

TOP_LEVEL_TOOLS = ["natal", "progressed", "solar_return", "summary"]


@pytest.mark.parametrize("tool", TOP_LEVEL_TOOLS)
def test_a_polar_fallback_chart_names_porphyry_at_the_top_level(tool):
    result = TOOLS[tool]()
    assert result["house_system"] == "Porphyrius"
    assert result["applied_settings"]["house_system"] == FALLBACK_NAME


def test_only_the_compact_tools_lack_the_top_level_field():
    have = sorted(tool for tool in TOOLS if "house_system" in TOOLS[tool]())
    assert set(TOP_LEVEL_TOOLS) <= set(have), have
    for tool in have:
        assert TOOLS[tool]()["house_system"] == "Porphyrius", tool


@pytest.mark.parametrize("tool", TOP_LEVEL_TOOLS)
def test_a_polar_whole_sign_chart_keeps_its_name(tool):
    assert TOOLS[tool](house_system="WHOLE_SIGN")["house_system"] == "Whole Sign"


LONDON = ("1990-05-15 12:00:00", "51n30", "0w07")
LONDON_TOOLS = {
    "natal": lambda: immanuel_server.generate_natal_chart(*LONDON, "Europe/London"),
    "summary": lambda: immanuel_server.get_chart_summary(*LONDON, "Europe/London"),
    "solar_return": lambda: immanuel_server.generate_solar_return_chart(*LONDON, 2026, "Europe/London"),
    "progressed": lambda: immanuel_server.generate_progressed_chart(
        *LONDON, "2026-11-08 12:00:00", "Europe/London"),
}


@pytest.mark.parametrize("tool", sorted(LONDON_TOOLS))
def test_a_chart_outside_the_polar_circle_is_unchanged(tool):
    result = LONDON_TOOLS[tool]()
    assert result["house_system"] == "Placidus"
    assert result["applied_settings"]["house_system"] == "Placidus"
    assert "warnings" not in result


def test_a_return_relocated_out_of_the_polar_circle_keeps_its_own_name():
    # The Tromsø natal chart falls back within the same call, but the
    # return chart is cast in London, where Placidus works.
    result = immanuel_server.generate_solar_return_chart(
        *TROMSO, 2026, TROMSO_TZ, return_latitude="51n30", return_longitude="0w07")
    assert result["status"] == "success", result.get("message")
    assert result["house_system"] == "Placidus"


# --- reversed cusps (0.12.1) -------------------------------------------------
# At some moments inside a polar circle the Swiss Ephemeris returns
# Regiomontanus, Campanus and Polich Page cusps in reverse (clockwise) order,
# with the MC and IC swapped. immanuel's house lookup assumes zodiacal order:
# it raised KeyError('index'), which reached callers as the message "'index'",
# or (Polich Page) built a chart with the houses scrambled. Each is now a
# PolarHouseError naming the systems that work.

REVERSED = "2020-08-13 20:55:00"            # Regiomontanus / Campanus reversed
PP_SILENT = "1999-03-25 02:08:00"           # Polich Page reversed, used to build
REVERSED_PROGRESSED = "2019-02-19 07:00:00"  # progressed to 2026-11-12 reversed
REVERSED_SOLAR_RETURN = "2011-08-23 05:03:00"  # 2026 return reversed
REVERSED_SUGGESTION = "Use house_system='PORPHYRIUS', 'EQUAL' or 'WHOLE_SIGN' for this chart."


def _tromso_natal(when, **kw):
    return immanuel_server.generate_natal_chart(when, *TROMSO[1:], TROMSO_TZ, **kw)


def _assert_reversed_error(result, name):
    assert result["status"] == "error", result.get("applied_settings")
    assert result["type"] == "PolarHouseError"
    assert name in result["message"] and "reverse" in result["message"], result["message"]
    assert result["suggestion"] == REVERSED_SUGGESTION


@pytest.mark.parametrize("system,name,when", [
    ("REGIOMONTANUS", "Regiomontanus", REVERSED),
    ("CAMPANUS", "Campanus", REVERSED),
    ("POLICH_PAGE", "Polich Page", PP_SILENT),
])
def test_reversed_cusps_are_a_clear_error(system, name, when):
    _assert_reversed_error(_tromso_natal(when, house_system=system), name)


def test_reversed_cusps_on_the_armc_path_are_a_clear_error():
    result = immanuel_server.generate_progressed_chart(
        REVERSED_PROGRESSED, *TROMSO[1:], "2026-11-12 12:00:00", TROMSO_TZ,
        house_system="REGIOMONTANUS")
    _assert_reversed_error(result, "Regiomontanus")


def test_reversed_return_cusps_are_a_clear_error():
    result = immanuel_server.generate_solar_return_chart(
        REVERSED_SOLAR_RETURN, *TROMSO[1:], 2026, TROMSO_TZ, house_system="REGIOMONTANUS")
    _assert_reversed_error(result, "Regiomontanus")


@pytest.mark.parametrize("system", ["PORPHYRIUS", "EQUAL", "WHOLE_SIGN"])
def test_the_suggested_systems_work_at_a_reversed_moment(system):
    assert _tromso_natal(REVERSED, house_system=system)["status"] == "success"


def test_cusp_order_check():
    in_order = [0.0] + [30.0 * i for i in range(12)]
    assert not polar.cusps_reversed(in_order)
    assert polar.cusps_reversed([0.0] + [(360 - 30.0 * i) % 360 for i in range(12)])
    # Wrapping past 0 Aries is still zodiacal order.
    assert not polar.cusps_reversed([0.0] + [(300 + 30.0 * i) % 360 for i in range(12)])


@pytest.mark.parametrize("system", ["REGIOMONTANUS", "CAMPANUS", "POLICH_PAGE"])
def test_these_systems_still_work_outside_the_polar_circle(system):
    result = immanuel_server.generate_natal_chart(REVERSED, "51n30", "0w07", "Europe/London",
                                                  house_system=system)
    assert result["status"] == "success", result.get("message")

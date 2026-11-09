#!/usr/bin/env python3
"""
time_status (immanuel 1.7): charts for an approximate or unknown birth time.

Every tool that takes a birth time accepts time_status ("known", the default,
"approximate" or "unknown"; composite and synastry take one per person).
Without a known time immanuel omits houses, angles, the Vertex, the Parts,
sect and day/night triplicity rulers, and "unknown" recasts at local noon.
The responses say so: applied_settings.house_system is None with a
time_status key, and a warning names what is missing.
"""

import json

import pytest

import immanuel_server as S
from immanuel_mcp.charts import lunar_return as L

BIRTH = ("1990-01-15 14:30:00", "32.71", "-117.15", "America/Los_Angeles")
PARTNER = ("1985-07-04 06:15:00", "51n30", "0w07", "Europe/London")
POLAR = ("1988-12-21 09:00:00", "69n39", "18e57", "Europe/Oslo")
ANGLES_AND_POINTS = ("Asc", "Desc", "MC", "IC", "Vertex", "Part of Fortune", "Part of Spirit", "Part of Eros")
TRANSIT = "2026-11-08 12:00:00"


def _single(name, dt, la, lo, tz, **kw):
    calls = {
        "natal": lambda: S.generate_natal_chart(dt, la, lo, tz, **kw),
        "compact_natal": lambda: S.generate_compact_natal_chart(dt, la, lo, tz, **kw),
        "summary": lambda: S.get_chart_summary(dt, la, lo, tz, **kw),
        "positions": lambda: S.get_planetary_positions(dt, la, lo, tz, **kw),
        "solar_return": lambda: S.generate_solar_return_chart(dt, la, lo, 2026, tz, **kw),
        "compact_solar_return": lambda: S.generate_compact_solar_return_chart(dt, la, lo, 2026, tz, **kw),
        "lunar_return": lambda: L.generate_lunar_return_chart(dt, la, lo, 2026, 11, tz, **kw),
        "compact_lunar_return": lambda: L.generate_compact_lunar_return_chart(dt, la, lo, 2026, 11, tz, **kw),
        "progressed": lambda: S.generate_progressed_chart(dt, la, lo, TRANSIT, tz, **kw),
        "compact_progressed": lambda: S.generate_compact_progressed_chart(dt, la, lo, TRANSIT, tz, **kw),
        "transit_to_natal": lambda: S.generate_transit_to_natal(dt, la, lo, TRANSIT, timezone=tz, **kw),
        "compact_transit_to_natal": lambda: S.generate_compact_transit_to_natal(dt, la, lo, TRANSIT, timezone=tz, **kw),
    }
    return calls[name]()


SINGLE = ["natal", "compact_natal", "summary", "positions", "solar_return", "compact_solar_return",
          "lunar_return", "compact_lunar_return", "progressed", "compact_progressed"]
TTN = ["transit_to_natal", "compact_transit_to_natal"]


def _object_names(result):
    objects = result.get("objects") or {}
    return {o.get("name") for o in objects.values()} if isinstance(objects, dict) else set()


@pytest.mark.parametrize("status", ["unknown", "approximate"])
@pytest.mark.parametrize("tool", SINGLE)
def test_untimed_charts_omit_houses_and_say_so(tool, status):
    result = _single(tool, *BIRTH, time_status=status)
    assert result.get("status") == "success", result
    assert "houses" not in result
    assert not _object_names(result) & set(ANGLES_AND_POINTS), _object_names(result)
    assert result["applied_settings"]["house_system"] is None
    assert result["applied_settings"]["time_status"] == status
    assert any(w.startswith(f"Birth time {status}") for w in result["warnings"]), result.get("warnings")


@pytest.mark.parametrize("status", ["unknown", "approximate"])
@pytest.mark.parametrize("tool", TTN)
def test_transit_to_natal_applies_status_to_the_natal_chart_only(tool, status):
    result = _single(tool, *BIRTH, time_status=status)
    assert result.get("status") == "success", result
    summary = result["natal_summary"]
    assert summary.get("rising_sign", summary.get("rising", "absent")) is None
    aspects = result["transit_to_natal_aspects"]
    aspects = aspects if isinstance(aspects, list) else list(aspects.values())
    assert aspects
    natal = {a["natal_object"] if "natal_object" in a else a["planets"].split("natal ", 1)[1]
             for a in aspects}
    assert not natal & set(ANGLES_AND_POINTS), natal
    # The transit chart's own time is known: its houses are still cast.
    assert result["applied_settings"]["house_system"] == "Placidus"
    assert result["applied_settings"]["natal_time_status"] == status
    assert result["lifecycle_events"] is not None
    assert any(w.startswith(f"Birth time {status}") for w in result["warnings"])


@pytest.mark.parametrize("tool", ["summary", "positions", "compact_solar_return",
                                  "compact_lunar_return", "compact_transit_to_natal"])
def test_known_is_the_default(tool):
    assert _single(tool, *BIRTH, time_status="known") == _single(tool, *BIRTH)


def test_known_output_has_no_new_keys():
    result = S.generate_compact_natal_chart(*BIRTH)
    assert "moon_range" not in result and "warnings" not in result
    assert "time_status" not in result["applied_settings"]


def test_unknown_recasts_at_local_noon():
    result = S.generate_natal_chart(*BIRTH, time_status="unknown")
    assert result["native"]["date_time"]["datetime"].startswith("1990-01-15 12:00:00")
    assert result["native"]["date_time"]["time_status"] == "Unknown time"
    approx = S.generate_natal_chart(*BIRTH, time_status="approximate")
    assert approx["native"]["date_time"]["datetime"].startswith("1990-01-15 14:30:00")


@pytest.mark.parametrize("value", ["KNOWN", " Unknown ", 2, "3"])
def test_accepted_spellings(value):
    assert S.get_chart_summary(*BIRTH, time_status=value)["status"] == "success"


@pytest.mark.parametrize("value", ["noon", "", 0, 4, True])
def test_invalid_time_status_is_an_error(value):
    result = S.get_chart_summary(*BIRTH, time_status=value)
    assert result.get("error") is True
    assert "time_status" in result["message"] and "known, approximate, unknown" in result["message"]


def test_positions_have_no_house_without_a_time():
    """Crashed with "'Object' object has no attribute 'house'" before."""
    planets = S.get_planetary_positions(*BIRTH, time_status="unknown")["planets"]
    assert planets["Sun"]["sign"] == "Capricorn"
    assert {p["house"] for p in planets.values()} == {None}


def test_summary_nulls_what_needs_a_time():
    result = S.get_chart_summary(*BIRTH, time_status="unknown")
    assert result["sun_sign"] == "Capricorn"
    assert result["rising_sign"] is None
    assert result["house_system"] is None
    assert result["diurnal"] is None


@pytest.mark.parametrize("tool", ["natal", "compact_natal"])
def test_moon_range_for_an_unknown_time(tool):
    result = _single(tool, *BIRTH, time_status="unknown")
    span = result["moon_range"]
    assert span["start"]["time"] == "1990-01-15T00:00:00-08:00"
    assert span["end"]["time"] == "1990-01-15T23:59:00-08:00"
    assert (span["start"]["sign"], span["end"]["sign"], span["sign_change"]) == ("Virgo", "Virgo", False)
    assert any("stays in Virgo all day" in w for w in result["warnings"])
    assert "moon_range" not in _single(tool, *BIRTH, time_status="approximate")


def test_moon_range_flags_a_sign_change():
    result = S.generate_compact_natal_chart("1990-01-16 14:30:00", *BIRTH[1:], time_status="unknown")
    span = result["moon_range"]
    assert (span["start"]["sign"], span["end"]["sign"], span["sign_change"]) == ("Virgo", "Libra", True)
    assert any("changes sign that day (Virgo" in w and "so its sign is uncertain" in w
               for w in result["warnings"])


def test_polar_untimed_chart_has_no_polar_warning():
    for result in (S.generate_natal_chart(*POLAR, time_status="unknown"),
                   S.get_chart_summary(*POLAR, time_status="unknown")):
        assert result["status"] == "success"
        assert not any("polar circle" in w for w in result["warnings"])
        assert result["applied_settings"]["house_system"] is None
    assert "house_system" not in S.generate_natal_chart(*POLAR, time_status="unknown")


def test_lunar_return_for_an_unknown_time_is_cast_at_the_return_instant():
    """The return chart must not be recast at noon: it uses TIME_APPROXIMATE."""
    untimed = L.generate_compact_lunar_return_chart(*BIRTH[:3], 2026, 11, BIRTH[3], time_status="unknown")
    noon = L.generate_compact_lunar_return_chart("1990-01-15 12:00:00", *BIRTH[1:3], 2026, 11, BIRTH[3])
    assert untimed["lunar_return_info"]["return_date"] == noon["lunar_return_info"]["return_date"]
    assert not untimed["lunar_return_info"]["return_date"].endswith("T12:00:00-08:00")
    assert "houses" not in untimed and "houses" in noon
    assert any("return instant" in w and "12 hours" in w for w in untimed["warnings"])


def test_relocated_returns_keep_the_status():
    result = S.generate_solar_return_chart(*BIRTH[:3], 2026, BIRTH[3], time_status="unknown",
                                           return_latitude="51n30", return_longitude="0w07")
    assert result["status"] == "success" and "houses" not in result
    lunar = L.generate_lunar_return_chart(*BIRTH[:3], 2026, 11, BIRTH[3], time_status="unknown",
                                          return_latitude="51n30", return_longitude="0w07")
    assert lunar["status"] == "success" and "houses" not in lunar


def test_solar_return_warns_about_the_instant():
    result = S.generate_compact_solar_return_chart(*BIRTH[:3], 2026, BIRTH[3], time_status="unknown")
    assert any("return instant" in w and "12 hours" in w for w in result["warnings"])


def test_progressed_warns_about_the_progressed_moon():
    result = S.generate_compact_progressed_chart(*BIRTH[:3], TRANSIT, BIRTH[3], time_status="unknown")
    assert any("progressed Moon" in w for w in result["warnings"])


PAIR_TOOLS = {
    "composite": S.generate_composite_chart,
    "compact_composite": S.generate_compact_composite_chart,
    "synastry": S.generate_synastry_aspects,
    "compact_synastry": S.generate_compact_synastry_aspects,
}


def _pair(tool, **kw):
    return PAIR_TOOLS[tool](*BIRTH[:3], *PARTNER[:3], BIRTH[3], PARTNER[3], **kw)


@pytest.mark.parametrize("tool", PAIR_TOOLS)
def test_pair_tools_take_a_status_per_person(tool):
    result = _pair(tool, partner_time_status="unknown")
    assert result.get("status") == "success", result
    assert "houses" not in result
    text = json.dumps({k: v for k, v in result.items() if k != "warnings"})
    for name in ("Vertex", "Part of Fortune"):
        assert name not in text
    assert result["applied_settings"]["house_system"] is None
    assert result["applied_settings"]["time_status"] == "unknown"
    assert any(w.startswith("Partner's birth time unknown") for w in result["warnings"])
    assert not any(w.startswith("Native's") for w in result["warnings"])
    assert _pair(tool, native_time_status="known", partner_time_status="known") == _pair(tool)

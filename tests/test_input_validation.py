#!/usr/bin/env python3
"""
Input validation gaps found by the 2026-11-08 sweep: an unknown
aspect_priority silently became 'tight', a progression before birth
succeeded, clock-change local times were used without a word, and an
unknown timezone was blamed on a missing tzdata.
"""

import pytest

import immanuel_server
from immanuel_mcp.charts import lunar_return
from immanuel_mcp.utils import errors

LONDON = ("1990-05-15 12:00:00", "51n30", "0w07")
TZ = "Europe/London"

PRIORITY_TOOLS = {
    "compact_solar_return": lambda p: immanuel_server.generate_compact_solar_return_chart(
        *LONDON, 2026, TZ, aspect_priority=p),
    "compact_progressed": lambda p: immanuel_server.generate_compact_progressed_chart(
        *LONDON, "2026-11-08 12:00:00", TZ, aspect_priority=p),
    "transit_to_natal": lambda p: immanuel_server.generate_transit_to_natal(
        *LONDON, "2026-11-08 12:00:00", timezone=TZ, aspect_priority=p),
    "compact_lunar_return": lambda p: lunar_return.generate_compact_lunar_return_chart(
        *LONDON, 2026, 7, TZ, aspect_priority=p),
}


@pytest.mark.parametrize("tool", sorted(PRIORITY_TOOLS))
def test_an_unknown_aspect_priority_is_rejected(tool):
    result = PRIORITY_TOOLS[tool]("banana")
    assert result.get("status") == "error", result.get("status")
    assert "banana" in result["message"]
    assert "tight, moderate, loose, all" in result["message"]
    assert PRIORITY_TOOLS[tool]("moderate")["status"] == "success"


@pytest.mark.parametrize("build", [
    immanuel_server.generate_progressed_chart,
    immanuel_server.generate_compact_progressed_chart,
], ids=["full", "compact"])
def test_a_progression_before_birth_is_rejected(build):
    result = build(*LONDON, "1989-01-01 12:00:00", TZ)
    assert result.get("status") == "error"
    assert "before the birth" in result["message"]


@pytest.mark.parametrize("date_time, expected", [
    ("1990-03-25 01:30:00",
     "01:30 did not exist on 1990-03-25 in Europe/London (the clocks went forward); "
     "using 01:30 GMT (UTC+0), the same instant as 02:30 BST (UTC+1)"),
    ("1990-10-28 01:30:00",
     "01:30 occurred twice on 1990-10-28 in Europe/London (the clocks went back); "
     "using 01:30 BST (UTC+1), the first of the two. Write the UTC offset to "
     "choose: 1990-10-28T01:30:00+01:00 (BST) or 1990-10-28T01:30:00+00:00 (GMT)"),
])
def test_a_clock_change_time_is_accepted_with_a_warning(date_time, expected):
    result = immanuel_server.generate_compact_natal_chart(date_time, "51n30", "0w07", TZ)
    assert result["status"] == "success", result.get("message")
    assert result["warnings"] == [expected]


def test_an_ordinary_time_carries_no_warning():
    assert "warnings" not in immanuel_server.generate_compact_natal_chart(*LONDON, TZ)


# An explicit UTC offset in date_time. immanuel replaces the datetime's own
# zone with the one it looks up from the coordinates (by design, upstream
# #33), so the offset used to be dropped without a word: 12:00+05:00 in
# London was cast at 12:00 BST, and the second 01:30 of a fall-back night
# could not be asked for at all.

FALL_BACK_FIRST = 2461338.5208333335   # 2026-10-25 00:30 UTC = 01:30 BST
FALL_BACK_SECOND = 2461338.5625        # 2026-10-25 01:30 UTC = 01:30 GMT


def _julian(result):
    assert result["status"] == "success", result.get("message")
    return result["native"]["date_time"]["julian"]


@pytest.mark.parametrize("date_time, julian, reading", [
    ("2026-10-25T01:30:00+00:00", FALL_BACK_SECOND, "01:30 GMT (UTC+0), the second"),
    ("2026-10-25T01:30:00Z", FALL_BACK_SECOND, "01:30 GMT (UTC+0), the second"),
    ("2026-10-25 01:30:00+0000", FALL_BACK_SECOND, "01:30 GMT (UTC+0), the second"),
    ("2026-10-25T01:30:00+01:00", FALL_BACK_FIRST, "01:30 BST (UTC+1), the first"),
])
@pytest.mark.parametrize("timezone", [None, TZ], ids=["inferred", "explicit"])
def test_an_offset_chooses_the_reading_on_a_fall_back_night(date_time, julian, reading, timezone):
    result = immanuel_server.generate_natal_chart(date_time, "51n30", "0w07", timezone)
    assert _julian(result) == pytest.approx(julian, abs=1e-9)
    assert reading in result["warnings"][0]


@pytest.mark.parametrize("date_time, julian, used", [
    # 01:30 never happened on 1990-03-25 in London; each offset names a real
    # instant, and the chart is cast at that instant.
    ("1990-03-25T01:30:00+00:00", 2447975.5625, "using 01:30 GMT (UTC+0)"),
    ("1990-03-25T01:30:00+01:00", 2447975.5208333335, "using 01:30 BST (UTC+1)"),
])
def test_an_offset_names_the_instant_in_a_spring_forward_gap(date_time, julian, used):
    result = immanuel_server.generate_natal_chart(date_time, "51n30", "0w07", TZ)
    assert _julian(result) == pytest.approx(julian, abs=1e-9)
    assert used in result["warnings"][0]


def test_an_offset_that_matches_the_zone_changes_nothing():
    plain = immanuel_server.generate_natal_chart(*LONDON, TZ)
    offset = immanuel_server.generate_natal_chart("1990-05-15T12:00:00+01:00", "51n30", "0w07", TZ)
    assert _julian(offset) == _julian(plain)
    assert "warnings" not in offset


@pytest.mark.parametrize("date_time, timezone, given, actual", [
    ("2026-06-01T12:00:00+05:00", None, "UTC+5", "UTC+1 (BST)"),
    ("2026-06-01T12:00:00Z", TZ, "UTC+0", "UTC+1 (BST)"),
    ("2026-10-25T01:30:00+02:00", TZ, "UTC+2", "UTC+1 (BST) or UTC+0 (GMT)"),
])
def test_an_offset_that_contradicts_the_zone_is_rejected(date_time, timezone, given, actual):
    result = immanuel_server.generate_natal_chart(date_time, "51n30", "0w07", timezone)
    assert result["status"] == "error"
    assert f"gives {given}" in result["message"]
    assert f"Europe/London is {actual}" in result["message"]


def test_an_offset_carries_into_every_birth_chart_of_a_call():
    # Composite and synastry build two subjects, relocated returns a second
    # one in the birth zone: each must honour its own offset.
    second = "2026-10-25T01:30:00+00:00"
    bad = "2026-06-01T12:00:00+05:00"
    composite = immanuel_server.generate_composite_chart(
        *LONDON, second, "51n30", "0w07", TZ, TZ)
    assert composite["status"] == "success", composite.get("message")
    rejected = immanuel_server.generate_synastry_aspects(
        *LONDON, bad, "51n30", "0w07", TZ, TZ)
    assert rejected["status"] == "error"
    assert "Partner" in rejected["message"]
    relocated = immanuel_server.generate_solar_return_chart(
        second, "51n30", "0w07", 2030, TZ, return_latitude="40n43", return_longitude="74w00")
    assert relocated["status"] == "success", relocated.get("message")


def test_an_offset_is_moot_for_an_unknown_birth_time():
    # The chart is cast for local noon whatever the clock time says.
    result = immanuel_server.generate_compact_natal_chart(
        "2026-06-01T03:00:00+05:00", "51n30", "0w07", TZ, time_status="unknown")
    assert result["status"] == "success", result.get("message")


def test_an_unknown_timezone_is_named_as_unknown():
    result = immanuel_server.generate_natal_chart(*LONDON, "Mars/Olympus")
    assert result["status"] == "error"
    assert "Unknown IANA timezone 'Mars/Olympus'" in result["message"]
    assert "tzdata" not in result["message"] + result["suggestion"]


def test_tzdata_is_suggested_only_when_the_zone_database_is_missing(monkeypatch):
    monkeypatch.setattr(errors.zoneinfo, "available_timezones", lambda: set())
    result = immanuel_server.generate_natal_chart(*LONDON, "Mars/Olympus")
    assert "tzdata" in result["message"] + result["suggestion"]

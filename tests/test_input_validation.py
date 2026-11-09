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
     "using 01:30 BST (UTC+1), the first of the two"),
])
def test_a_clock_change_time_is_accepted_with_a_warning(date_time, expected):
    result = immanuel_server.generate_compact_natal_chart(date_time, "51n30", "0w07", TZ)
    assert result["status"] == "success", result.get("message")
    assert result["warnings"] == [expected]


def test_an_ordinary_time_carries_no_warning():
    assert "warnings" not in immanuel_server.generate_compact_natal_chart(*LONDON, TZ)


def test_an_unknown_timezone_is_named_as_unknown():
    result = immanuel_server.generate_natal_chart(*LONDON, "Mars/Olympus")
    assert result["status"] == "error"
    assert "Unknown IANA timezone 'Mars/Olympus'" in result["message"]
    assert "tzdata" not in result["message"] + result["suggestion"]


def test_tzdata_is_suggested_only_when_the_zone_database_is_missing(monkeypatch):
    monkeypatch.setattr(errors.zoneinfo, "available_timezones", lambda: set())
    result = immanuel_server.generate_natal_chart(*LONDON, "Mars/Olympus")
    assert "tzdata" in result["message"] + result["suggestion"]

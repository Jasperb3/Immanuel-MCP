#!/usr/bin/env python3
"""
The lunar-return search must not skip a return.

find_return_jd used immanuel's transit.next_aspect_to, whose
_fixed_aspect_search steps a whole day while the unsigned distance is at
least today's speed. When the Moon accelerates during that day it
overshoots the target, the distance grows again, and the loop runs on to the
next cycle. Searches from midnight on the 1st hit it: 6 of 528 month searches
(four charts, 2020-2030) skipped a return, e.g. 1990 London February 2026
("No lunar return found", though one falls on 2026-02-14 23:51 UTC).
"""

from datetime import datetime, timezone as dt_timezone

import pytest
import swisseph as swe
from immanuel import charts
from immanuel.const import chart as chart_const
from immanuel.tools import date as date_tools
from zoneinfo import ZoneInfo

from immanuel_mcp.charts import lunar_return
from immanuel_mcp.charts.lunar_return import _find_lunar_return_jds
from immanuel_mcp.utils.coordinates import parse_coordinate
from immanuel_mcp.utils.search import body_position, find_return_jd
from immanuel_mcp.utils.subjects import create_subject

CHARTS = {
    "London": ("1990-05-15 12:00:00", "51n30", "0w07", "Europe/London"),
    "San Diego": ("1984-01-01 12:00:00", "32n43", "117w09", "America/Los_Angeles"),
    "Sydney": ("1975-11-20 23:50:00", "-33.87", "151.21", "Australia/Sydney"),
    "Tokyo": ("2001-09-09 04:00:00", "35.68", "139.69", "Asia/Tokyo"),
}
# The months the old search got wrong
SKIPPED = [("London", 2025, 2), ("London", 2026, 2), ("San Diego", 2025, 8),
           ("Sydney", 2027, 5), ("Sydney", 2030, 8), ("Tokyo", 2027, 9)]
MINUTE = 1 / 1440


def _chart(name):
    date_time, latitude, longitude, tz = CHARTS[name]
    lat, lon = parse_coordinate(latitude, True), parse_coordinate(longitude, False)
    moon = charts.Natal(create_subject(date_time, lat, lon, tz)).objects[chart_const.MOON]
    return moon.longitude.raw, lat, lon, tz


def _month_jds(year, month, lat, lon, tz):
    start = date_tools.to_jd(datetime(year, month, 1), lat=lat, lon=lon, time_zone=tz)
    end = date_tools.to_jd(datetime(year + (month == 12), month % 12 + 1, 1),
                           lat=lat, lon=lon, time_zone=tz)
    return start, end


def _moon_minus(target, jd):
    return swe.difdeg2n(swe.calc_ut(jd, swe.MOON)[0][0], target)


def _brute_force(target, start, end):
    """Every crossing in [start, end): 0.05-day steps on the signed
    difference, then bisection. Independent of the code under test."""
    found, jd, previous = [], start, _moon_minus(target, start)
    while jd < end:
        nxt = min(jd + 0.05, end)
        current = _moon_minus(target, nxt)
        if previous < 0 <= current:
            lo, hi = jd, nxt
            while hi - lo > 1e-7:
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if _moon_minus(target, mid) < 0 else (lo, mid)
            found.append(hi)
        jd, previous = nxt, current
    return found


def test_1990_london_february_2026_has_its_return():
    result = lunar_return.generate_compact_lunar_return_chart(
        *CHARTS["London"][:3], 2026, 2, CHARTS["London"][3])
    assert result["status"] == "success", result.get("message")
    info = result["lunar_return_info"]
    assert len(info["returns_in_month"]) == 1
    moment = datetime.fromisoformat(info["return_date"])
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("Europe/London"))
    expected = datetime(2026, 2, 14, 23, 51, tzinfo=dt_timezone.utc)
    assert abs((moment - expected).total_seconds()) <= 60


@pytest.mark.parametrize("name, year, month", SKIPPED)
def test_the_months_the_old_search_skipped(name, year, month):
    target, lat, lon, tz = _chart(name)
    start, end = _month_jds(year, month, lat, lon, tz)
    want = _brute_force(target, start, end)
    got = _find_lunar_return_jds(target, year, month, lat, lon, tz)
    assert len(want) == 1 and len(got) == 1
    assert abs(got[0] - want[0]) < 2 * MINUTE


@pytest.mark.parametrize("name", sorted(CHARTS))
def test_every_month_2020_2030_matches_a_brute_force_scan(name):
    target, lat, lon, tz = _chart(name)
    for year in range(2020, 2031):
        for month in range(1, 13):
            start, end = _month_jds(year, month, lat, lon, tz)
            want = _brute_force(target, start, end)
            got = _find_lunar_return_jds(target, year, month, lat, lon, tz)
            assert len(got) == len(want), (name, year, month, got, want)
            for g, w in zip(got, want):
                assert abs(g - w) < 2 * MINUTE, (name, year, month)


# --- search boundaries ------------------------------------------------------

def _a_return():
    target = _chart("London")[0]
    return target, find_return_jd(chart_const.MOON, target, 2461072.5)


def test_a_search_starting_exactly_on_a_return_finds_that_return():
    target, moment = _a_return()
    assert abs(find_return_jd(chart_const.MOON, target, moment) - moment) < 1e-5
    # Just after it, the next return (~27.3 days on)
    later = find_return_jd(chart_const.MOON, target, moment + 1e-3)
    assert 27 < later - moment < 28


def test_a_return_on_the_search_window_edge_is_found():
    # The first scan window is 30 days. The Moon always returns inside it,
    # so use the Sun (one return a year) and put its return exactly on the
    # window's end: the scan must not drop it at the seam, and the doubled
    # window must not count it twice.
    moment = 2461072.5
    target = body_position(chart_const.SUN, moment)["lon"]
    assert abs(find_return_jd(chart_const.SUN, target, moment - 30.0) - moment) < 1e-5
    assert abs(find_return_jd(chart_const.SUN, target, moment - 30.0 - 1e-9) - moment) < 1e-5


def test_a_return_on_a_month_boundary_is_in_exactly_one_month():
    _, lat, lon, tz = _chart("London")
    boundary, _ = _month_jds(2026, 8, lat, lon, tz)  # 2026-08-01 00:00 BST
    target = body_position(chart_const.MOON, boundary)["lon"]  # a return at the boundary
    july = _find_lunar_return_jds(target, 2026, 7, lat, lon, tz)
    august = _find_lunar_return_jds(target, 2026, 8, lat, lon, tz)
    at_boundary = [jd for jd in july + august if abs(jd - boundary) < 1e-4]
    assert len(at_boundary) == 1, (july, august)


# --- the return chart is cast at the return instant -------------------------
# The chart was rebuilt from the naive local time string, so a return in the
# repeated hour of a fall-back night took the first reading. A 1995-03-04
# 07:31:37 London birth returns at 01:30 GMT on 2026-10-25 (the second
# 01:30); the chart was cast at 01:30 BST, an hour early.

FALL_BACK_BIRTH = ("1995-03-04 07:31:37", "51n30", "0w07")


@pytest.mark.parametrize("build", [
    lunar_return.generate_lunar_return_chart,
    lunar_return.generate_compact_lunar_return_chart,
], ids=["full", "compact"])
def test_a_return_in_the_repeated_fall_back_hour_is_cast_at_that_instant(build):
    result = build(*FALL_BACK_BIRTH, 2026, 10, "Europe/London")
    assert result["status"] == "success", result.get("message")
    info = result["lunar_return_info"]
    true_jd = find_return_jd(chart_const.MOON, info["natal_moon_longitude"], 2461337.5)
    assert abs(true_jd - 2461338.5625) < 1 / 1440  # 01:30 GMT
    moment = datetime.fromisoformat(info["return_date"])
    if moment.tzinfo is not None:
        assert moment.utcoffset().total_seconds() == 0  # GMT, the second 01:30
    # The chart itself: its Moon is on the natal Moon
    chart = lunar_return.generate_lunar_return_chart(*FALL_BACK_BIRTH, 2026, 10, "Europe/London")
    chart_moon = chart["objects"][str(chart_const.MOON)]["longitude"]["raw"]
    assert abs(swe.difdeg2n(chart_moon, info["natal_moon_longitude"])) < 1 / 3600
    # A computed moment is not the user's input: no clock-change warning
    assert "warnings" not in result

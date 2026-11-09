#!/usr/bin/env python3
"""
Every return and calendar timestamp is ISO 8601 with whole seconds and an
explicit offset.

They came in four shapes: '2026-07-01T13:51:43' (no offset),
'2026-07-28T20:07:33.143294' (microseconds), '...-04:00' only when a lunar
return was relocated, and the calendars with microseconds. Seconds are
truncated, never rounded up, so a displayed time is never later than the
moment and can't spill into the next day or month; which month a return
belongs to is decided from the full-precision Julian date.
"""

import re

import pytest
from immanuel import charts
from immanuel.const import chart as chart_const
from immanuel.tools import date as date_tools

import immanuel_server
from immanuel_mcp.charts import ingresses, lunar_return, lunations
from immanuel_mcp.charts.lunar_return import _find_lunar_return_jds
from immanuel_mcp.utils.subjects import create_subject

ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")
LONDON = ("1990-05-15 12:00:00", "51n30", "0w07")
TZ = "Europe/London"


def _all_match(values):
    values = list(values)
    assert values
    for value in values:
        assert ISO.match(value), value


def test_lunar_return_timestamps():
    info = lunar_return.generate_lunar_return_chart(*LONDON, 2026, 7, TZ)["lunar_return_info"]
    assert info["returns_in_month"] == ["2026-07-01T13:51:43+01:00", "2026-07-28T20:07:33+01:00"]
    assert info["return_date"] == "2026-07-01T13:51:43+01:00"
    second = lunar_return.generate_compact_lunar_return_chart(*LONDON, 2026, 7, TZ, occurrence=2)
    assert second["lunar_return_info"]["return_date"] == "2026-07-28T20:07:33+01:00"


def test_a_relocated_lunar_return_keeps_its_zone_rule():
    info = lunar_return.generate_lunar_return_chart(
        *LONDON, 2026, 7, TZ, return_latitude="40n43", return_longitude="74w00")["lunar_return_info"]
    # The return location's zone (New York, EDT), same instants as above
    assert info["returns_in_month"] == ["2026-07-01T08:51:43-04:00", "2026-07-28T15:07:33-04:00"]


@pytest.mark.parametrize("build", [
    immanuel_server.generate_solar_return_chart,
    immanuel_server.generate_compact_solar_return_chart,
], ids=["full", "compact"])
def test_solar_return_timestamp(build):
    assert build(*LONDON, 2026, TZ)["solar_return_info"]["return_date"] == "2026-05-15T05:04:25+01:00"


def test_calendar_timestamps():
    found = lunations.get_lunations_and_eclipses("2026-11-08 00:00:00", count=4, timezone=TZ)
    _all_match(e[key] for kind in ("new_moons", "full_moons", "solar_eclipses", "lunar_eclipses")
               for e in found[kind] for key in ("date_time_utc", "date_time_local"))
    found = ingresses.get_sign_ingresses("2026-11-08 00:00:00", count=3, timezone=TZ)
    _all_match(e[key] for events in found["ingresses"].values()
               for e in events for key in ("date_time_utc", "date_time_local"))


def test_a_return_in_the_last_second_of_a_month_stays_in_it():
    # This birth's natal Moon is reached at 23:59:59.83 BST on 2026-07-31.
    # Rounded to the nearest second that would read 2026-08-01T00:00:00.
    natal = ("1995-03-01 03:15:01.500000", "51n30", "0w07")
    lat, lon = 51.5, -0.11666666666666667
    moon = charts.Natal(create_subject(natal[0], lat, lon, TZ)).objects[chart_const.MOON].longitude.raw
    last = date_tools.to_datetime(
        _find_lunar_return_jds(moon, 2026, 7, lat, lon, TZ)[-1], lat=lat, lon=lon, time_zone=TZ)
    assert (last.month, last.day, last.hour, last.minute, last.second) == (7, 31, 23, 59, 59)
    assert last.microsecond >= 500000  # so rounding would spill into August

    july = lunar_return.generate_compact_lunar_return_chart(*natal, 2026, 7, TZ)["lunar_return_info"]
    august = lunar_return.generate_compact_lunar_return_chart(*natal, 2026, 8, TZ)["lunar_return_info"]
    assert july["returns_in_month"][-1] == "2026-07-31T23:59:59+01:00"
    assert all(r.startswith("2026-08") for r in august["returns_in_month"])
    assert not any(r.startswith("2026-08-01T00:00") for r in august["returns_in_month"])

#!/usr/bin/env python3
"""
in_sect on day and night charts of every chart class.

immanuel 1.7.0 dropped in_sect from every night chart (Chart.wrap_objects
tested `is_daytime` instead of `is_daytime is not None`), and the server
shimmed it back until 1.8.0 fixed it upstream (theriftlab/immanuel-python#31).
These now guard against a regression: before them nothing covered in_sect,
and all 402 tests passed on 1.7.0 with the bug in place.
"""

import datetime as _dt

import pytest
from immanuel import charts
from immanuel.const import chart as chart_const
from immanuel.tools import condition

import immanuel_mcp  # noqa: F401  (installs the compat shims)

SECT_PLANETS = (chart_const.SUN, chart_const.MOON, chart_const.MERCURY, chart_const.VENUS,
                chart_const.MARS, chart_const.JUPITER, chart_const.SATURN)

NIGHT = ("2001-03-21 23:59:00", -33.87, 151.21, "Australia/Sydney")  # diurnal False
DAY = ("1990-01-15 14:30:00", 32.71, -117.15, "America/Los_Angeles")  # diurnal True
PARTNER_NIGHT = ("1985-07-04 02:15:00", 51.5, -0.1167, "Europe/London")


def _subject(spec, **kwargs):
    dt, lat, lon, tz = spec
    return charts.Subject(dt, lat, lon, timezone=tz, **kwargs)


def _in_sect(chart):
    return {i: getattr(chart.objects[i], "in_sect", None) for i in SECT_PLANETS}


def _expected(chart):
    """1.6's computation, from the chart's own raw objects."""
    return {i: condition.is_object_in_sect(chart._objects[i], chart._diurnal, chart._triad[chart_const.SUN])
            for i in SECT_PLANETS}


def test_night_natal_matches_immanuel_16():
    """Values from the 0.10.5 (immanuel 1.6) snapshot of this chart."""
    natal = charts.Natal(_subject(NIGHT))
    assert natal.diurnal is False
    assert _in_sect(natal) == {
        chart_const.SUN: False, chart_const.MOON: True, chart_const.MERCURY: False,
        chart_const.VENUS: True, chart_const.MARS: True, chart_const.JUPITER: False,
        chart_const.SATURN: False,
    }


def test_day_natal_unchanged():
    natal = charts.Natal(_subject(DAY))
    assert natal.diurnal is True
    assert _in_sect(natal) == {
        chart_const.SUN: True, chart_const.MOON: False, chart_const.MERCURY: True,
        chart_const.VENUS: False, chart_const.MARS: False, chart_const.JUPITER: True,
        chart_const.SATURN: True,
    }


class _FrozenNow(_dt.datetime):
    """03:00 UTC on 2026-11-08: night in London."""

    @classmethod
    def now(cls, tz=None):
        frozen = _dt.datetime(2026, 11, 8, 3, 0, tzinfo=_dt.timezone.utc)
        return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)


def _night_charts(monkeypatch):
    native = _subject(NIGHT)
    natal = charts.Natal(native)
    monkeypatch.setattr(charts, "datetime", _FrozenNow)
    found = {
        "natal": natal,
        "solar_return": charts.SolarReturn(native, 2026),
        "progressed": charts.Progressed(native, "2026-11-08 12:00:00"),
        "composite": charts.Composite(native, _subject(PARTNER_NIGHT)),
        "transits": charts.Transits(51.5, -0.1167, timezone="Europe/London"),
        "transit_to_natal": charts.Natal(
            charts.Subject("2026-11-08 03:00:00", 51.5, -0.1167, timezone="Europe/London"),
            aspects_to=natal),
        # A lunar return chart is a Natal at the return instant (charts/lunar_return.py).
        "lunar_return": charts.Natal(charts.Subject(2461352.1, -33.87, 151.21, timezone="Australia/Sydney")),
    }
    return found


def test_every_chart_class_reports_sect_at_night(monkeypatch):
    found = _night_charts(monkeypatch)
    night = {name: c for name, c in found.items() if c._diurnal is False}
    # Each chart class must be exercised by a night chart, or the test proves nothing.
    assert {"natal", "progressed", "composite", "transits", "transit_to_natal", "lunar_return"} <= set(night), \
        {name: c._diurnal for name, c in found.items()}
    for name, c in found.items():
        values = _in_sect(c)
        assert all(isinstance(v, bool) for v in values.values()), (name, values)
        assert values == _expected(c), name


def test_unknown_time_has_no_sect():
    natal = charts.Natal(_subject(NIGHT, time_status=chart_const.TIME_UNKNOWN))
    assert set(_in_sect(natal).values()) == {None}


def test_full_serialized_night_chart_carries_sect():
    import immanuel_server

    result = immanuel_server.generate_natal_chart(*NIGHT[:1], str(NIGHT[1]), str(NIGHT[2]), NIGHT[3])
    assert result["diurnal"] is False
    sun = result["objects"][str(chart_const.SUN)]
    assert sun.get("in_sect") is False


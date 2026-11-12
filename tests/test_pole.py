"""Exactly 90 degrees north or south: houses and angles are undefined.

The Swiss Ephemeris returns an Ascendant of 0 Aries (or one tied to the Sun)
there with no error, which made spurious exact aspects. A timed chart there
is now an error; an untimed one, which casts no houses, still builds.
"""

import pytest

from immanuel_server import (
    generate_compact_natal_chart,
    generate_compact_progressed_chart,
    generate_composite_chart,
    generate_natal_chart,
)

MOMENT = "1990-01-15 12:00:00"


@pytest.mark.parametrize("latitude", ["90", "-90", "90n00", "90s00"])
@pytest.mark.parametrize("tool", [generate_natal_chart, generate_compact_natal_chart])
def test_timed_chart_at_the_pole_is_an_error(tool, latitude):
    result = tool(MOMENT, latitude, "0", timezone="UTC")
    assert result["status"] == "error"
    assert result["type"] == "PoleError"
    assert "undefined" in result["message"]
    assert "time_status='unknown'" in result["suggestion"]


@pytest.mark.parametrize("time_status", ["unknown", "approximate"])
def test_untimed_chart_at_the_pole_builds_with_lifecycle(time_status):
    result = generate_compact_natal_chart(MOMENT, "-90", "0", timezone="UTC", time_status=time_status)
    assert result["status"] == "success", result
    assert result["lifecycle_events"] is not None


def test_untimed_progression_at_the_pole_builds():
    result = generate_compact_progressed_chart(
        MOMENT, "90", "0", "2026-11-12 12:00:00", timezone="UTC", time_status="unknown")
    assert result["status"] == "success", result


def test_just_off_the_pole_builds():
    result = generate_compact_natal_chart(MOMENT, "89.99", "0", timezone="UTC")
    assert result["status"] == "success", result


def test_composite_with_a_partner_at_the_pole_is_an_error():
    result = generate_composite_chart(MOMENT, "51.5", "-0.13", MOMENT, "-90", "0")
    assert result["status"] == "error"
    assert result["type"] == "PoleError"


def test_transit_chart_at_the_pole_is_an_error():
    from immanuel_server import generate_compact_transit_chart
    result = generate_compact_transit_chart("90", "0")
    assert result["status"] == "error"
    assert result["type"] == "PoleError"


def test_return_relocated_to_the_pole_is_an_error():
    from immanuel_server import generate_compact_solar_return_chart
    result = generate_compact_solar_return_chart(
        MOMENT, "51.5", "-0.13", 2026, timezone="Europe/London",
        return_latitude="-90", return_longitude="0")
    assert result["status"] == "error"
    assert result["type"] == "PoleError"

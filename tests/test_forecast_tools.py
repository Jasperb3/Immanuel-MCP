"""Tests for the lunation/eclipse and sign-ingress calendars (v0.7.0).

Expected values are checked against the published ephemeris rather than
against the implementation, so a regression in the search shows up as a
wrong date rather than a silently shifted fixture.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from immanuel_mcp.charts.ingresses import get_sign_ingresses
from immanuel_mcp.charts.lunations import get_lunations_and_eclipses


def _dates(events):
    return [e["date_time_utc"][:10] for e in events]


# ---------------------------------------------------------------------------
# Lunations and eclipses
# ---------------------------------------------------------------------------

def test_lunations_match_published_ephemeris():
    result = get_lunations_and_eclipses("2025-01-01 00:00:00", count=2)
    assert result["status"] == "success"
    assert _dates(result["new_moons"]) == ["2025-01-29", "2025-02-28"]
    assert _dates(result["full_moons"]) == ["2025-01-13", "2025-02-12"]
    assert result["new_moons"][0]["sign"] == "Aquarius"


def test_eclipses_carry_type_and_match_ephemeris():
    result = get_lunations_and_eclipses("2025-01-01 00:00:00", count=1)
    solar = result["solar_eclipses"][0]
    lunar = result["lunar_eclipses"][0]
    assert solar["date_time_utc"][:10] == "2025-03-29"
    assert solar["eclipse_type"] == "Partial"
    assert lunar["date_time_utc"][:10] == "2025-03-14"
    assert lunar["eclipse_type"] == "Total"
    assert lunar["sign"] == "Virgo"


def test_eclipses_can_be_omitted():
    result = get_lunations_and_eclipses(
        "2025-01-01 00:00:00", count=1, include_eclipses=False)
    assert "solar_eclipses" not in result
    assert "lunar_eclipses" not in result


def test_lunations_local_time_uses_requested_zone():
    result = get_lunations_and_eclipses(
        "2025-09-01 00:00:00", count=1, timezone="Europe/London")
    event = result["new_moons"][0]
    assert event["date_time_local"].endswith("+01:00")  # BST
    assert event["date_time_utc"].endswith("+00:00")


def test_lunations_reject_out_of_range_count():
    result = get_lunations_and_eclipses("2025-01-01 00:00:00", count=99)
    assert result["status"] == "error"
    assert "count must be between" in result["message"]


# ---------------------------------------------------------------------------
# Sign ingresses
# ---------------------------------------------------------------------------

def test_saturn_ingresses_include_retrograde_re_entry():
    """Saturn crosses into Aries in May 2025, retrogrades back into Pisces in
    September, and re-enters in February 2026. Searching only forward would
    report the first and third and silently drop the middle one."""
    result = get_sign_ingresses("2025-01-01 00:00:00", planets=["Saturn"], count=3)
    assert result["status"] == "success"
    events = result["ingresses"]["Saturn"]
    assert _dates(events) == ["2025-05-25", "2025-09-01", "2026-02-14"]
    assert [e["into_sign"] for e in events] == ["Aries", "Pisces", "Aries"]
    assert [e["retrograde_re_entry"] for e in events] == [False, True, False]


def test_neptune_ingresses_match_ephemeris():
    result = get_sign_ingresses("2025-01-01 00:00:00", planets=["Neptune"], count=3)
    assert _dates(result["ingresses"]["Neptune"]) == [
        "2025-03-30", "2025-10-22", "2026-01-26"]


def test_venus_re_entry_after_a_station_is_not_skipped():
    """Regression: immanuel's own next_sign_ingress() brackets by 1/|speed|
    days, so as Venus approaches its April 2025 station the step grows without
    bound and leaps over the 2025-04-30 Aries re-entry, answering 2026-03-06
    instead. The bounded bracketing here must find it."""
    result = get_sign_ingresses("2025-01-01 00:00:00", planets=["Venus"], count=5)
    dates = _dates(result["ingresses"]["Venus"])
    assert dates == [
        "2025-01-03", "2025-02-04", "2025-03-27", "2025-04-30", "2025-06-06"]


def test_slow_planet_crossings_are_not_skipped():
    """Same station hazard on a slow body: Pluto's first crossing out of
    Aquarius is 2043-03-09, not the 2044-01-19 final settling."""
    result = get_sign_ingresses("2025-01-01 00:00:00", planets=["Pluto"], count=3)
    assert _dates(result["ingresses"]["Pluto"]) == [
        "2043-03-09", "2043-09-01", "2044-01-19"]


def test_fast_planet_ingresses_are_sane():
    """The Moon changes sign every ~2.3 days; the bracketing step must adapt
    to speed rather than assume a slow body."""
    result = get_sign_ingresses("2025-01-01 00:00:00", planets=["Moon"], count=5)
    events = result["ingresses"]["Moon"]
    assert _dates(events)[:3] == ["2025-01-01", "2025-01-03", "2025-01-05"]
    assert [e["into_sign"] for e in events[:3]] == ["Aquarius", "Pisces", "Aries"]


def test_ingresses_are_chronological():
    result = get_sign_ingresses("2025-01-01 00:00:00", count=4)
    for planet, events in result["ingresses"].items():
        dates = _dates(events)
        assert dates == sorted(dates), f"{planet} ingresses out of order"


def test_ingresses_default_to_the_slow_bodies():
    result = get_sign_ingresses("2025-01-01 00:00:00", count=1)
    assert set(result["ingresses"]) == {
        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"}


def test_ingresses_reject_unknown_planet():
    result = get_sign_ingresses(
        "2025-01-01 00:00:00", planets=["Saturn", "Nibiru"])
    assert result["status"] == "error"
    assert "Nibiru" in result["message"]


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_new_tools_are_registered():
    import asyncio
    import immanuel_server

    names = {t.name for t in asyncio.run(immanuel_server.mcp.list_tools())}
    assert "get_lunations_and_eclipses" in names
    assert "get_sign_ingresses" in names
    assert len(names) == 23

#!/usr/bin/env python3
"""
Future lifecycle events are dated by the ephemeris, not by age arithmetic.

Reported from live use on a 1 Jan 1984 San Diego chart: the Uranus
Opposition's exact_date was simply the query date, its date_range moved with
the query date, and lifecycle_summary named an already-perfected Pluto Square
as the "next" event, dated today. Its real perfections are 2028-06-19,
2028-12-29 and 2029-04-05 (age 44.5-45, outside the generic age 40-43 window
that used to gate it, so a query after age 43 dropped it altogether).
"""

import pytest

import immanuel_server
from immanuel_mcp.lifecycle.timeline import group_passes

NATAL = ("1984-01-01 12:00:00", "32.71", "-117.15")
TZ = "America/Los_Angeles"
URANUS_OPPOSITION_PASSES = ["2028-06-19", "2028-12-29", "2029-04-05"]


def _lifecycle(query_date):
    result = immanuel_server.generate_compact_transit_to_natal(
        *NATAL, query_date, timezone=TZ)
    assert result["status"] == "success", result.get("message")
    return result["lifecycle_events"], result["lifecycle_summary"]


def _event(events, name):
    matches = [e for e in events if e.get("event_type") == name]
    assert len(matches) == 1, [e.get("event_type") for e in events]
    return matches[0]


@pytest.mark.parametrize("query_date", [
    "2025-01-15 12:00:00",   # age 41.0
    "2026-11-08 12:00:00",   # age 42.9
    "2027-07-01 12:00:00",   # age 43.5: past the old age_range cut-off
])
def test_uranus_opposition_is_dated_by_the_ephemeris(query_date):
    events, _ = _lifecycle(query_date)
    uranus = _event(events, "Uranus Opposition")
    assert uranus["status"] == "upcoming"
    # All three passes, the retrograde middle one included
    assert uranus["exact_dates"] == URANUS_OPPOSITION_PASSES
    assert uranus["exact_date"] == "2028-06-19"
    assert uranus["exact_date_estimated"] is False
    assert uranus["prediction_basis"] == "ephemeris"
    # The same window whatever the query date
    assert uranus["date_range"] == "2028-06-19 to 2029-04-05"


def test_next_major_event_is_the_next_significant_perfection():
    events, summary = _lifecycle("2026-11-08 12:00:00")
    # A Mars Return perfects first (2027-08-25, Mars back on its natal
    # 205.1 deg; the old mean-period arithmetic said 2027-03-29, when Mars is
    # at 141 deg), but it is MODERATE, so the summary names the next
    # HIGH/CRITICAL event instead.
    mars = [e for e in events if e.get("event_type", "").startswith("Mars Return")]
    assert [m["exact_date"] for m in mars] == ["2027-08-25"]
    assert summary["next_major_event"] == "Uranus Opposition"
    assert summary["next_major_event_date"] == "2028-06-19"
    assert summary["years_until_event"] == pytest.approx(1.6, abs=0.1)


def test_a_fully_perfected_transit_is_not_listed_as_upcoming():
    events, _ = _lifecycle("2026-11-08 12:00:00")
    pluto = [e for e in events if e.get("event_type") == "Pluto Square"]
    # Its passes (2025-01-24, 08-30, 11-26) are all behind the query date; it
    # may still be active (in orb), but never "upcoming".
    assert all(e["status"] != "upcoming" for e in pluto)


def test_future_returns_are_dated_by_the_ephemeris():
    events, _ = _lifecycle("2026-11-08 12:00:00")
    upcoming_returns = [e for e in events
                        if e.get("category") == "return" and e["status"] == "upcoming"]
    assert upcoming_returns
    for event in upcoming_returns:
        assert event["exact_date_estimated"] is False, event["event_type"]
        assert event["exact_dates"], event["event_type"]
        assert event["exact_date"] in event["exact_dates"]
        assert event["prediction_basis"] == "ephemeris"


def test_passes_split_on_the_gap_between_hits():
    # Julian days: a three-pass retrograde sequence (gaps of months), then the
    # next one more than a year later.
    jds = [100.0, 300.0, 400.0, 900.0, 1000.0]
    assert group_passes(jds) == [[100.0, 300.0, 400.0], [900.0, 1000.0]]
    assert group_passes([]) == []

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
    # Its five passes (2024-03-28 to 2025-11-26) are all behind the query date; it
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


# --- review follow-ups ------------------------------------------------------

from datetime import datetime

from immanuel import charts
from immanuel.const import chart as chart_const

from immanuel_mcp.interpretations.aspects import english_aspect_terms
from immanuel_mcp.lifecycle.constants import MAJOR_LIFE_TRANSITS
from immanuel_mcp.lifecycle.lifecycle import _build_summary_enhancements, detect_lifecycle_events
from immanuel_mcp.lifecycle.timeline import (
    _jd_to_datetime, build_future_timeline, date_next_major_transit)
from immanuel_mcp.utils.search import find_exact_aspect_dates
from immanuel_mcp.utils.subjects import create_subject

BIRTH_DT = datetime(1984, 1, 1, 20, 0)


def _natal(config=None):
    subject = create_subject(*NATAL, TZ)
    return charts.Natal(subject, config=config) if config else charts.Natal(subject)


def test_dedup_against_active_events_does_not_shrink_the_timeline():
    # On 2025-01-15 the Pluto Square is active with a pass still ahead
    # (2025-01-24), so it is also the soonest future candidate. Removing it as
    # a duplicate must not leave the timeline one short.
    natal = _natal()
    reference = datetime(2025, 1, 15, 20, 0)
    transit = charts.Natal(create_subject("2025-01-15 12:00:00", "32.71", "-117.15", TZ))
    result = detect_lifecycle_events(natal, transit, BIRTH_DT, reference,
                                     future_years=20, max_future_events=2)
    assert any(e.get("name") == "Pluto Square" for e in result["current_events"])
    assert len(result["future_timeline"]) == 2
    assert all(e.get("name") != "Pluto Square" for e in result["future_timeline"])


def test_fallback_predictions_respect_the_timeline_horizon():
    config = charts.Config()
    config.objects = [o for o in config.objects
                      if o not in (chart_const.URANUS, chart_const.CHIRON)]
    timeline = build_future_timeline(
        42.9, BIRTH_DT, years_ahead=20, natal_chart=_natal(config),
        reference_datetime=datetime(2026, 11, 8, 20, 0))
    assert timeline
    for event in timeline:
        assert 0 <= event["years_until"] <= 20, event
    fallback = [e for e in timeline if e.get("prediction_basis") != "ephemeris"]
    assert fallback, "expected Uranus/Chiron events from the fallback"


def test_next_major_event_never_names_a_perfected_active_event():
    current = [{"event_type": "major_transit", "name": "Pluto Square",
                "significance": "CRITICAL", "exact_dates": ["2025-01-24", "2025-11-26"]}]
    future = [{"event_type": "return", "planet": "Mars", "cycle_number": 22,
               "significance": "MODERATE", "exact_dates": ["2027-08-25"],
               "predicted_date": "2027-08-25", "years_until": 0.8}]
    summary = _build_summary_enhancements(current, future, datetime(2026, 11, 8))
    assert summary["next_major_event"] == "Mars Return Cycle 22"
    assert summary["next_major_event_date"] == "2027-08-25"


def test_a_significant_fallback_event_can_be_next():
    future = [
        {"event_type": "return", "planet": "Mars", "cycle_number": 22,
         "significance": "MODERATE", "exact_dates": ["2026-12-01"],
         "predicted_date": "2026-12-01", "years_until": 0.1},
        {"event_type": "major_transit", "name": "Uranus Opposition",
         "significance": "CRITICAL", "exact_dates": [],
         "predicted_date": "2027-01-15", "years_until": 0.2,
         "prediction_basis": "typical_age"},
    ]
    summary = _build_summary_enhancements([], future, datetime(2026, 11, 8))
    assert summary["next_major_event"] == "Uranus Opposition"
    assert summary["next_major_event_date"] == "2027-01-15"


def test_a_reference_on_the_last_pass_does_not_drop_the_event():
    natal = _natal()
    uranus_opposition = next(c for c in MAJOR_LIFE_TRANSITS if c["name"] == "Uranus Opposition")
    natal_uranus = natal.objects[chart_const.URANUS].longitude.raw
    last_pass_jd = find_exact_aspect_dates(
        chart_const.URANUS, natal_uranus, 180.0, 2461000.0, 3 * 365.25)[-1]
    reference = _jd_to_datetime(last_pass_jd)  # sub-second rounding at the boundary
    event = date_next_major_transit(uranus_opposition, natal, BIRTH_DT, reference, 20)
    if event is not None:  # the boundary pass may fall either side; it must not raise
        assert event["exact_date"] in event["exact_dates"]


def test_interpretation_terms_require_the_angle():
    with pytest.raises(KeyError):
        english_aspect_terms({"active": 4000001, "passive": 4000002, "type": "Trígono"})


# --- age_at_event (0.10.1) --------------------------------------------------
# It used to read the textbook typical_age on every future major transit, and
# the current age on every active event.

from immanuel_mcp.lifecycle.lifecycle import format_lifecycle_event_feed

LONDON_1990 = ("1990-05-15 12:00:00", "51n30", "0w07")
LONDON_TZ = "Europe/London"


def _compact(natal, query_date, tz):
    result = immanuel_server.generate_compact_transit_to_natal(*natal, query_date, timezone=tz)
    assert result["status"] == "success", result.get("message")
    return result["lifecycle_events"], result["lifecycle_summary"]


@pytest.mark.parametrize("name, exact_date, age", [
    ("Neptune Square", "2031-05-09", 41.0),
    ("Pluto Square", "2033-03-25", 42.9),
    ("Uranus Opposition", "2034-08-19", 44.3),
])
def test_upcoming_major_transit_age_is_the_age_at_its_exact_date(name, exact_date, age):
    events, _ = _compact(LONDON_1990, "2019-12-01 12:00:00", LONDON_TZ)
    event = _event(events, name)
    assert event["exact_date"] == exact_date
    assert event["exact_date_estimated"] is False
    assert event["age_at_event"] == pytest.approx(age, abs=0.1)


def test_1984_uranus_opposition_age_is_not_the_textbook_41():
    events, _ = _lifecycle("2026-11-08 12:00:00")
    assert _event(events, "Uranus Opposition")["age_at_event"] == pytest.approx(44.5, abs=0.1)


def test_active_event_age_is_the_age_at_the_first_pass_of_its_cluster():
    events, summary = _lifecycle("2026-11-08 12:00:00")
    pluto = _event(events, "Pluto Square")
    assert pluto["status"] == "active"
    # Five passes, 2024-03-28 to 2025-11-26 (raw swisseph scan). Before
    # 0.10.3 the active search truncated it to the last three, so this read
    # 2025-01-24 / 41.1.
    assert pluto["exact_dates"] == [
        "2024-03-28", "2024-06-08", "2025-01-24", "2025-08-30", "2025-11-26"]
    assert pluto["age_at_event"] == pytest.approx(40.2, abs=0.1)
    assert summary["current_age"] == pytest.approx(42.9, abs=0.1)  # not the current age


def test_fallback_major_transit_keeps_the_typical_age_and_says_so():
    config = charts.Config()
    config.objects = [o for o in config.objects if o != chart_const.URANUS]
    natal = charts.Natal(create_subject(*LONDON_1990, LONDON_TZ), config=config)
    transit = charts.Natal(create_subject("2019-12-01 12:00:00", "51n30", "0w07", LONDON_TZ))
    birth, reference = datetime(1990, 5, 15, 11, 0), datetime(2019, 12, 1, 12, 0)
    data = detect_lifecycle_events(natal, transit, birth, reference, future_years=20)
    events = format_lifecycle_event_feed(data, reference)["events"]
    uranus = _event(events, "Uranus Opposition")
    assert uranus["exact_date_estimated"] is True
    assert uranus["prediction_basis"] == "typical_age"
    assert uranus["age_at_event"] == 41


# --- current_stage (0.10.1) -------------------------------------------------
# It came from a fixed age table: the 1984 chart at 42.9 read "Uranus
# Opposition" (band 41-43) while next_major_event said that opposition is
# 2028-29.

def _stage(natal, query_date, tz):
    return _compact(natal, query_date, tz)[1]["current_stage"]


def test_stage_is_the_active_ephemeris_event_not_the_age_band():
    stage = _stage(NATAL, "2026-11-08 12:00:00", TZ)
    assert stage["stage_name"] == "Pluto Square"
    assert stage["stage_basis"] == "ephemeris"
    # Multi-pass: the span of all five passes, 2024-03-28 to 2025-11-26
    assert stage["age_range"] == [40.2, 41.9]


def test_stage_during_the_saturn_return():
    stage = _stage(LONDON_1990, "2020-02-02 12:00:00", LONDON_TZ)
    assert stage["stage_name"] == "Saturn Return Cycle 1"
    assert stage["stage_basis"] == "ephemeris"
    # Single pass: the orb window (date_range 2019-12-19 to 2020-03-17),
    # not [29.7, 29.7]
    assert stage["age_range"][0] < stage["age_range"][1]
    assert set(stage) == {"stage_name", "description", "age_range", "themes", "stage_basis"}


def test_a_recent_past_event_is_the_stage_labelled_as_past():
    # 2.3 years after the Saturn Return's last pass, nothing major active
    stage = _stage(LONDON_1990, "2022-06-01 12:00:00", LONDON_TZ)
    assert stage["stage_name"] == "After Saturn Return Cycle 1"
    assert stage["stage_basis"] == "ephemeris_past"


def test_a_past_event_older_than_three_years_falls_back_to_the_age_band():
    stage = _stage(LONDON_1990, "2024-06-01 12:00:00", LONDON_TZ)
    assert stage["stage_basis"] == "age_band"
    assert stage["stage_name"] == "Post-Saturn Return"  # the age-34 band, not "After ..."
    assert stage["age_range"] == [31, 36]


def test_an_infant_has_only_the_age_band():
    stage = _stage(("2020-01-01 12:00:00", "51n30", "0w07"), "2021-06-01 12:00:00", LONDON_TZ)
    assert stage["stage_basis"] == "age_band"
    assert stage["stage_name"] == "Childhood"


# --- North Node return crossings (0.10.2) -----------------------------------
# The true node wobbles, so for 1990 London it crosses the natal node three
# times: 2027-09-22, 09-25 and 09-26 (brute-force scan of TRUE_NODE). The
# scanner's step put two crossings inside one step, so only one was reported,
# and which one depended on the query date.

NODE_PASSES = ["2027-09-22", "2027-09-25", "2027-09-26"]


@pytest.mark.parametrize("query_date", [
    "2019-12-01 12:00:00", "2022-06-01 12:00:00", "2026-11-08 12:00:00", "2027-06-01 12:00:00"])
def test_north_node_return_lists_every_crossing(query_date):
    events, _ = _compact(LONDON_1990, query_date, LONDON_TZ)
    node = _event(events, "North Node Return Cycle 2")
    assert node["exact_dates"] == NODE_PASSES
    assert node["exact_date"] == "2027-09-22"
    assert node["date_range"] == "2027-09-22 to 2027-09-26"


def test_the_natal_and_transiting_node_are_the_same_point():
    from immanuel_mcp.constants import PLANET_CONSTANTS
    natal = charts.Natal(create_subject(*LONDON_1990, LONDON_TZ))
    assert PLANET_CONSTANTS["North Node"] == chart_const.TRUE_NORTH_NODE
    assert chart_const.TRUE_NORTH_NODE in natal.objects
    assert chart_const.NORTH_NODE not in natal.objects  # no mean node to mix up


def test_an_active_node_return_lists_every_crossing():
    natal = charts.Natal(create_subject(*LONDON_1990, LONDON_TZ))
    transit = charts.Natal(create_subject("2027-09-24 12:00:00", "51n30", "0w07", LONDON_TZ))
    reference = datetime(2027, 9, 24, 11, 0)
    data = detect_lifecycle_events(natal, transit, datetime(1990, 5, 15, 11, 0), reference)
    node = [e for e in data["current_events"] if e.get("planet") == "North Node"]
    assert len(node) == 1
    assert node[0]["exact_dates"] == NODE_PASSES


# --- active events report the whole pass cluster (0.10.3) -------------------
# While active, the 1990 London Pluto Square reported 2-3 of its five passes,
# chosen by the query date: the active search sized its window from the
# current speed and kept at most 3 hits. Upcoming queries got all five.

PLUTO_SQUARE_PASSES = ["2033-03-25", "2033-07-11", "2034-01-30", "2034-09-27", "2034-11-29"]


def _active(query_date, name):
    events, _ = _compact(LONDON_1990, query_date, LONDON_TZ)
    matches = [e for e in events if e.get("event_type", "").startswith(name)]
    assert len(matches) == 1, [e.get("event_type") for e in events]
    return matches[0]


@pytest.mark.parametrize("query_date", [
    "2033-01-15 12:00:00",  # in orb (1.9 deg), before the first pass
    "2033-04-01 12:00:00", "2033-06-01 12:00:00", "2034-01-15 12:00:00",
    "2034-01-30 12:00:00",  # exactly on a pass
    "2034-10-15 12:00:00",  # between passes 4 and 5
    "2034-12-15 12:00:00", "2035-03-01 12:00:00",
])
def test_an_active_pluto_square_reports_all_five_passes(query_date):
    pluto = _active(query_date, "Pluto Square")
    assert pluto["status"] == "active"
    assert pluto["exact_dates"] == PLUTO_SQUARE_PASSES
    assert pluto["date_range"] == "2033-03-25 to 2034-11-29"
    assert pluto["age_at_event"] == pytest.approx(42.9, abs=0.05)
    # exact_date for an active event stays the pass closest to the query
    assert pluto["exact_date"] in PLUTO_SQUARE_PASSES


def test_an_active_event_exact_date_is_the_closest_pass_even_if_past():
    assert _active("2034-10-15 12:00:00", "Pluto Square")["exact_date"] == "2034-09-27"
    assert _active("2034-01-30 12:00:00", "Pluto Square")["exact_date"] == "2034-01-30"


@pytest.mark.parametrize("query_date", ["2031-08-01 12:00:00", "2031-12-01 12:00:00"])
def test_an_active_neptune_square_keeps_its_three_passes(query_date):
    neptune = _active(query_date, "Neptune Square")
    assert neptune["status"] == "active"
    assert neptune["exact_dates"] == ["2031-05-09", "2031-10-02", "2032-03-10"]


def test_an_active_single_pass_return_is_unchanged():
    saturn = _active("2020-02-02 12:00:00", "Saturn Return")
    assert saturn["exact_dates"] == ["2020-02-02"]


def test_an_active_mars_return_picks_the_nearest_of_several_clusters():
    # A +-4 year window holds several Mars return clusters (~every 2.1
    # years); the 2035 retrograde one is three passes.
    mars = _active("2035-10-15 12:00:00", "Mars Return")
    assert mars["status"] == "active"
    assert mars["exact_dates"] == ["2035-07-05", "2035-10-06", "2035-10-24"]


# --- a pass at a grazing station (0.10.4) -----------------------------------
# 1984 San Diego's Neptune Square target is 359.3776 deg. Neptune stations
# direct in December 2025 17.7" past it: it crosses on 12-06, turns, and
# re-crosses on 12-14. Both crossings fell inside one 10-day scan step, the
# side was the same at both ends, and the pair was lost - or not, depending
# on where the query date put the samples.

SD_1984 = ("1984-01-01 12:00:00", "32n43", "117w09")
SD_TZ = "America/Los_Angeles"
SD_NEPTUNE_SQUARE = ["2024-05-17", "2024-08-18", "2025-03-14", "2025-12-06", "2025-12-14"]


@pytest.mark.parametrize("query_date", ["2024-08-15 12:00:00", "2025-12-10 12:00:00"])
def test_a_grazing_station_keeps_both_of_its_passes(query_date):
    events, _ = _compact(SD_1984, query_date, SD_TZ)
    neptune = _event(events, "Neptune Square")
    assert neptune["status"] == "active"
    assert neptune["exact_dates"] == SD_NEPTUNE_SQUARE
    assert neptune["date_range"] == "2024-05-17 to 2025-12-14"


def test_at_a_grazing_station_exact_date_is_one_of_its_two_passes():
    events, _ = _compact(SD_1984, "2025-12-10 12:00:00", SD_TZ)
    # 4 days either side: the closest-pass rule allows either
    assert _event(events, "Neptune Square")["exact_date"] in ("2025-12-06", "2025-12-14")


# --- sequences that run past the timeline horizon (0.10.4) ------------------
# The future-timeline scan stopped at the 20-year horizon, so a sequence
# that started inside it lost its later passes. Queried 2026-06-15, horizon
# 2046-06-15.

HORIZON_QUERY = "2026-06-15 12:00:00"


@pytest.mark.parametrize("birth, name, passes", [
    ("1987-02-12 09:30:00", "Saturn Return Cycle 2", ["2046-01-20", "2046-06-18", "2046-10-20"]),
    ("2006-10-26 14:30:00", "Neptune Square",
     ["2045-08-02", "2045-09-06", "2046-05-13", "2046-12-15", "2047-03-08"]),
    ("1971-01-19 11:30:00", "Chiron Opposition", ["2046-01-03", "2046-02-05", "2046-08-21"]),
])
def test_a_sequence_crossing_the_horizon_is_listed_whole(birth, name, passes):
    events, _ = _compact((birth, "51n30", "0w07"), HORIZON_QUERY, LONDON_TZ)
    event = _event(events, name)
    assert event["status"] == "upcoming"
    assert event["exact_dates"] == passes
    assert event["exact_date"] == passes[0]
    assert event["date_range"] == f"{passes[0]} to {passes[-1]}"


def test_a_sequence_starting_after_the_horizon_is_not_listed():
    from datetime import datetime

    from immanuel.const import calc as calc_const
    from immanuel.const import chart as chart_const

    from immanuel_mcp.lifecycle.timeline import find_next_pass

    # 2006 London natal Neptune 317.0327: the square's first pass is
    # 2045-08-02, a month after a 20-year horizon from 2025-07-01.
    natal_neptune = 317.0327
    reference = datetime(2025, 7, 1, 12)
    assert find_next_pass(chart_const.NEPTUNE, natal_neptune, calc_const.SQUARE,
                          reference, 20) == ([], None)
    passes, first = find_next_pass(chart_const.NEPTUNE, natal_neptune, calc_const.SQUARE,
                                   reference, 20.2)
    assert first.strftime("%Y-%m-%d") == "2045-08-02"
    assert len(passes) == 5

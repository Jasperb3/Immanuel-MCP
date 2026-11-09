#!/usr/bin/env python3
"""
Two crossings either side of a station must both be found.

A body that stations just past a target crosses it, turns, and crosses back,
sometimes days apart. When both crossings fall inside one scan step the side
is the same at both ends, so watching the side alone sees nothing: 1984 San
Diego's Neptune Square lost its 2025-12-06 / 12-14 pair (a 17.7" overshoot).
The scanner also watches the sign of the speed. A sign change brackets a
station; the side at the station tells whether the pair is there.
"""

import pytest
import swisseph as swe
from immanuel.const import chart as chart_const

from immanuel_mcp.utils.search import _crossings, body_position, find_state_changes

BODIES = {
    chart_const.MERCURY: "Mercury", chart_const.VENUS: "Venus", chart_const.MARS: "Mars",
    chart_const.JUPITER: "Jupiter", chart_const.SATURN: "Saturn",
    chart_const.URANUS: "Uranus", chart_const.NEPTUNE: "Neptune",
    chart_const.PLUTO: "Pluto", chart_const.CHIRON: "Chiron",
}
START_JD = 2460676.5  # 2025-01-01


def _speed(index, jd):
    return body_position(index, jd)["speed"]


def _first_station(index, from_jd):
    """Bisected moment of the first sign change of the speed after from_jd."""
    jd, direct = from_jd, _speed(index, from_jd) >= 0
    while (_speed(index, jd + 1) >= 0) == direct:
        jd += 1
    lo, hi = jd, jd + 1
    while hi - lo > 1e-7:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if (_speed(index, mid) >= 0) == direct else (lo, mid)
    return hi, direct


@pytest.mark.parametrize("overshoot_arcsec", [1.0, 20.0, 60.0])
@pytest.mark.parametrize("index", sorted(BODIES), ids=lambda i: BODIES[i])
@pytest.mark.parametrize("skip", [True, False], ids=["skip", "stepped"])
def test_a_station_just_past_a_target_gives_two_crossings(index, overshoot_arcsec, skip):
    station, direct_before = _first_station(index, START_JD)
    station_lon = body_position(index, station)["lon"]
    # Set the target short of the station's turning point, on the side the
    # body came from: it crosses going in, and again coming back.
    sign = 1 if direct_before else -1
    target = (station_lon - sign * overshoot_arcsec / 3600) % 360
    hits = _crossings(index, target, station - 120, station + 120, skip=skip)
    # Only this station's pair: a fast body (Mercury) reaches the same
    # longitude again a few weeks on, past its next station.
    half_gap = (_first_station(index, station + 1e-3)[0] - station) / 2
    near = [jd for jd in hits if abs(jd - station) < half_gap]
    assert len(near) == 2, (BODIES[index], overshoot_arcsec, near)
    assert near[0] < station < near[1]
    for jd in near:
        assert abs(swe.difdeg2n(body_position(index, jd)["lon"], target)) < 1e-4


def test_a_station_just_short_of_a_target_gives_none():
    station, direct_before = _first_station(chart_const.NEPTUNE, START_JD)
    station_lon = body_position(chart_const.NEPTUNE, station)["lon"]
    sign = 1 if direct_before else -1
    target = (station_lon + sign * 1.0 / 3600) % 360  # 1" beyond the turn
    hits = _crossings(chart_const.NEPTUNE, target, station - 120, station + 120)
    assert hits == []


def test_the_generic_scanner_finds_the_pair_without_a_filter():
    # Callers that give find_state_changes no may_hide_pair get every
    # station checked.
    station, direct_before = _first_station(chart_const.NEPTUNE, START_JD)
    station_lon = body_position(chart_const.NEPTUNE, station)["lon"]
    target = (station_lon - (1 if direct_before else -1) * 1.0 / 3600) % 360
    hits = find_state_changes(
        chart_const.NEPTUNE, station - 60, station + 60,
        lambda planet: swe.difdeg2n(planet["lon"], target) >= 0)
    assert len(hits) == 2 and hits[0] < station < hits[1]

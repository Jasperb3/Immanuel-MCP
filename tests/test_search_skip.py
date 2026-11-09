#!/usr/bin/env python3
"""
The crossing search's safe skip must not lose crossings.

_crossings() may jump a body that is far from its target by the time it would
need at its (padded) maximum speed to get within a degree. Physically that
cannot pass a crossing of the target; it only changes where samples fall.

Before 0.10.4 the stepping scanner had a blind spot: two crossings inside one
step near a station, caught or not by sample phase, so the two scanners
disagreed there (three station pairs over 792 offline searches). The scanner
now watches the speed's sign and recovers both crossings of such a pair, so
the skipped and stepped scans must agree exactly.
"""

import pytest
import swisseph as swe
from immanuel.const import chart as chart_const

from immanuel_mcp.utils.search import _crossings, body_position

BODIES = [chart_const.MARS, chart_const.JUPITER, chart_const.SATURN, chart_const.URANUS,
          chart_const.NEPTUNE, chart_const.PLUTO, chart_const.CHIRON,
          chart_const.TRUE_NORTH_NODE]
TARGETS = [7.37, 67.37, 127.37, 187.37, 247.37, 307.37]
START_JD = 2446066.5  # 1985-01-01
SPAN_DAYS = 20 * 365.25


def _is_crossing(index, jd, target):
    before = swe.difdeg2n(body_position(index, jd - 0.01)["lon"], target) >= 0
    after = swe.difdeg2n(body_position(index, jd + 0.01)["lon"], target) >= 0
    at = abs(swe.difdeg2n(body_position(index, jd)["lon"], target))
    return at < 1e-3 and before != after


@pytest.mark.parametrize("index", BODIES)
def test_skip_finds_exactly_what_the_stepped_scan_finds(index):
    for target in TARGETS:
        stepped = _crossings(index, target, START_JD, START_JD + SPAN_DAYS, skip=False)
        skipped = _crossings(index, target, START_JD, START_JD + SPAN_DAYS, skip=True)
        for jd in stepped + skipped:
            assert _is_crossing(index, jd, target), (index, target, jd)
        assert len(stepped) == len(skipped), (index, target, stepped, skipped)
        for a, b in zip(stepped, skipped):
            assert abs(a - b) < 1e-5, (index, target, a, b)


def test_skip_is_what_makes_lifecycle_dating_cheap():
    """Guards the reason the skip exists: a 20-year Pluto search."""
    from immanuel_mcp.utils import search

    calls = {"n": 0}
    original = search.body_position

    def counting(index, jd):
        calls["n"] += 1
        return original(index, jd)

    search.body_position = counting
    try:
        _crossings(chart_const.PLUTO, 127.37, START_JD, START_JD + SPAN_DAYS, skip=True)
        skipped_calls = calls["n"]
        calls["n"] = 0
        _crossings(chart_const.PLUTO, 127.37, START_JD, START_JD + SPAN_DAYS, skip=False)
        stepped_calls = calls["n"]
    finally:
        search.body_position = original
    assert skipped_calls * 5 < stepped_calls, (skipped_calls, stepped_calls)

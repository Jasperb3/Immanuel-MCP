#!/usr/bin/env python3
"""
Transit-to-natal aspects say whether they are applying, and transit positions
say which natal house they fall in.

immanuel's own `movement` on a cross-chart aspect can't be trusted for
transits: it picks the "active" object by speed (so a natal Moon can be
"active" against transiting Neptune) and calls any retrograde active object
applicative. On 2026-11-12 it reports transiting Saturn (8°39' Aries,
retrograde) square natal Neptune (9°58' Capricorn) as Applicative, though
Saturn is backing away from the exact degree. The natal point is fixed, so
the direction follows from the transiting object alone: `applying` is true
when its motion is closing the orb.

The `house` on a transit position is a house of the transit moment's own
chart. `natal_house` is the house of the natal chart the position falls in.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from immanuel_mcp.optimizers.transit_direction import natal_house_of, transit_applying
from immanuel_server import generate_compact_transit_to_natal, generate_transit_to_natal

NATAL = dict(natal_date_time="1988-03-14 06:20:00", natal_latitude="53.8008",
             natal_longitude="-1.5491", timezone="Europe/London")
ON = "2026-11-12 12:00:00"


# --- the direction rule ---

@pytest.mark.parametrize("transit, speed, natal, angle, expected", [
    (8.64, -0.02, 279.97, 90, False),    # before the exact degree (9.97 Aries), retrograde: backing away
    (8.64, 0.02, 279.97, 90, True),      # before it, direct: closing
    (10.50, 0.02, 279.97, 90, False),    # past it, direct: leaving
    (10.50, -0.02, 279.97, 90, True),    # past it, retrograde: coming back
    (359.0, 1.0, 1.0, 0, True),          # conjunction across 0 Aries
    (2.0, 1.0, 1.0, 0, False),
    (179.0, 1.0, 0.5, 180, True),        # opposition
    (182.0, 1.0, 0.5, 180, False),
    (58.0, 0.1, 0.0, 60, True),          # sextile from either side
    (302.0, 0.1, 0.0, 60, False),        # 58 degrees behind and closing in on the conjunction, so the sextile is past
    (298.0, 0.1, 0.0, 60, True),
    (120.0, 0.5, 0.0, 120, False),       # exactly on it: any motion widens the orb
])
def test_transit_applying(transit, speed, natal, angle, expected):
    assert transit_applying(transit, speed, natal, angle) is expected


# --- natal house of a longitude ---

def test_natal_house_of():
    cusps = [348.16, 43.14, 68.26, 85.91, 102.73, 124.27, 168.16, 223.14, 248.26, 265.91, 282.73, 304.27]
    assert natal_house_of(8.64, cusps) == 1       # Aries, after a Pisces Ascendant
    assert natal_house_of(348.16, cusps) == 1     # on the cusp
    assert natal_house_of(348.15, cusps) == 12
    assert natal_house_of(303.25, cusps) == 11    # early Aquarius, just before the 12th cusp
    assert natal_house_of(270.0, cusps) == 10


# --- the compact tool ---

def _aspect(result, transiting, natal):
    for a in result["transit_to_natal_aspects"]:
        if a.get("transiting_object") == transiting and a.get("natal_object") == natal:
            return a
        if a.get("planets") == f"transit {transiting} → natal {natal}":
            return a
    raise AssertionError(f"no {transiting} -> {natal} aspect")


def test_compact_aspects_carry_applying():
    result = generate_compact_transit_to_natal(**NATAL, transit_date_time=ON, include_interpretations=False,
                                               include_lifecycle_events=False)
    assert result["status"] == "success"
    assert all(isinstance(a["applying"], bool) for a in result["transit_to_natal_aspects"])
    # Saturn retrograde at 8°39' Aries, natal Neptune at 9°58' Capricorn: moving away.
    assert _aspect(result, "Saturn", "Neptune")["applying"] is False
    # Neptune retrograde at 1°52' Aries, natal Uranus at 0°51' Capricorn: backing onto it.
    assert _aspect(result, "Neptune", "Uranus")["applying"] is True
    # Pluto direct at 3°15' Aquarius, natal Moon at 0°44' Aquarius: past it.
    assert _aspect(result, "Pluto", "Moon")["applying"] is False


def test_compact_applying_matches_the_orb_three_days_later():
    """For slow planets that don't station in between, applying means the orb shrinks."""
    kw = dict(include_interpretations=False, include_lifecycle_events=False)
    now = generate_compact_transit_to_natal(**NATAL, transit_date_time=ON, **kw)
    later = generate_compact_transit_to_natal(**NATAL, transit_date_time="2026-11-15 12:00:00", **kw)
    slow = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    retro_now = {o["name"]: o["retrograde"] for o in now["transit_positions"].values()}
    retro_later = {o["name"]: o["retrograde"] for o in later["transit_positions"].values()}
    checked = 0
    for a in now["transit_to_natal_aspects"]:
        t, n = a["transiting_object"], a["natal_object"]
        if t not in slow or retro_now[t] != retro_later[t] or abs(a["orb"]) < 0.1:
            continue
        b = next((x for x in later["transit_to_natal_aspects"]
                  if x["transiting_object"] == t and x["natal_object"] == n and x["type"] == a["type"]), None)
        if b is None:
            continue
        assert a["applying"] == (abs(b["orb"]) < abs(a["orb"])), (t, n, a["orb"], b["orb"])
        checked += 1
    assert checked >= 8


def test_compact_positions_carry_natal_house():
    result = generate_compact_transit_to_natal(**NATAL, transit_date_time=ON, include_interpretations=False,
                                               include_lifecycle_events=False)
    saturn = next(o for o in result["transit_positions"].values() if o["name"] == "Saturn")
    assert saturn["house"] == 2            # the transit moment's own chart
    assert saturn["natal_house"] == 1      # Aries, after a Pisces Ascendant at 18°10'
    pluto = next(o for o in result["transit_positions"].values() if o["name"] == "Pluto")
    assert pluto["natal_house"] == 11      # 3°15' Aquarius, before the 12th cusp at 4°16'
    assert all("natal_house" in o for o in result["transit_positions"].values())


def test_untimed_natal_chart_has_no_natal_house():
    result = generate_compact_transit_to_natal(**NATAL, transit_date_time=ON, time_status="unknown",
                                               include_interpretations=False, include_lifecycle_events=False)
    assert result["status"] == "success"
    assert all(o["natal_house"] is None for o in result["transit_positions"].values())
    assert all(isinstance(a["applying"], bool) for a in result["transit_to_natal_aspects"])


# --- the full tool ---

def test_full_aspects_carry_applying_and_keep_movement():
    result = generate_transit_to_natal(**NATAL, transit_date_time=ON, include_lifecycle_events=False)
    assert result["status"] == "success"
    aspects = result["transit_to_natal_aspects"]
    assert aspects and all(isinstance(a["applying"], bool) for a in aspects)
    saturn = _aspect(result, "Saturn", "Neptune")
    assert saturn["applying"] is False
    assert saturn["movement"] == "Applicative"     # immanuel's own label, left as it was
    assert result["transit_positions"]["Saturn"]["natal_house"] == 1
    assert result["transit_positions"]["Saturn"]["house"] == 2

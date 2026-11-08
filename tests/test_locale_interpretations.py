#!/usr/bin/env python3
"""
Interpretations must not depend on the session locale.

Chart data is translated under a locale ('Trígono', 'Júpiter'), but the
interpretation tables are English prose keyed by English names. Keying the
lookup on the translated names made every non-English aspect fall through to
the generic "energy, connection, influence" text.
"""

import pytest

import immanuel_server
from immanuel_mcp.utils.settings import reset_global_settings

NATAL = ("1984-01-01 12:00:00", "32.71", "-117.15")
TZ = "America/Los_Angeles"
TRANSIT_DATE = "2026-11-08 12:00:00"
PARTNER = ("1985-07-04 06:15:00", "51n30", "0w07")

ANGLES = {"Asc", "MC"}
INTERPRETATION_KEYS = ("keywords", "nature", "interpretation")


@pytest.fixture(autouse=True)
def clean_session():
    reset_global_settings()
    yield
    reset_global_settings()


def _interpretations(aspects):
    return [tuple(str(a.get(k)) for k in INTERPRETATION_KEYS) for a in aspects]


def _in_locale(locale, build):
    reset_global_settings()
    if locale:
        assert immanuel_server.configure_immanuel_settings("locale", locale)["status"] == "success"
    return build()


def _transit_to_natal():
    return immanuel_server.generate_compact_transit_to_natal(
        *NATAL, TRANSIT_DATE, timezone=TZ)["transit_to_natal_aspects"]


def _synastry():
    return immanuel_server.generate_compact_synastry_aspects(
        *NATAL, *PARTNER, TZ, "Europe/London")["aspects"]


def _return_cross_aspects():
    return immanuel_server.generate_compact_solar_return_chart(
        *NATAL, 2026, timezone=TZ, aspect_priority="all")["natal_cross_aspects"]


@pytest.mark.parametrize("locale", ["pt_BR", "de_DE", "es_ES"])
@pytest.mark.parametrize("build", [_transit_to_natal, _synastry, _return_cross_aspects],
                         ids=["transit_to_natal", "synastry", "return_cross"])
def test_interpretations_match_english(locale, build):
    english = _in_locale(None, build)
    localized = _in_locale(locale, build)
    assert english, "fixture produced no aspects"
    assert _interpretations(localized) == _interpretations(english)


def test_fixture_covers_angle_and_planet_pairs():
    """Guards the test above: it must exercise both an angle-planet pair and a
    planet-planet pair with a pair-specific (non-generic) interpretation."""
    aspects = _transit_to_natal()
    pairs = [{a["object1"], a["object2"]} for a in aspects]
    assert any(pair & ANGLES for pair in pairs), pairs
    assert any(a["nature"] != "variable" and not ({a["object1"], a["object2"]} & ANGLES)
               for a in aspects)


def test_compact_aspects_carry_their_angle():
    aspects = immanuel_server.generate_compact_natal_chart(*NATAL, timezone=TZ)["aspects"]
    assert aspects
    assert all(a["angle"] in (0.0, 60.0, 90.0, 120.0, 180.0) for a in aspects)

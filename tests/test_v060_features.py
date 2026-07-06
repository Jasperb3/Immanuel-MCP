#!/usr/bin/env python3
"""
Tests for the v0.6.0 feature set (post-v0.5.0 enhancement plan):

- I1: per-call house_system on chart tools via isolated settings,
      plus the applied_settings echo on every chart response
- I2: progressed-to-natal and return-to-natal cross aspects (aspects_to)
- I3: relocated solar and lunar returns
- I4: settings validation, reset tool, session-scope warnings
- I5: status field on all tool responses

Run from the repo root: python -m pytest tests/test_v060_features.py
"""

import pytest

from immanuel import setup
from immanuel.const import chart as chart_const

import immanuel_server
from immanuel_mcp.charts import lunar_return as lunar_return_module

BIRTH = ("1990-01-15 14:30:00", "32.71", "-117.15")
TZ = "America/Los_Angeles"


@pytest.fixture(autouse=True)
def _pristine_global_settings():
    """Every test starts and ends with the library-default house system."""
    setup.settings.house_system = chart_const.PLACIDUS
    yield
    setup.settings.house_system = chart_const.PLACIDUS


# ---------------------------------------------------------------------------
# I1: per-call house_system
# ---------------------------------------------------------------------------

def test_per_call_house_system_changes_cusps():
    default = immanuel_server.generate_natal_chart(*BIRTH, timezone=TZ)
    campanus = immanuel_server.generate_natal_chart(
        *BIRTH, timezone=TZ, house_system="CAMPANUS")
    assert not default.get("error") and not campanus.get("error")
    # Second house cusp differs between Placidus and Campanus at this location
    d2 = default["houses"]["2000002"]["longitude"]["raw"]
    c2 = campanus["houses"]["2000002"]["longitude"]["raw"]
    assert d2 != pytest.approx(c2, abs=1e-6)
    assert campanus["house_system"] == "Campanus"


def test_invalid_house_system_returns_structured_error_with_valid_values():
    result = immanuel_server.generate_natal_chart(
        *BIRTH, timezone=TZ, house_system="WHOLESIGN")
    assert result.get("error") is True
    assert "WHOLE_SIGN" in result["message"]
    assert "Whole Sign" in result["message"]


def test_per_call_override_leaves_global_settings_untouched():
    before = setup.settings.house_system
    immanuel_server.generate_natal_chart(*BIRTH, timezone=TZ, house_system="CAMPANUS")
    assert setup.settings.house_system == before


def test_applied_settings_echo_per_call_and_session_global():
    per_call = immanuel_server.generate_natal_chart(
        *BIRTH, timezone=TZ, house_system="KOCH")
    assert per_call["applied_settings"] == {
        "house_system": "Koch", "source": "per-call"}

    default = immanuel_server.get_chart_summary(*BIRTH, timezone=TZ)
    assert default["applied_settings"] == {
        "house_system": "Placidus", "source": "session-global"}


def test_house_system_threads_into_secondary_charts():
    # get_planetary_positions reports houses; a whole-sign call must place
    # planets in whole-sign houses, not Placidus ones.
    placidus = immanuel_server.get_planetary_positions(*BIRTH, timezone=TZ)
    whole = immanuel_server.get_planetary_positions(
        *BIRTH, timezone=TZ, house_system="WHOLE_SIGN")
    assert not placidus.get("error") and not whole.get("error")
    houses_p = {k: v["house"] for k, v in placidus["planets"].items()}
    houses_w = {k: v["house"] for k, v in whole["planets"].items()}
    assert houses_p != houses_w


def test_house_system_accepted_by_all_chart_tools():
    partner = ("1990-07-16 02:30:00", "48.85", "2.35")
    calls = [
        lambda: immanuel_server.generate_compact_natal_chart(
            *BIRTH, timezone=TZ, house_system="CAMPANUS"),
        lambda: immanuel_server.generate_solar_return_chart(
            *BIRTH, 2025, timezone=TZ, house_system="CAMPANUS"),
        lambda: immanuel_server.generate_compact_solar_return_chart(
            *BIRTH, 2025, timezone=TZ, house_system="CAMPANUS"),
        lambda: immanuel_server.generate_progressed_chart(
            *BIRTH, "2026-07-06 12:00:00", timezone=TZ, house_system="CAMPANUS"),
        lambda: immanuel_server.generate_compact_progressed_chart(
            *BIRTH, "2026-07-06 12:00:00", timezone=TZ, house_system="CAMPANUS"),
        lambda: immanuel_server.generate_composite_chart(
            *BIRTH, *partner, house_system="CAMPANUS"),
        lambda: immanuel_server.generate_compact_composite_chart(
            *BIRTH, *partner, house_system="CAMPANUS"),
        lambda: immanuel_server.generate_synastry_aspects(
            *BIRTH, *partner, house_system="CAMPANUS"),
        lambda: immanuel_server.generate_compact_synastry_aspects(
            *BIRTH, *partner, house_system="CAMPANUS"),
        lambda: immanuel_server.generate_transit_chart(
            "32.71", "-117.15", house_system="CAMPANUS"),
        lambda: immanuel_server.generate_compact_transit_chart(
            "32.71", "-117.15", house_system="CAMPANUS"),
        lambda: immanuel_server.generate_transit_to_natal(
            *BIRTH, "2026-07-04 12:00:00", house_system="CAMPANUS"),
        lambda: immanuel_server.generate_compact_transit_to_natal(
            *BIRTH, "2026-07-04 12:00:00", house_system="CAMPANUS"),
        lambda: lunar_return_module.generate_lunar_return_chart(
            *BIRTH, 2025, 1, timezone=TZ, house_system="CAMPANUS"),
        lambda: lunar_return_module.generate_compact_lunar_return_chart(
            *BIRTH, 2025, 1, timezone=TZ, house_system="CAMPANUS"),
    ]
    for call in calls:
        result = call()
        assert not result.get("error"), result
        assert result["applied_settings"]["house_system"] == "Campanus"
        assert result["applied_settings"]["source"] == "per-call"


# ---------------------------------------------------------------------------
# I2: natal cross-aspects on predictive charts
# ---------------------------------------------------------------------------

PROGRESSION_DATE = "2026-07-06 12:00:00"


def test_progressed_chart_carries_natal_cross_aspects():
    result = immanuel_server.generate_progressed_chart(
        *BIRTH, PROGRESSION_DATE, timezone=TZ)
    assert not result.get("error"), result
    cross = result["natal_cross_aspects"]
    assert cross, "expected progressed-to-natal aspects"
    for aspect in cross:
        assert "progressed_object" in aspect and "natal_object" in aspect
        assert aspect["priority"] in {"tight", "moderate", "loose"}
    # Known contact for this subject: progressed Sun conjunct natal MC (~1.0 orb)
    assert any(
        a["progressed_object"] == "Sun" and a["natal_object"] == "MC"
        and a["type"] == "Conjunction" and a["orb"] < 2.0
        for a in cross
    )
    # The chart's own internal aspects are untouched (nested dict keyed by object)
    assert isinstance(result["aspects"], dict)


def test_include_natal_aspects_false_yields_none():
    result = immanuel_server.generate_progressed_chart(
        *BIRTH, PROGRESSION_DATE, timezone=TZ, include_natal_aspects=False)
    assert not result.get("error"), result
    assert result["natal_cross_aspects"] is None


def test_compact_progressed_cross_aspects_respect_priority():
    tight = immanuel_server.generate_compact_progressed_chart(
        *BIRTH, PROGRESSION_DATE, timezone=TZ, aspect_priority="tight")
    moderate = immanuel_server.generate_compact_progressed_chart(
        *BIRTH, PROGRESSION_DATE, timezone=TZ, aspect_priority="moderate")
    assert not tight.get("error") and not moderate.get("error")
    assert all(a["orb"] <= 2.0 for a in tight["natal_cross_aspects"])
    assert all(2.0 < a["orb"] <= 5.0 for a in moderate["natal_cross_aspects"])
    summary = tight["natal_cross_aspect_summary"]
    assert summary["total_aspects"] == (
        summary["tight_aspects"] + summary["moderate_aspects"] + summary["loose_aspects"])


def test_solar_return_cross_aspects_use_return_object_labels():
    result = immanuel_server.generate_solar_return_chart(*BIRTH, 2025, timezone=TZ)
    assert not result.get("error"), result
    cross = result["natal_cross_aspects"]
    assert cross
    assert all("return_object" in a and "natal_object" in a for a in cross)


def test_lunar_return_cross_aspects_use_return_object_labels():
    result = lunar_return_module.generate_compact_lunar_return_chart(
        *BIRTH, 2025, 1, timezone=TZ)
    assert not result.get("error"), result
    cross = result["natal_cross_aspects"]
    assert cross
    assert all("return_object" in a and "natal_object" in a for a in cross)
    # Moon-to-natal-Moon conjunction is definitional for a lunar return
    assert any(
        a["return_object"] == "Moon" and a["natal_object"] == "Moon"
        and a["type"] == "Conjunction"
        for a in cross
    )


# ---------------------------------------------------------------------------
# I3: relocated solar and lunar returns
# ---------------------------------------------------------------------------

LONDON = ("51.5", "-0.12")


def test_relocated_solar_return_same_instant_different_ascendant():
    home = immanuel_server.generate_solar_return_chart(*BIRTH, 2025, timezone=TZ)
    reloc = immanuel_server.generate_solar_return_chart(
        *BIRTH, 2025, timezone=TZ,
        return_latitude=LONDON[0], return_longitude=LONDON[1])
    assert not home.get("error") and not reloc.get("error"), (home, reloc)

    # Same return moment: both charts express it in the birth timezone, so
    # the serialized return datetimes must be identical (sidereal_time is
    # location-dependent by definition and rightly differs).
    assert home["solar_return_date_time"]["datetime"] == \
        reloc["solar_return_date_time"]["datetime"]
    assert home["solar_return_date_time"]["timezone"] == \
        reloc["solar_return_date_time"]["timezone"]

    # Different houses: Ascendant moves with the location
    home_asc = home["objects"]["3000001"]["longitude"]["raw"]
    reloc_asc = reloc["objects"]["3000001"]["longitude"]["raw"]
    assert abs(home_asc - reloc_asc) > 1.0

    assert reloc["return_location"] == {
        "latitude": 51.5, "longitude": -0.12, "relocated": True}
    assert home["return_location"]["relocated"] is False


def test_relocated_lunar_return_same_instant_different_houses():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    home = lunar_return_module.generate_lunar_return_chart(
        *BIRTH, 2025, 1, timezone=TZ)
    reloc = lunar_return_module.generate_lunar_return_chart(
        *BIRTH, 2025, 1, timezone=TZ,
        return_latitude=LONDON[0], return_longitude=LONDON[1])
    assert not home.get("error") and not reloc.get("error"), (home, reloc)

    # Same absolute instant: home return_date is naive local (birth tz),
    # relocated return_date is aware local at the return location.
    home_utc = datetime.fromisoformat(home["lunar_return_info"]["return_date"]) \
        .replace(tzinfo=ZoneInfo(TZ)).astimezone(ZoneInfo("UTC"))
    reloc_utc = datetime.fromisoformat(reloc["lunar_return_info"]["return_date"]) \
        .astimezone(ZoneInfo("UTC"))
    assert abs((home_utc - reloc_utc).total_seconds()) < 60

    # Natal Moon longitude comes from the birth-location natal chart either way
    assert home["lunar_return_info"]["natal_moon_longitude"] == pytest.approx(
        reloc["lunar_return_info"]["natal_moon_longitude"])

    home_asc = home["objects"]["3000001"]["longitude"]["raw"]
    reloc_asc = reloc["objects"]["3000001"]["longitude"]["raw"]
    assert abs(home_asc - reloc_asc) > 1.0

    assert reloc["return_location"]["relocated"] is True


def test_unrelocated_returns_unchanged_from_v050():
    # Regression pin: omitting the relocation params keeps prior behaviour
    result = lunar_return_module.generate_lunar_return_chart(
        *BIRTH, 2025, 1, timezone=TZ)
    assert result["lunar_return_info"]["return_date"].startswith("2025-01-18T05:27")
    assert result["return_location"] == {
        "latitude": 32.71, "longitude": -117.15, "relocated": False}

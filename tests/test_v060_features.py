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

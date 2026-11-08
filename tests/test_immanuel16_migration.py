#!/usr/bin/env python3
"""
Regression tests for the immanuel 1.6 migration.

- immanuel.const.data.OBJECTS/HOUSES/ASPECTS became ints in 1.6 while the
  serialized keys stayed 'objects'/'houses'/'aspects'. Keying into ToJSON
  output with the constants left every compact chart empty, with no error.
- The settings singleton became a session charts.Config. Reset rebinds it,
  so it must be reached through get_session_config() and nothing else.
"""

import pathlib
import re

import pytest
from immanuel.const import chart as chart_const

import immanuel_server
from immanuel_mcp.charts import lunar_return
from immanuel_mcp.utils.settings import get_session_config, reset_global_settings

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

BIRTH = ("1990-01-15 14:30:00", "32.71", "-117.15")
TZ = "America/Los_Angeles"
PARTNER = ("1985-07-04 06:15:00", "51n30", "0w07")
PARTNER_TZ = "Europe/London"
TRANSIT_DATE = "2026-07-04 12:00:00"


# ---------------------------------------------------------------------------
# Compact charts must never come back hollow
# ---------------------------------------------------------------------------

COMPACT_CHARTS = {
    "natal": lambda: immanuel_server.generate_compact_natal_chart(*BIRTH, timezone=TZ),
    "solar_return": lambda: immanuel_server.generate_compact_solar_return_chart(
        *BIRTH, 2026, timezone=TZ),
    "progressed": lambda: immanuel_server.generate_compact_progressed_chart(
        *BIRTH, TRANSIT_DATE, timezone=TZ),
    "lunar_return": lambda: lunar_return.generate_compact_lunar_return_chart(
        *BIRTH, 2026, 7, timezone=TZ),
    "composite": lambda: immanuel_server.generate_compact_composite_chart(
        *BIRTH, *PARTNER, TZ, PARTNER_TZ),
    "transit": lambda: immanuel_server.generate_compact_transit_chart("32.71", "-117.15"),
}


@pytest.mark.parametrize("chart", sorted(COMPACT_CHARTS))
def test_compact_chart_blocks_are_populated(chart):
    result = COMPACT_CHARTS[chart]()
    assert result["status"] == "success", result.get("message")
    assert len(result["objects"]) >= 10
    assert len(result["houses"]) == 12
    assert result["aspects"], "compact aspects came back empty"


def test_compact_transit_to_natal_is_populated():
    result = immanuel_server.generate_compact_transit_to_natal(
        *BIRTH, TRANSIT_DATE, timezone=TZ)
    assert result["status"] == "success", result.get("message")
    assert len(result["transit_positions"]) >= 10
    assert result["transit_to_natal_aspects"], "transit-to-natal aspects came back empty"


def test_compact_synastry_is_populated():
    result = immanuel_server.generate_compact_synastry_aspects(
        *BIRTH, *PARTNER, TZ, PARTNER_TZ)
    assert result["status"] == "success", result.get("message")
    assert result["aspects"], "compact synastry aspects came back empty"


# ---------------------------------------------------------------------------
# Session Config: reset, isolation, locale
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_session():
    reset_global_settings()
    yield
    reset_global_settings()


def test_reset_takes_effect_on_the_next_chart(clean_session):
    immanuel_server.configure_immanuel_settings("house_system", "WHOLE_SIGN")
    before_reset = immanuel_server.generate_compact_natal_chart(*BIRTH, timezone=TZ)
    assert before_reset["applied_settings"]["house_system"] == "Whole Sign"
    whole_sign = immanuel_server.generate_compact_natal_chart(
        *BIRTH, timezone=TZ, house_system="WHOLE_SIGN")
    assert before_reset["houses"] == whole_sign["houses"]

    immanuel_server.reset_immanuel_settings()

    after_reset = immanuel_server.generate_compact_natal_chart(*BIRTH, timezone=TZ)
    assert after_reset["applied_settings"] == {
        "house_system": "Placidus", "source": "session-global"}
    # applied_settings is derived from the session Config, not from the
    # Config the chart was built with, so also check the chart itself: its
    # cusps must be Placidus cusps, not the Whole Sign ones from before.
    placidus = immanuel_server.generate_compact_natal_chart(
        *BIRTH, timezone=TZ, house_system="PLACIDUS")
    assert after_reset["houses"] == placidus["houses"]


def test_session_config_is_only_reached_through_the_accessor():
    """A module holding its own reference to _session_config would keep the
    pre-reset object and silently ignore every reset."""
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in [REPO_ROOT / "immanuel_server.py",
                     *(REPO_ROOT / "immanuel_mcp").rglob("*.py")]
        if path.name != "settings.py" or path.parent.name != "utils"
        if re.search(r"\b_session_config\b", path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_per_call_override_leaves_session_config_untouched(clean_session):
    before = get_session_config().house_system
    result = immanuel_server.generate_compact_natal_chart(
        *BIRTH, timezone=TZ, house_system="KOCH")
    assert result["applied_settings"] == {"house_system": "Koch", "source": "per-call"}
    assert get_session_config().house_system == before


def test_reset_restores_a_mutated_objects_list(clean_session):
    startup_objects = list(get_session_config().objects)
    get_session_config().objects.append(chart_const.CERES)
    assert len(get_session_config().objects) == len(startup_objects) + 1

    result = reset_global_settings()

    assert "objects" in result["changed"]
    assert list(get_session_config().objects) == startup_objects


def test_locale_round_trip(clean_session):
    result = immanuel_server.configure_immanuel_settings("locale", "pt_BR")
    assert result["status"] == "success", result.get("message")
    sun = immanuel_server.generate_compact_natal_chart(
        *BIRTH, timezone=TZ)["objects"]["4000001"]
    assert sun["sign"] == "Capricórnio"

    immanuel_server.reset_immanuel_settings()

    sun = immanuel_server.generate_compact_natal_chart(
        *BIRTH, timezone=TZ)["objects"]["4000001"]
    assert sun["sign"] == "Capricorn"

#!/usr/bin/env python3
"""
Regression tests for the 2026-07 audit fixes.

Each test pins one fixed defect so it cannot silently return:
- C1: aspect pagination classified by configured max orb instead of actual orb
- C2/C3: tool registration split across multiple FastMCP instances
- C4: DMS coordinates with seconds parsed to wrong positions
- C5: datetime parser dropped single-digit-hour times as timezone tokens
- M1: timezone parameter ignored in transit-to-natal
- M2: aspect direction lost / cross-aspects dropped by dedup
- M3: lifecycle movement (applying/separating) and estimated exact dates
- M5/M6: lunar return precision
- M7/minors: lifecycle attached to natal and lunar return responses

Run from the repo root: python -m pytest tests/test_audit_regressions.py
"""

import asyncio

import pytest

import immanuel_server
from immanuel_mcp.charts import lunar_return as lunar_return_module
from immanuel_mcp.pagination.helpers import classify_aspect_priority, get_actual_orb
from immanuel_mcp.utils.coordinates import parse_coordinate
from immanuel_mcp.utils.datetimes import parse_datetime_value

BIRTH = ("1990-01-15 14:30:00", "32.71", "-117.15")
TRANSIT_DATE = "2026-07-04 12:00:00"


# ---------------------------------------------------------------------------
# C4: coordinate parsing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("coord,is_lat,expected", [
    ("117w09'30", False, -117.15833),   # the corrupting case: was -132.5
    ("117w09", False, -117.15),
    ("32n43", True, 32.71667),
    ("32N43", True, 32.71667),
    ("51°23'30\"N", True, 51.39167),
    ("32 43 30 N", True, 32.725),
    ("32.71", True, 32.71),
    ("-117.15", False, -117.15),
    ("0w10", False, -0.16667),
])
def test_coordinate_formats(coord, is_lat, expected):
    assert parse_coordinate(coord, is_latitude=is_lat) == pytest.approx(expected, abs=1e-3)


@pytest.mark.parametrize("coord", ["117w75", "32n99", "abc", "117w0930", "200.0"])
def test_invalid_coordinates_rejected(coord):
    with pytest.raises(ValueError):
        parse_coordinate(coord, is_latitude=False)


# ---------------------------------------------------------------------------
# C5: datetime parsing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("2024-01-01 1:00", "2024-01-01 01:00:00"),    # was silently -> midnight
    ("2024-01-01 9:30", "2024-01-01 09:30:00"),
    ("2024-01-01 12:00:00 Europe/London", "2024-01-01 12:00:00"),
    ("2024-01-01 12:00:00 UTC", "2024-01-01 12:00:00"),
    ("2024-01-01 12:00:00+05:30", "2024-01-01 12:00:00"),
    ("2024-01-01 12:00:00Z", "2024-01-01 12:00:00"),
    ("2024-01-01", "2024-01-01 00:00:00"),
])
def test_datetime_parsing(value, expected):
    assert str(parse_datetime_value(value)) == expected


# ---------------------------------------------------------------------------
# C1: actual orb, not configured maximum
# ---------------------------------------------------------------------------

def test_get_actual_orb_full_serializer_shape():
    # ToJSON shape: 'orb' is the configured max, 'difference' the actual orb
    aspect = {"orb": 10.0, "difference": {"raw": 1.23}}
    assert get_actual_orb(aspect) == pytest.approx(1.23)
    assert classify_aspect_priority(aspect) == "tight"


def test_get_actual_orb_compact_serializer_shape():
    # Compact shape: 'orb' already holds the actual deviation
    assert get_actual_orb({"orb": -3.4}) == pytest.approx(3.4)
    assert classify_aspect_priority({"orb": -3.4}) == "moderate"


def test_transit_to_natal_tight_page_is_actually_tight():
    result = immanuel_server.generate_transit_to_natal(*BIRTH, TRANSIT_DATE)
    assert not result.get("error"), result
    aspects = result["transit_to_natal_aspects"]
    assert aspects, "tight page should not be empty for this chart"
    assert all(a["orb"] <= 2.0 for a in aspects)
    # With default settings virtually no aspect carries a configured max <= 2,
    # so a healthy tight page proves classification uses the actual orb.
    assert result["aspect_summary"]["tight_aspects"] >= 5


# ---------------------------------------------------------------------------
# C2/C3: single shared MCP instance with the full tool set
# ---------------------------------------------------------------------------

def test_all_tools_registered_on_shared_instance():
    import immanuel_mcp.server as modular_server
    from immanuel_mcp.app import mcp as shared

    assert immanuel_server.mcp is shared
    assert modular_server.mcp is shared

    tools = {t.name for t in asyncio.run(shared.list_tools())}
    assert len(tools) == 21
    assert "generate_lunar_return_chart" in tools
    assert "generate_compact_lunar_return_chart" in tools
    assert "reset_immanuel_settings" in tools


# ---------------------------------------------------------------------------
# M1: timezone honored in transit-to-natal
# ---------------------------------------------------------------------------

def test_transit_timezone_changes_positions():
    la = immanuel_server.generate_transit_to_natal(
        *BIRTH, TRANSIT_DATE, timezone="America/Los_Angeles")
    utc = immanuel_server.generate_transit_to_natal(
        *BIRTH, TRANSIT_DATE, timezone="UTC")
    assert not la.get("error") and not utc.get("error")
    assert la["transit_positions"]["Moon"]["position"] != utc["transit_positions"]["Moon"]["position"]


# ---------------------------------------------------------------------------
# M2: direction preserved, cross-aspects survive dedup
# ---------------------------------------------------------------------------

def test_full_transit_aspects_carry_direction():
    result = immanuel_server.generate_transit_to_natal(*BIRTH, TRANSIT_DATE)
    labels = [a["planets"] for a in result["transit_to_natal_aspects"]]
    assert labels and all(l.startswith("transit ") and " → natal " in l for l in labels)


def test_synastry_cross_aspects_survive_dedup():
    # This chart pair produces mirrored cross-contacts (e.g. A's Saturn to
    # B's Neptune AND A's Neptune to B's Saturn) which the old dedup dropped.
    result = immanuel_server.generate_compact_synastry_aspects(
        "1990-01-15 14:30:00", "32.71", "-117.15",
        "1990-07-16 02:30:00", "48.85", "2.35",
        include_interpretations=False,
    )
    aspects = result["aspects"]
    assert aspects
    # direction fields present
    assert all("native_object" in a and "partner_object" in a for a in aspects)
    # at least one planet pair + type appears twice with different orbs
    from collections import Counter
    keys = Counter(
        (tuple(sorted((a["object1"], a["object2"]))), a["type"]) for a in aspects
    )
    assert any(count > 1 for count in keys.values()), \
        "expected mirrored cross-aspects to survive deduplication"


def test_natal_chart_mirrored_duplicates_still_collapse():
    result = immanuel_server.generate_compact_natal_chart(*BIRTH)
    aspects = result["aspects"]
    seen = set()
    for a in aspects:
        key = (a["active"], a["passive"], a["type"], round(a["orb"], 4))
        assert key not in seen, f"duplicate natal aspect: {a}"
        seen.add(key)


# ---------------------------------------------------------------------------
# M3: lifecycle movement and estimated exact dates
# ---------------------------------------------------------------------------

def test_lifecycle_events_have_movement_and_estimated_dates():
    # 1985 birth at this transit date sits inside Pluto square / Neptune square
    result = immanuel_server.generate_compact_transit_to_natal(
        "1985-02-10 12:00:00", "51.5", "-0.17", TRANSIT_DATE)
    events = result.get("lifecycle_events") or []
    active = [e for e in events if e.get("status") == "active"]
    assert active, "expected active lifecycle events for a 41-year-old"
    for event in active:
        assert event.get("movement") in {"applying", "exact", "separating", "stationary"}
        assert event.get("exact_date_estimated") is True
        assert event.get("current_angular_separation") is not None


# ---------------------------------------------------------------------------
# M5/M6: lunar return precision; minors: lifecycle attachment
# ---------------------------------------------------------------------------

def test_lunar_return_precision():
    from immanuel import charts

    result = lunar_return_module.generate_lunar_return_chart(
        *BIRTH, 2025, 1, "America/Los_Angeles")
    assert not result.get("error"), result
    info = result["lunar_return_info"]

    subject = charts.Subject(
        date_time=info["return_date"].replace("T", " "),
        latitude=32.71, longitude=-117.15, timezone="America/Los_Angeles")
    moon = charts.Natal(subject).objects.get(4000002)
    diff = abs(moon.longitude.raw - info["natal_moon_longitude"])
    diff = min(diff, 360 - diff)
    # 0.01 deg of Moon motion is ~1 minute of clock time
    assert diff < 0.01, f"Moon {diff} deg from natal position at return moment"


def test_lunar_return_includes_lifecycle():
    result = lunar_return_module.generate_compact_lunar_return_chart(
        *BIRTH, 2025, 1, "America/Los_Angeles")
    assert not result.get("error")
    assert result.get("lifecycle_events"), "lunar return should carry lifecycle events"


def test_natal_chart_includes_lifecycle():
    result = immanuel_server.generate_compact_natal_chart(*BIRTH)
    assert not result.get("error")
    assert result.get("lifecycle_events"), "natal chart should carry lifecycle events"

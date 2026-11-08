#!/usr/bin/env python3
"""
Regression tests for the immanuel 1.6 migration.

- immanuel.const.data.OBJECTS/HOUSES/ASPECTS became ints in 1.6 while the
  serialized keys stayed 'objects'/'houses'/'aspects'. Keying into ToJSON
  output with the constants left every compact chart empty, with no error.
"""

import pytest

import immanuel_server
from immanuel_mcp.charts import lunar_return

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

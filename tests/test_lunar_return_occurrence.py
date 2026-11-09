#!/usr/bin/env python3
"""
A month can contain two lunar returns (the sidereal month is ~27.3 days).
For 1990 London, July 2026 has returns on 1 July and 28 July. The tools
always gave the first, and August gives 25 August, so 28 July was
unreachable. `occurrence` selects one, and `returns_in_month` lists them.
"""

from datetime import datetime

import pytest
import swisseph as swe
from immanuel.tools import date as date_tools

from immanuel_mcp.charts import lunar_return
from immanuel_mcp.utils.search import body_position
from immanuel_mcp.constants import PLANET_CONSTANTS

LONDON = ("1990-05-15 12:00:00", "51n30", "0w07")
TZ = "Europe/London"
TOOLS = {
    "full": lunar_return.generate_lunar_return_chart,
    "compact": lunar_return.generate_compact_lunar_return_chart,
}


def _natal_moon():
    result = lunar_return.generate_lunar_return_chart(*LONDON, 2026, 7, TZ)
    return result["lunar_return_info"]["natal_moon_longitude"]


@pytest.mark.parametrize("kind", sorted(TOOLS))
def test_july_2026_lists_both_returns(kind):
    result = TOOLS[kind](*LONDON, 2026, 7, TZ)
    assert result["status"] == "success", result.get("message")
    returns = result["lunar_return_info"]["returns_in_month"]
    assert [r[:10] for r in returns] == ["2026-07-01", "2026-07-28"]
    assert returns[0].startswith("2026-07-01T13:51")
    assert result["lunar_return_info"]["return_date"] == returns[0]
    assert result["lunar_return_info"]["occurrence"] == 1


@pytest.mark.parametrize("kind", sorted(TOOLS))
def test_occurrence_2_is_the_28_july_return(kind):
    result = TOOLS[kind](*LONDON, 2026, 7, TZ, occurrence=2)
    assert result["status"] == "success", result.get("message")
    info = result["lunar_return_info"]
    assert info["return_date"].startswith("2026-07-28")
    assert info["occurrence"] == 2
    local = datetime.fromisoformat(info["return_date"])
    jd = date_tools.to_jd(local, lat=51.5, lon=-0.1167, time_zone=TZ)
    moon = body_position(PLANET_CONSTANTS["Moon"], jd)["lon"]
    assert abs(swe.difdeg2n(moon, info["natal_moon_longitude"])) < 30 / 3600


@pytest.mark.parametrize("kind", sorted(TOOLS))
def test_an_occurrence_that_does_not_exist_names_the_ones_that_do(kind):
    result = TOOLS[kind](*LONDON, 2026, 7, TZ, occurrence=3)
    assert result.get("error") is True
    assert "2026-07-01T13:51" in result["message"] and "2026-07-28" in result["message"]


def test_a_one_return_month_lists_one():
    result = lunar_return.generate_compact_lunar_return_chart(*LONDON, 2026, 8, TZ)
    assert [r[:10] for r in result["lunar_return_info"]["returns_in_month"]] == ["2026-08-25"]

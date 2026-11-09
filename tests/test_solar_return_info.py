#!/usr/bin/env python3
"""
Solar return responses report when the return happens.

Neither tool said so (the full chart's native.date_time is the birth time),
so callers borrowed the moment from another engine. solar_return_info
.return_date mirrors lunar_return_info.return_date: naive ISO in the birth
timezone.
"""

from datetime import datetime

import pytest
import swisseph as swe
from immanuel.tools import date as date_tools

import immanuel_server
from immanuel_mcp.constants import PLANET_CONSTANTS
from immanuel_mcp.utils.search import body_position

LONDON = ("1990-05-15 12:00:00", "51n30", "0w07")
TZ = "Europe/London"


@pytest.mark.parametrize("build", [
    immanuel_server.generate_solar_return_chart,
    immanuel_server.generate_compact_solar_return_chart,
], ids=["full", "compact"])
def test_return_date_is_when_the_sun_is_back_on_its_natal_degree(build):
    result = build(*LONDON, 2026, TZ)
    assert result["status"] == "success", result.get("message")
    return_date = result["solar_return_info"]["return_date"]
    assert return_date.startswith("2026-05-15T05:04")
    natal = immanuel_server.generate_natal_chart(*LONDON, TZ)
    natal_sun = natal["objects"][str(PLANET_CONSTANTS["Sun"])]["longitude"]["raw"]
    jd = date_tools.to_jd(datetime.fromisoformat(return_date), lat=51.5, lon=-0.1167, time_zone=TZ)
    sun = body_position(PLANET_CONSTANTS["Sun"], jd)["lon"]
    assert abs(swe.difdeg2n(sun, natal_sun)) < 1 / 3600

"""Every tool that attaches lifecycle events can switch them off."""

import pytest

import immanuel_server as server
from immanuel_mcp.charts import lunar_return

BIRTH = dict(date_time="1985-06-21 14:30:00", latitude="51.5", longitude="-0.13", timezone="Europe/London")
TOOLS = [
    (server.generate_natal_chart, {}),
    (server.generate_compact_natal_chart, {}),
    (server.generate_solar_return_chart, dict(return_year=2026)),
    (server.generate_compact_solar_return_chart, dict(return_year=2026)),
    (server.generate_progressed_chart, dict(progression_date_time="2026-11-12 12:00:00")),
    (server.generate_compact_progressed_chart, dict(progression_date_time="2026-11-12 12:00:00")),
    (lunar_return.generate_lunar_return_chart, dict(return_year=2026, return_month=11)),
    (lunar_return.generate_compact_lunar_return_chart, dict(return_year=2026, return_month=11)),
]
IDS = [tool.__name__ for tool, _ in TOOLS]


@pytest.mark.parametrize("tool,extra", TOOLS, ids=IDS)
def test_lifecycle_on_by_default(tool, extra):
    result = tool(**BIRTH, **extra)
    assert result["status"] == "success", result
    assert result["lifecycle_events"]
    assert result["lifecycle_summary"]


@pytest.mark.parametrize("tool,extra", TOOLS, ids=IDS)
def test_lifecycle_switched_off(tool, extra):
    result = tool(**BIRTH, **extra, include_lifecycle_events=False)
    assert result["status"] == "success", result
    assert result["lifecycle_events"] is None
    assert result["lifecycle_summary"] is None

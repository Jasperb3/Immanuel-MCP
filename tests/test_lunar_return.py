#!/usr/bin/env python3
"""Test lunar return chart generation."""

import json

from immanuel_mcp.charts import lunar_return

BIRTH = dict(
    date_time="1990-01-15 14:30:00",
    latitude="32.71",
    longitude="-117.15",
    return_year=2025,
    return_month=1,
    timezone="America/Los_Angeles",
)


def test_full_lunar_return_chart():
    result = lunar_return.generate_lunar_return_chart(**BIRTH)

    assert not result.get('error'), result.get('message')
    assert 'lunar_return_info' in result
    info = result['lunar_return_info']
    assert info['return_date']
    assert 0 <= info['natal_moon_longitude'] < 360


def test_compact_lunar_return_chart_fits_mcp_limit():
    result = lunar_return.generate_compact_lunar_return_chart(**BIRTH)

    assert not result.get('error'), result.get('message')
    size_kb = len(json.dumps(result)) / 1024
    assert size_kb <= 50, f"compact lunar return is {size_kb:.1f} KB, over the MCP limit"

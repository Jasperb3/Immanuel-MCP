"""Tool text content is compact JSON, identical in data to the structured content."""

import asyncio
import json

import pytest

from immanuel_mcp import server  # noqa: F401  (registers the tools)
from immanuel_mcp.app import mcp

NATAL = dict(date_time="1990-01-15 12:00:00", latitude="78.22", longitude="15.63")


def _call(name, arguments):
    return asyncio.run(mcp.call_tool(name, arguments))


@pytest.mark.parametrize("name", ["generate_natal_chart", "generate_compact_natal_chart", "get_chart_summary"])
def test_text_is_compact_and_matches_structured(name):
    content, structured = _call(name, NATAL)
    assert len(content) == 1
    text = content[0].text
    assert json.loads(text) == structured["result"]
    assert len(text) < len(json.dumps(structured["result"], indent=2, ensure_ascii=False))
    assert "\n" not in text


def test_full_natal_text_is_a_third_smaller():
    content, structured = _call("generate_natal_chart", NATAL)
    indented = json.dumps(structured["result"], indent=2, ensure_ascii=False)
    assert len(content[0].text) <= 0.7 * len(indented)
    assert len(content[0].text) < 90_000


def test_errors_are_compact_too():
    content, structured = _call("generate_natal_chart", dict(NATAL, latitude="95"))
    assert json.loads(content[0].text)["status"] == "error"

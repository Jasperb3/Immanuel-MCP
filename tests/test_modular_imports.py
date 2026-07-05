#!/usr/bin/env python3
"""Verify the modular package structure imports correctly.

The tool functions live in immanuel_server.py and register against the
shared FastMCP instance in immanuel_mcp.app; the former _legacy_import
bridge is gone.
"""


def test_package_import():
    import immanuel_mcp
    assert immanuel_mcp.__version__


def test_shared_mcp_instance():
    from immanuel_mcp import mcp
    from immanuel_mcp.app import mcp as app_mcp
    import immanuel_server

    assert mcp is app_mcp
    assert immanuel_server.mcp is app_mcp


def test_constants_import():
    from immanuel_mcp import CELESTIAL_BODIES
    assert len(CELESTIAL_BODIES) == 20


def test_chart_functions_importable():
    from immanuel_server import generate_natal_chart
    from immanuel_mcp.charts.lunar_return import generate_lunar_return_chart

    assert callable(generate_natal_chart)
    assert callable(generate_lunar_return_chart)

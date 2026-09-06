"""Immanuel MCP Server - Modular astrology chart generation.

This package provides a Model Context Protocol (MCP) server that exposes
the Immanuel Python astrology library as a set of tools for chart generation.

Main Components:
- app: The shared FastMCP server instance
- server: Entry point that loads all tools onto the shared instance
- constants: CELESTIAL_BODIES mapping and other constants
- utils: Coordinate parsing, subject creation, error handling
- optimizers: Response optimization (positions, aspects, dignities)
- pagination: Aspect pagination helpers
- charts: Chart generation modules (natal, solar return, etc.)
- interpretations: Aspect interpretation data and logic

Usage:
    python -m immanuel_mcp

Note: this __init__ deliberately does NOT import .server. Tool modules
import subpackages like immanuel_mcp.lifecycle at load time, so an eager
.server import here would create a circular import chain.
"""

import pathlib
import re
from importlib import metadata

from .app import mcp
from .constants import CELESTIAL_BODIES


def _detect_version() -> str:
    """
    Read the version from the one place it is declared.

    Installed (wheel, or `uv sync`'s editable install): package metadata.
    Run from a source checkout that was never installed: pyproject.toml,
    which is where that metadata would have come from anyway. These two
    routes are complementary rather than redundant - pyproject.toml is
    absent from an installed wheel, and metadata is absent from a bare
    checkout - so between them the version is never a duplicated literal.
    """
    try:
        return metadata.version("immanuel-mcp-server")
    except metadata.PackageNotFoundError:
        pass

    # Regex rather than tomllib: this package supports Python 3.10, which
    # predates it, and the field is a plain top-level string.
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        match = re.search(
            r'^version = "([^"]+)"', pyproject.read_text(encoding="utf-8"), re.MULTILINE)
    except OSError:
        match = None
    if match is None:
        raise RuntimeError(
            "Cannot determine immanuel-mcp-server version: the package is not "
            f"installed and {pyproject} is missing or declares no version."
        )
    return match.group(1)


__version__ = _detect_version()
__all__ = ["mcp", "CELESTIAL_BODIES", "__version__"]

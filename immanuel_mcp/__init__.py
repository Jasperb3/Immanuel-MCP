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

from .app import mcp
from .constants import CELESTIAL_BODIES

__version__ = "0.5.0"
__all__ = ["mcp", "CELESTIAL_BODIES"]

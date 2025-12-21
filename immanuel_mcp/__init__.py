"""Immanuel MCP Server - Modular astrology chart generation.

This package provides a Model Context Protocol (MCP) server that exposes
the Immanuel Python astrology library as a set of tools for chart generation.

Main Components:
- server: MCP server setup and tool registration
- constants: CELESTIAL_BODIES mapping and other constants
- utils: Coordinate parsing, subject creation, error handling
- optimizers: Response optimization (positions, aspects, dignities)
- pagination: Aspect pagination helpers
- charts: Chart generation modules (natal, solar return, etc.)
- interpretations: Aspect interpretation data and logic

Usage:
    from immanuel_mcp import mcp

    if __name__ == "__main__":
        mcp.run()
"""

from .server import mcp
from .constants import CELESTIAL_BODIES

__version__ = "0.3.0"
__all__ = ["mcp", "CELESTIAL_BODIES"]

"""Shared FastMCP server instance.

This is the single source of truth for the MCP server object. Both entry
points (the top-level ``immanuel_server.py`` script and ``python -m
immanuel_mcp``) import this instance, and all ``@mcp.tool()`` decorators
register against it.

This module must stay a leaf: it may not import anything else from
immanuel_mcp or from immanuel_server, otherwise the circular imports this
module exists to prevent come back.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("immanuel-astrology-server")

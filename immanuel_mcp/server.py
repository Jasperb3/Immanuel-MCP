#!/usr/bin/env python3
"""MCP Server for Immanuel Astrology Library - Modular Version

Entry point for ``python -m immanuel_mcp``. All tools register themselves
against the shared FastMCP instance in ``immanuel_mcp.app`` when their
defining modules are imported below, so this entry point and the top-level
``immanuel_server.py`` script serve an identical tool set.
"""

import logging

from .app import mcp

logger = logging.getLogger(__name__)

# Importing immanuel_server executes all @mcp.tool() decorators against the
# shared instance. It also imports immanuel_mcp.charts.lunar_return itself,
# so the lunar return tools are registered too.
import immanuel_server  # noqa: E402,F401


def main():
    """Main entry point when running as a module or script."""
    logger.info("Starting Immanuel Astrology MCP Server (modular version)")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""MCP Server for Immanuel Astrology Library - Modular Version

This module provides the main MCP server instance that registers all
astrology tools from the modular immanuel_mcp package structure.
"""

import logging
from mcp.server.fastmcp import FastMCP

# Configure logging to file only (avoid stdout interference with MCP stdio)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('immanuel_mcp.log'),
    ]
)

logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP("immanuel-astrology-server")

# Import all chart generation functions from the legacy bridge
# These will be migrated to individual chart modules incrementally
from .charts._legacy_import import (
    # Natal
    generate_natal_chart,
    generate_compact_natal_chart,
    get_chart_summary,
    get_planetary_positions,

    # Solar Return
    generate_solar_return_chart,
    generate_compact_solar_return_chart,

    # Progressed
    generate_progressed_chart,
    generate_compact_progressed_chart,

    # Composite
    generate_composite_chart,
    generate_compact_composite_chart,

    # Synastry
    generate_synastry_aspects,
    generate_compact_synastry_aspects,

    # Transit
    generate_transit_chart,
    generate_compact_transit_chart,

    # Transit to Natal
    generate_transit_to_natal,
    generate_compact_transit_to_natal,

    # Configuration
    configure_immanuel_settings,
    list_available_settings,
)

# Import new chart modules (these auto-register their tools via @mcp.tool() decorators)
from .charts import lunar_return  # Lunar return charts - first native modular chart type

# Register all tools with the MCP server
# The @mcp.tool() decorators in the original functions handle registration
# Since we're importing decorated functions, they're already registered

def main():
    """Main entry point when running as a module or script."""
    logger.info("Starting Immanuel Astrology MCP Server (modular version)")
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()

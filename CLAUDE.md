# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that exposes the Immanuel Python astrology library as a set of tools. The server provides comprehensive astrological chart generation capabilities including natal charts, solar returns, progressions, composite charts, synastry aspects, and transit charts.

## Core Architecture

### Single-File Server Design
- **Main Server**: `immanuel_server.py` - Contains all MCP tools and server logic
- **Architecture**: FastMCP-based server with 7 main astrology tools
- **Key Components**:
  - MCP tool decorators expose functions as callable tools
  - Coordinate parsing system supporting multiple formats
  - Chart generation wrapper functions around Immanuel library
  - Error handling with standardized error responses

### Dependencies
- **Core**: `mcp[cli]` (MCP server framework), `immanuel` (astrology calculations)
- **Python**: Requires Python 3.10+
- **Package Manager**: Uses `uv` for dependency management

## Development Commands

### Server Operations
```bash
# Install dependencies
uv sync

# Run the server directly
uv run immanuel_server.py

# Run as installed package
uv run immanuel-mcp
```

### Testing the Server
```bash
# Basic server test (should start without errors)
uv run immanuel_server.py

# Test with MCP client tools if available
mcp run immanuel_server.py
```

## MCP Tool Interface

### Chart Generation Tools
- `generate_natal_chart` - Birth charts with planets, houses, and aspects
- `generate_solar_return_chart` - Annual solar return charts
- `generate_progressed_chart` - Secondary progression charts
- `generate_composite_chart` - Relationship midpoint charts
- `generate_synastry_aspects` - Inter-chart aspects between two people
- `generate_transit_chart` - Current planetary positions for a location

### Configuration Tool
- `configure_immanuel_settings` - Modify global Immanuel library settings (house systems, orbs, celestial objects)

## Coordinate System

### Supported Formats
- **Traditional**: `32n43` (32°43'N), `117w09` (117°09'W)
- **Decimal**: `32.71`, `-117.15`
- **Directions**: N/S for latitude, E/W for longitude

### Parsing Logic
The `parse_coordinate()` function handles format conversion and validation. Southern latitudes and western longitudes use negative values.

## Error Handling Strategy

### Standardized Error Response
All chart generation functions use `handle_chart_error()` to return consistent error structures:
```python
{
    "error": True,
    "message": "Error description",
    "type": "ExceptionType"
}
```

### Common Error Sources
- Invalid coordinate formats
- Invalid date/time formats (expects ISO format)
- Immanuel library calculation errors
- Timezone parsing issues

## Configuration Integration

### Claude Desktop Setup
The server is designed to run via Claude Desktop's MCP configuration. The `cwd` parameter in the Claude config must point to this directory, and the command should use `uv run immanuel_server.py`.

### Runtime Configuration
The `configure_immanuel_settings` tool allows dynamic modification of astrology calculation parameters without restarting the server.

## Data Flow

1. **Input**: MCP client sends tool calls with astrological parameters
2. **Parsing**: Coordinates and datetime strings are parsed and validated
3. **Subject Creation**: Immanuel Subject objects are created with location/time data
4. **Chart Generation**: Appropriate Immanuel chart class is instantiated
5. **Serialization**: Chart objects are converted to JSON via `to_json()`
6. **Response**: JSON data is returned to the MCP client

## Development Notes

### Adding New Chart Types
1. Create a new `@mcp.tool()` decorated function
2. Follow the existing pattern for parameter parsing
3. Use `handle_chart_error()` for consistent error handling
4. Return `json.loads(chart.to_json())` for serialization

### Modifying Settings Support
New Immanuel settings can be added to `configure_immanuel_settings()` by extending the conditional logic that handles different setting types (constants, lists, numeric values, etc.).
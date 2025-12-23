# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python Virtual Environment Management (WSL + Windows Integration)

When developing an MCP (Model Context Protocol) Python project that will be deployed to Claude Desktop on Windows, but where development happens in a WSL (Windows Subsystem for Linux) environment, careful attention must be paid to virtual environment configuration. **The Python virtual environment should reside on the Windows C: Drive (not within WSL's filesystem), and should be a Windows-native Python environment, not the WSL Python interpreter.** This ensures that the Claude Desktop app running on Windows can directly access and activate the virtual environment without path translation issues or cross-platform compatibility problems. To set this up: (1) Install Python directly on Windows (not just in WSL) and verify the installation with `python --version` and `where python` from a Windows Command Prompt or PowerShell; (2) Create the virtual environment on the Windows filesystem using the Windows Python interpreter, typically in your project root with `C:\path\to\windows\python.exe -m venv venv` executed from Windows PowerShell or by using the full Windows path from WSL; (3) From WSL, activate and manage dependencies using the Windows venv with `source /mnt/c/path/to/project/venv/Scripts/activate` (note the /mnt/c prefix for C: drive access and Scripts folder for Windows venv structure); (4) When the MCP server runs in Claude Desktop on Windows, configure it to use the full Windows path to the venv Python executable (e.g., `C:\Users\YourUsername\path\to\project\venv\Scripts\python.exe`) rather than a relative or WSL path; (5) In your MCP server configuration file (typically claude_desktop_config.json or similar), specify the Windows-native paths explicitly and avoid any WSL path references. This approach eliminates confusion between WSL and Windows Python environments, prevents "command not found" errors when Claude Desktop tries to launch the MCP server, and ensures all installed packages are compatible with the Windows Python runtime that will actually execute the code. When committing to version control, always add the venv directory to .gitignore, and document the exact Windows Python version and any platform-specific dependencies in your project README for other contributors.

## Project Overview

This is an MCP (Model Context Protocol) server that exposes the Immanuel Python astrology library as a set of tools. The server provides comprehensive astrological chart generation capabilities including natal charts, solar returns, progressions, composite charts, synastry aspects, and transit charts.

## Core Architecture

### Modular Package Structure (v0.3.0+)
- **Package**: `immanuel_mcp/` - Modular astrology server package
- **Entry Points**:
  - `immanuel_server.py` - Original single-file server (maintained for compatibility)
  - `python -m immanuel_mcp` - New modular package entry point
- **Architecture**: FastMCP-based server with 18 main astrology tools (9 full + 9 compact)
- **Package Structure**:
  ```
  immanuel_mcp/
  ├── __init__.py                    # Package initialization
  ├── server.py                      # MCP server setup and registration
  ├── constants.py                   # CELESTIAL_BODIES mapping
  ├── utils/                         # Utility functions
  │   ├── coordinates.py             # parse_coordinate, validate_inputs
  │   ├── subjects.py                # create_subject helper
  │   └── errors.py                  # handle_chart_error
  ├── optimizers/                    # Response optimization
  │   ├── positions.py               # format_position, optimized transit positions
  │   ├── aspects.py                 # build_optimized_aspects
  │   └── dignities.py               # extract_primary_dignity, build_dignities_section
  ├── pagination/                    # Aspect pagination
  │   └── helpers.py                 # classify_aspect_priority, build_pagination_object
  ├── charts/                        # Chart generation
  │   ├── _legacy_import.py          # Temporary bridge to original implementation
  │   └── lunar_return.py            # 🆕 Lunar return charts (native modular implementation)
  ├── lifecycle/                     # 🆕 Lifecycle events detection (v0.4.0)
  │   ├── __init__.py                # Package exports
  │   ├── constants.py               # Orbital periods, significance levels, keywords
  │   ├── returns.py                 # Planetary return calculations
  │   ├── transits.py                # Major life transit detection
  │   ├── timeline.py                # Future predictions and lifecycle stages
  │   └── lifecycle.py               # Master orchestration function
  └── interpretations/               # Aspect interpretations
      └── aspects.py                 # ASPECT_INTERPRETATIONS, context-aware interpretations
  ```
- **Key Components**:
  - MCP tool decorators expose functions as callable tools
  - Coordinate parsing system supporting multiple formats
  - Chart generation wrapper functions around Immanuel library
  - Custom compact serializer for optimized chart output (84.9% size reduction)
  - Error handling with standardized error responses
  - Intelligent aspect pagination for transit-to-natal
  - **🆕 Lifecycle events detection system**: Automatic detection of planetary returns and major life transits

### Dependencies
- **Core**: `mcp[cli]` (MCP server framework), `immanuel` (astrology calculations)
- **Custom**: `compact_serializer.py` (streamlined chart output for LLM optimization)
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
- `generate_natal_chart` - Full birth charts with complete astrological data
- `generate_compact_natal_chart` - Streamlined natal charts for faster processing and reduced token usage
- `get_chart_summary` - Essential chart information (Sun/Moon/Rising signs, chart shape, moon phase)
- `get_planetary_positions` - Simplified planetary positions in signs and houses
- `generate_solar_return_chart` - Annual solar return charts
- `generate_compact_solar_return_chart` - Streamlined solar return charts
- `generate_lunar_return_chart` - **🆕 NEW**: Monthly lunar return charts (Moon returns to natal position)
- `generate_compact_lunar_return_chart` - **🆕 NEW**: Streamlined lunar return charts
- `generate_progressed_chart` - Secondary progression charts
- `generate_compact_progressed_chart` - Streamlined progressed charts
- `generate_composite_chart` - Relationship midpoint charts
- `generate_compact_composite_chart` - Streamlined composite charts
- `generate_synastry_aspects` - Inter-chart aspects between two people
- `generate_compact_synastry_aspects` - Filtered synastry aspects (major objects and aspects only)
- `generate_transit_chart` - Current planetary positions for a location
- `generate_compact_transit_chart` - Streamlined transit charts
- `generate_transit_to_natal` - Full transit-to-natal aspects with intelligent pagination
- `generate_compact_transit_to_natal` - Streamlined transit-to-natal with interpretations

### Transit-to-Natal Pagination System

The `generate_transit_to_natal` endpoint includes intelligent pagination to comply with MCP transport limits (~50 KB) while organizing aspects by astrological significance.

**Pagination Parameters:**
- `aspect_priority: str = "tight"` - Priority tier to return
  - `"tight"`: 0-2° orb aspects (most critical, peak influence)
  - `"moderate"`: 2-5° orb aspects (secondary priority, building/waning influence)
  - `"loose"`: 5-8° orb aspects (background influences, subtle themes)
  - `"all"`: Return all aspects (warning: may exceed MCP size limits)
- `include_all_aspects: bool = False` - Override filtering and return all aspects

**Response Structure Enhancements:**
- `aspect_summary`: Counts for tight/moderate/loose/total aspects
- `pagination`: Current page, total pages, has_more_aspects, next_page, navigation instructions

**Default Behavior:**
Without specifying `aspect_priority`, the endpoint returns only tight aspects (0-2° orb), ensuring the response stays well under MCP limits while providing the most astrologically significant transits.

### Lifecycle Events Detection System (✅ v0.4.0 - Production Ready)

All chart types (Transit-to-Natal, Solar Return, Progressed) include comprehensive lifecycle events detection, automatically identifying planetary returns and major life transits to provide context about where someone is in their astrological life journey.

**What is Detected:**
- **Planetary Returns**: Saturn Return, Jupiter Return, Uranus Opposition, Chiron Return, etc.
- **Major Life Transits**: Uranus Opposition (midlife ~41), Neptune Square (~39), Pluto Square (~36)
- **Future Timeline**: Upcoming returns and transits (10-20 years ahead)
- **Lifecycle Stage**: Current life phase based on age and active transits

**Parameter:**
- `include_lifecycle_events: bool = True` - Enable/disable lifecycle detection (default: enabled)

**Response Structure:**
```json
{
  "lifecycle_events": [
    {
      "event_type": "Saturn Return Cycle 1",
      "natal_object": "Saturn",
      "transiting_object": "Saturn",
      "aspect_type": "Conjunction",
      "current_angular_separation": 1.2,
      "orb_status": "applicative",
      "exact_date": "2025-01-15",
      "date_range": "2024-11-20 to 2025-03-12",
      "age_at_event": 29.5,
      "years_until_event": 0.0,
      "significance": "CRITICAL",
      "keywords": ["maturity", "responsibility", "karma", "structure"],
      "status": "active",
      "category": "return"
    }
  ],
  "lifecycle_summary": {
    "current_age": 29.5,
    "current_stage": {
      "stage_name": "Saturn Return",
      "description": "Karmic maturation and life restructuring",
      "age_range": [29, 31],
      "themes": ["responsibility", "maturity", "commitment"]
    },
    "active_event_count": 1,
    "next_major_event": "Jupiter Return Cycle 3",
    "years_until_event": 0.6,
    "next_major_event_date": "2025-08-15"
  }
}
```

**Field Definitions:**
- `current_angular_separation`: Degrees (0-180°) between current and exact position. NOT traditional astrological orb, but actual angular distance remaining until the event becomes exact.
- `orb_status`: "applicative" (approaching), "exact" (< 0.5°), or "separative" (past exact)
- `status`: "active" (happening now), "upcoming" (future), or "past" (historical)
- `category`: "return" (planetary return) or "major_transit" (square/opposition)

**Significance Levels:**
- **CRITICAL**: Saturn Returns, Uranus Opposition, Neptune Square, Pluto Square
- **HIGH**: Jupiter Returns (esp. 1st-3rd), Chiron Return/Opposition
- **MODERATE**: Other tracked returns and transits
- **LOW**: Infrequent or less impactful returns

**Tracked Planets:**
- Primary: Jupiter, Saturn, Uranus, Neptune, Pluto, Chiron
- Optional: Sun (solar return), Mars (~2yr), North Node (~18.6yr)

**Size Impact:**
- Adds ~3-5 KB to response (well within MCP 50 KB limit)
- Graceful degradation: If detection fails, lifecycle_events = null
- Can be disabled with `include_lifecycle_events=False`

**Chart Type Support:**
Lifecycle events are available in:
- ✅ Transit-to-Natal (full and compact)
- ✅ Solar Return (full and compact)
- ✅ Progressed (full and compact)
- ✅ Lunar Return (full and compact)

**Claude Desktop Integration:**
The lifecycle events are automatically included in all supported chart responses, providing Claude with rich context about the person's life stage. For example, when someone asks "What are my transits today?", Claude can naturally incorporate lifecycle context like "You're currently in your Saturn Return—one of the most significant astrological transits of your life!"

**Response Sizes (typical):**
- Tight: ~25 KB (2-10 aspects)
- Moderate: ~33 KB (10-20 aspects)
- Loose: ~48 KB (20-50 aspects)
- All: ~59 KB (exceeds MCP limit)

**Usage Example:**
```python
# Get most critical transits (default)
result = generate_transit_to_natal(natal_date_time="...", ...)
# Returns tight aspects with pagination.next_page = "moderate"

# Get secondary transits
result = generate_transit_to_natal(..., aspect_priority="moderate")
# Returns moderate aspects with pagination.next_page = "loose"

# Get background influences
result = generate_transit_to_natal(..., aspect_priority="loose")
# Returns loose aspects with pagination.has_more_aspects = False
```

### Lunar Return Charts (🆕 v0.3.0)

Lunar return charts are a monthly predictive technique that calculates the chart for the moment when the transiting Moon returns to its exact natal position. This happens approximately every 27-28 days (one sidereal lunar month).

**Astrological Significance:**
- **Monthly Themes**: Shows energies and themes for the coming lunar month
- **Timing**: Each lunar return marks the beginning of a new monthly cycle
- **Precision**: Calculated to within 1 minute of the exact Moon return moment
- **Application**: Used for monthly forecasting, similar to how solar returns are used for annual forecasting

**Implementation Details:**
- Custom algorithm finds the exact moment of Moon return within the specified month
- Uses binary search refinement to pinpoint the return time within 1-minute accuracy
- Generates a standard natal chart for the return moment
- Includes metadata: return_date, natal_moon_longitude, return_year, return_month

**Function Signatures:**

```python
@mcp.tool()
def generate_lunar_return_chart(
    date_time: str,          # Birth date and time (ISO format)
    latitude: str,           # Birth location latitude
    longitude: str,          # Birth location longitude
    return_year: int,        # Year for lunar return (e.g., 2025)
    return_month: int,       # Month for lunar return (1-12)
    timezone: str = None     # Optional IANA timezone
) -> Dict[str, Any]:
    """Full lunar return chart with all positions and aspects"""

@mcp.tool()
def generate_compact_lunar_return_chart(
    # Same parameters as above
) -> Dict[str, Any]:
    """Compact lunar return with 84.9% size reduction (18 KB typical)"""
```

**Usage Example:**
```python
# Calculate January 2025 lunar return
result = generate_lunar_return_chart(
    date_time="1990-01-15 14:30:00",
    latitude="32.71",
    longitude="-117.15",
    return_year=2025,
    return_month=1,
    timezone="America/Los_Angeles"
)
# Returns: return_date: "2025-01-18T04:57:04"
#          natal_moon_longitude: 172.94
#          Full chart data...
```

**Response Size:**
- Full version: ~40 KB (complete chart data)
- Compact version: ~18 KB (major objects and aspects only)

### Configuration Tools
- `configure_immanuel_settings` - Modify global Immanuel library settings (house systems, orbs, celestial objects)
- `list_available_settings` - View current Immanuel library settings

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

The server is designed to run via Claude Desktop's MCP configuration. Based on the working configuration and troubleshooting guide, use the following setup:

#### Windows Configuration
Add this to your Claude Desktop config file (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "immanuel-astrology": {
      "command": "C:\\Users\\[USERNAME]\\.local\\bin\\uv.exe",
      "args": ["--directory", "C:\\Users\\[USERNAME]\\Documents\\MCP\\astro-mcp", "run", "python", "immanuel_server.py"]
    }
  }
}
```

**Key Configuration Elements:**
- **Full path to uv executable**: `C:\\Users\\[USERNAME]\\.local\\bin\\uv.exe`
- **`--directory` flag**: Specifies the project directory (replaces `cwd` parameter)
- **Relative file path**: `immanuel_server.py` (works because directory is specified)
- **No `cwd` parameter**: Not needed with `--directory` flag

#### Linux/macOS Configuration
Add this to your Claude Desktop config file (`~/.config/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "immanuel-astrology": {
      "command": "/home/[USERNAME]/.local/bin/uv",
      "args": ["--directory", "/home/[USERNAME]/astro-mcp", "run", "python", "immanuel_server.py"]
    }
  }
}
```

#### Prerequisites
Before configuring Claude Desktop:
1. **Install dependencies**: Run `uv sync` in the project directory
2. **Verify installation**: Check `uv pip list` shows `immanuel` and `mcp[cli]`
3. **Test server**: Run `uv run immanuel_server.py` to verify it starts without errors

#### Common Configuration Issues
- **"Failed to spawn" errors**: Use full path to uv executable
- **"ModuleNotFoundError"**: Run `uv sync` to install dependencies
- **File path errors**: Use `--directory` flag instead of `cwd` parameter
- **Server not found**: Restart Claude Desktop after configuration changes

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
4. For full charts: Return `json.loads(json.dumps(chart, cls=ToJSON))`
5. For compact charts: Return `json.loads(json.dumps(chart, cls=CompactJSONSerializer))`

### Chart Output Options
- **Full Charts**: Use `ToJSON` serializer for complete astrological data
- **Compact Charts**: Use `CompactJSONSerializer` for streamlined output optimized for LLM token efficiency

### Compact Chart Design
The `CompactJSONSerializer` filters chart data to include:
- **Major Objects Only**: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Ascendant, Midheaven
- **Major Aspects Only**: Conjunction, Opposition, Square, Trine, Sextile
- **Essential Data**: Object positions, house placements, aspect orbs
- **Excluded**: Minor asteroids, detailed weightings, chart shape analysis, moon phase details

### Modifying Settings Support
New Immanuel settings can be added to `configure_immanuel_settings()` by extending the conditional logic that handles different setting types (constants, lists, numeric values, etc.).
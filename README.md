# Immanuel MCP Server

A Model Context Protocol (MCP) server that exposes the powerful [Immanuel Python astrology library](https://github.com/theriftlab/immanuel-python) as a set of tools accessible to MCP-compatible clients like Claude Desktop.

**v0.6.0 · 21 tools · 112 tests passing · tropical zodiac, structured data only** (see [Scope and Division of Labour](#scope-and-division-of-labour)). See [`CHANGELOG.md`](CHANGELOG.md) for release history.

## Features

### Chart Generation Tools
- **Natal Charts**: Complete birth charts with houses, planets, and aspects (full and compact variants)
- **Chart Summaries**: Essential information (Sun/Moon/Rising signs, chart shape, moon phase)
- **Planetary Positions**: Simplified planetary positions in signs and houses
- **Solar Returns**: Annual solar return charts, with optional relocation (full and compact variants)
- **Lunar Returns**: Monthly lunar return charts, found by ephemeris search to sub-minute precision, with optional relocation (full and compact variants)
- **Progressions**: Secondary progression charts (full and compact variants)
- **Composite Charts**: Relationship midpoint charts (full and compact variants)
- **Synastry Aspects**: Inter-chart aspects between two people (full and compact variants)
- **Transit Charts**: Current planetary positions for any location (full and compact variants)
- **Transit-to-Natal**: Transiting aspects to a natal chart, with intelligent orb-based pagination (full and compact variants)

Compact variants filter output to major objects (Sun through Pluto, Ascendant, Midheaven) and major aspects (Conjunction, Opposition, Square, Trine, Sextile) for reduced LLM token usage — see [Chart Output Options](#chart-output-options) below.

Every chart-generating tool accepts a per-call `house_system` override and returns a `status`/`applied_settings` response envelope — see [Common parameters and response envelope](#common-parameters-and-response-envelope-v060) in the Tool Reference.

### Chart Output Options
- **Full Charts**: Complete astrological data with all objects, aspects, and detailed properties
- **Compact Charts**: Filtered data focusing on major planets and aspects for LLM optimization

### Lifecycle Events Detection
- **Automatic Detection**: Identifies planetary returns (Saturn Return, Jupiter Return, etc.) and major life transits
- **Life Stage Context**: Shows where you are in your astrological life journey
- **Future Timeline**: Predicts upcoming returns and transits (10-20 years ahead)
- **Significance Levels**: Prioritizes events by astrological importance (CRITICAL, HIGH, MODERATE, LOW)
- **Major Transits Tracked**:
  - Saturn Return (ages 29-30, 58-60, 87-90) - Karmic maturation
  - Uranus Opposition (age 41-42) - Midlife awakening
  - Neptune Square (age 39-40) - Spiritual crisis/awakening
  - Pluto Square (age 36-37) - Deep transformation
  - Chiron Return (age 50+) - Wounded healer emergence
  - Jupiter Returns every ~12 years - Expansion and growth
- **Universal Integration**: Available in Natal, Transit-to-Natal, Solar Return, Lunar Return, and Progressed charts
- **Size Efficient**: Adds only ~3-5 KB to responses while providing rich context
- **Angular Separation**: Shows current distance (0-180°) from exact event occurrence

### Configuration
- Dynamically configure all Immanuel library settings (house systems, orbs, calculation methods, etc.)
- View current settings and available options

## Installation

### Prerequisites

#### All Platforms
- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager

### Platform-Specific Installation

#### Windows

1. **Install Python** (if not already installed):
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

2. **Install uv**:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Clone or download this repository**:
   ```powershell
   git clone https://github.com/Jasperb3/Immanuel-MCP.git
   cd Immanuel-MCP
   ```

#### Linux/macOS

1. **Install Python** (if not already installed):
   - macOS: `brew install python@3.10` (using Homebrew)
   - Linux: `sudo apt install python3.10` (Ubuntu/Debian) or use your distribution's package manager

2. **Install uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Clone or download this repository**:
   ```bash
   git clone https://github.com/Jasperb3/Immanuel-MCP.git
   cd Immanuel-MCP
   ```

#### Windows Subsystem for Linux (WSL)

Follow the Linux instructions above within your WSL environment.

### Server Setup

1. **Navigate to the project directory**:
   ```bash
   cd Immanuel-MCP
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Test the server**:
   ```bash
   uv run immanuel_server.py
   # or, equivalently, the modular package entry point:
   uv run python -m immanuel_mcp
   ```

   Both commands register the identical set of 21 tools against the same server. You should see the server start without errors. Press `Ctrl+C` to stop it.

## Claude Desktop Configuration

### Prerequisites

Before configuring Claude Desktop, ensure you have:

1. **Installed dependencies**: Run `uv sync` in the project directory
2. **Verified installation**: Check `uv pip list` shows `immanuel`, `mcp[cli]` and `tzdata`
3. **Tested the server**: Run `uv run immanuel_server.py` to verify it starts without errors

### Windows

1. **Locate the configuration file**:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Add the server configuration**:
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

   **Replace `[USERNAME]` with your actual Windows username.**

### macOS and Linux

1. **Locate the configuration file**:
   ```
   ~/.config/Claude/claude_desktop_config.json
   ```

2. **Add the server configuration**:
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

   **On macOS, use `/Users/[USERNAME]/.local/bin/uv` for the command path.**

3. **Save and restart**: Save the file and restart Claude Desktop.

### Configuration Notes

- **Use full paths**: Always specify the complete path to the `uv` executable
- **`--directory` flag**: This replaces the `cwd` parameter and ensures proper project context
- **No `cwd` needed**: The `--directory` flag handles working directory specification
- **Restart required**: Always restart Claude Desktop after configuration changes

## Usage Examples

Once configured, you can use the Immanuel tools in Claude Desktop by asking Claude to generate astrological charts. Here are some examples:

### Generate a Natal Chart

#### Full Natal Chart
```
"Generate a natal chart for someone born on January 1, 1990 at 3:30 PM in 
San Diego, California (coordinates: 32n43, 117w09)"
```

#### Compact Natal Chart (Optimized for LLM Processing)
```
"Generate a compact natal chart for someone born on January 1, 1990 at 3:30 PM in 
San Diego, California (coordinates: 32n43, 117w09)"
```

**Compact Chart Benefits:**
- Faster processing and reduced token usage
- Focuses on major planets only (Sun through Pluto, Ascendant, Midheaven)
- Includes only major aspects (Conjunction, Opposition, Square, Trine, Sextile)
- Excludes minor asteroids, detailed weightings, and chart shape analysis

The server accepts coordinates in multiple formats:
- Traditional: `32n43` (32°43'N), `117w09` (117°09'W)
- Decimal: `32.71`, `-117.15`

### Generate a Solar Return Chart

```
"Create a solar return chart for 2024 for someone born on March 15, 1985 
at 10:00 AM in New York City (40n42, 74w00)"
```

### Calculate Synastry Aspects

```
"Calculate the synastry aspects between:
Person 1: Born June 10, 1988 at 2:15 PM in London (51n30, 0w07)
Person 2: Born November 22, 1990 at 9:45 AM in Paris (48n52, 2e20)"
```

### Generate Current Transits

```
"Show me the current planetary positions for Los Angeles (34n03, 118w15)"
```

### Configure Settings

```
"Change the house system to Whole Sign houses"
"Set the orb for conjunctions to 8 degrees"
"Include Chiron and Lilith in all charts"
```

## Tool Reference

### Common parameters and response envelope (v0.6.0)

Every chart tool accepts, in addition to the parameters listed per tool:
- `timezone`: Optional IANA timezone name (e.g., "Europe/London"). Inferred from coordinates when omitted.
- `house_system`: Optional house system **for that call only** (e.g., "CAMPANUS", "WHOLE_SIGN"). Applied to every chart built within the call without touching the session-global settings; an invalid name returns an error listing all 23 valid values. Per-call overrides start from library defaults and deliberately ignore session-level `configure_immanuel_settings` changes.

Every response carries:
- `status`: `"success"` or `"error"` (error responses keep the existing `error`/`message`/`type`/`suggestion` keys).
- `applied_settings`: `{"house_system": "<display name>", "source": "per-call" | "session-global"}` on chart responses — lets the consuming LLM verify which settings produced the chart instead of assuming.

### `generate_natal_chart`
Generates a complete birth chart with full astrological data.

**Parameters:**
- `date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `latitude`: Birth location latitude (e.g., "32n43" or "32.71")
- `longitude`: Birth location longitude (e.g., "117w09" or "-117.15")

### `generate_compact_natal_chart`
Generates a streamlined natal chart optimized for LLM processing and reduced token usage.

**Parameters:**
- `date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `latitude`: Birth location latitude (e.g., "32n43" or "32.71")
- `longitude`: Birth location longitude (e.g., "117w09" or "-117.15")

**Output Differences from Full Chart:**
- Only major celestial objects (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Ascendant, Midheaven)
- Only major aspects (Conjunction, Opposition, Square, Trine, Sextile)
- Simplified object data (name, sign, degree, house, retrograde status)
- Excludes weightings, chart shape, moon phase details, and minor asteroids

### `get_chart_summary`
Gets essential chart information in a simplified format.

**Parameters:**
- `date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `latitude`: Birth location latitude (e.g., "32n43" or "32.71")
- `longitude`: Birth location longitude (e.g., "117w09" or "-117.15")

### `get_planetary_positions`
Gets planetary positions in a simplified format.

**Parameters:**
- `date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `latitude`: Birth location latitude (e.g., "32n43" or "32.71")
- `longitude`: Birth location longitude (e.g., "117w09" or "-117.15")

### `generate_solar_return_chart`
Calculates a solar return chart for a specific year.

**Parameters:**
- `date_time`: Birth date and time
- `latitude`: Birth location latitude
- `longitude`: Birth location longitude
- `return_year`: Year for the solar return
- `include_natal_aspects`: Include return-planet-to-natal aspects under `natal_cross_aspects` (default: true). Each entry carries explicit `return_object`/`natal_object` keys.
- `return_latitude` / `return_longitude`: Optional coordinates to relocate the return chart to where the person is at the return moment (the astrological convention). The return *moment* is unchanged; only houses/angles move. The response echoes `return_location: {latitude, longitude, relocated}`.

### `generate_compact_solar_return_chart`
Generates a streamlined solar return chart optimized for LLM processing.

**Parameters:**
- `date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `latitude`: Birth location latitude (e.g., "32n43" or "32.71")
- `longitude`: Birth location longitude (e.g., "117w09" or "-117.15")
- `return_year`: Year for the solar return
- `include_natal_aspects`: As on the full tool (default: true)
- `aspect_priority`: Priority tier for the natal cross-aspects — "tight" (default, 0–2° actual orb), "moderate" (>2–5°), "loose" (>5°), or "all". A `natal_cross_aspect_summary` reports the per-tier counts.
- `return_latitude` / `return_longitude`: As on the full tool

**Output:** Same filtering as compact natal charts - major objects and aspects only

### `generate_lunar_return_chart`
Calculates the monthly lunar return chart (the moment the Moon returns to its natal position, found by ephemeris search to sub-minute precision).

**Parameters:**
- `date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `latitude`: Birth location latitude (e.g., "32n43" or "32.71")
- `longitude`: Birth location longitude (e.g., "117w09" or "-117.15")
- `return_year`: Year for the lunar return (e.g., 2025)
- `return_month`: Month for the lunar return (1–12)
- `include_natal_aspects`: Include return-to-natal aspects under `natal_cross_aspects` (default: true)
- `return_latitude` / `return_longitude`: Optional relocation coordinates; the return instant is preserved and reported in the return location's zone

### `generate_compact_lunar_return_chart`
Streamlined lunar return chart optimized for LLM processing. Same parameters as the full tool, plus `aspect_priority` for the natal cross-aspects (see compact solar return).

### `generate_progressed_chart`
Creates a secondary progression chart.

**Parameters:**
- `date_time`: Birth date and time
- `latitude`: Birth location latitude
- `longitude`: Birth location longitude
- `progression_date_time`: Date to progress the chart to
- `include_natal_aspects`: Include progressed-to-natal aspects — the core technique of secondary progressions — under `natal_cross_aspects` (default: true). Each entry carries explicit `progressed_object`/`natal_object` keys.

### `generate_compact_progressed_chart`
Generates a streamlined progressed chart optimized for LLM processing.

**Parameters:**
- `date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `latitude`: Birth location latitude (e.g., "32n43" or "32.71")
- `longitude`: Birth location longitude (e.g., "117w09" or "-117.15")
- `progression_date_time`: Date to progress the chart to (ISO format)
- `include_natal_aspects`: As on the full tool (default: true)
- `aspect_priority`: Priority tier for the natal cross-aspects — "tight" (default), "moderate", "loose", or "all"

**Output:** Same filtering as compact natal charts - major objects and aspects only

### `generate_composite_chart`
Generates a composite chart for two people.

**Parameters:**
- `native_date_time`: First person's birth date/time
- `native_latitude`: First person's birth latitude
- `native_longitude`: First person's birth longitude
- `partner_date_time`: Second person's birth date/time
- `partner_latitude`: Second person's birth latitude
- `partner_longitude`: Second person's birth longitude

### `generate_compact_composite_chart`
Generates a streamlined composite chart optimized for LLM processing.

**Parameters:**
- `native_date_time`: First person's birth date/time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `native_latitude`: First person's birth latitude (e.g., "32n43" or "32.71")
- `native_longitude`: First person's birth longitude (e.g., "117w09" or "-117.15")
- `partner_date_time`: Second person's birth date/time (ISO format)
- `partner_latitude`: Second person's birth latitude
- `partner_longitude`: Second person's birth longitude

**Output:** Same filtering as compact natal charts - major objects and aspects only

### `generate_synastry_aspects`
Calculates aspects between two charts.

**Parameters:**
- `native_*`: First person's birth data (will receive the aspects)
- `partner_*`: Second person's birth data (planets being aspected)

**Breaking change (v0.6.0):** the payload is now wrapped under an `aspects` key (previously the raw aspects dict was the top level) to make room for the response envelope.

### `generate_compact_synastry_aspects`
Calculates filtered synastry aspects optimized for LLM processing.

**Parameters:**
- `native_date_time`: First person's birth date/time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `native_latitude`: First person's birth latitude (e.g., "32n43" or "32.71")
- `native_longitude`: First person's birth longitude (e.g., "117w09" or "-117.15")
- `partner_date_time`: Second person's birth date/time (ISO format)
- `partner_latitude`: Second person's birth latitude
- `partner_longitude`: Second person's birth longitude

**Output:** Only major aspects between major objects (filtered synastry)

### `generate_transit_chart`
Shows current planetary positions.

**Parameters:**
- `latitude`: Location latitude
- `longitude`: Location longitude

### `generate_compact_transit_chart`
Shows current planetary positions with filtering for major objects only.

**Parameters:**
- `latitude`: Location latitude (e.g., "32n43" or "32.71")
- `longitude`: Location longitude (e.g., "117w09" or "-117.15")

**Output:** Only major planetary positions (Sun through Pluto, Ascendant, Midheaven)

### `generate_transit_to_natal`
Calculates transiting planet aspects to a natal chart with intelligent pagination and optimized response structure.

**✨ Optimized**: 87% size reduction (74 KB → 10 KB) through streamlined data structure.

**Parameters:**
- `natal_date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `natal_latitude`: Birth location latitude (e.g., "51n23" or "51.38")
- `natal_longitude`: Birth location longitude (e.g., "0w05" or "-0.08")
- `transit_date_time`: Date/time for transits (ISO format)
- `transit_latitude`: Optional transit location latitude (defaults to natal location)
- `transit_longitude`: Optional transit location longitude (defaults to natal location)
- `timezone`: Optional IANA timezone name (e.g., "Europe/London", "America/New_York")
- `aspect_priority`: Priority tier to return - "tight" (default), "moderate", "loose", or "all"
- `include_all_aspects`: Deprecated - treated as `aspect_priority="all"` (kept for compatibility)

**Pagination System:**
- **Tight** (0-2° orb, default): Most critical transits only (~4 KB)
- **Moderate** (2-5° orb): Secondary priority, building/waning influence
- **Loose** (5-8° orb): Background influences, subtle themes
- **All**: Every aspect (auto-adjusts to "tight" when lifecycle events are enabled, to stay under MCP size limits)

**Optimized Response Structure:**
- `natal_summary`: Simplified Sun/Moon/Rising (no redundant date_time)
- `transit_positions`: Named keys (`"Sun"` not `4000001`), consolidated position strings
- `dignities`: Consolidated section (not scattered in each position)
- `transit_to_natal_aspects`: Streamlined aspects with `planets` field (`"Venus → Chiron"`)
- `aspect_summary`: Counts for tight/moderate/loose/total aspects
- `pagination`: Current page, total pages, next page instructions

**Example:**
```
"Calculate transit-to-natal aspects for natal chart 1984-01-11 18:45:00 at 51n23, 0w05,
with transits for 2025-12-20 12:00:00 at 51n34, 0w09 in Europe/London timezone"
```

### `generate_compact_transit_to_natal`
Calculates compact transit-to-natal aspects with optional interpretations.

**Parameters:**
- `natal_date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `natal_latitude`: Birth location latitude (e.g., "51n23" or "51.38")
- `natal_longitude`: Birth location longitude (e.g., "0w05" or "-0.08")
- `transit_date_time`: Date/time for transits (ISO format)
- `transit_latitude`: Optional transit location latitude (defaults to natal location)
- `transit_longitude`: Optional transit location longitude (defaults to natal location)
- `timezone`: Optional IANA timezone name
- `include_interpretations`: Include aspect interpretation keywords (default: True)

**Output:** Streamlined aspects between major objects only with context-aware interpretations

### `configure_immanuel_settings`
Modifies global Immanuel library settings. **This changes global state for every subsequent chart in the session** (the response carries `scope: "session-global"`); for a one-off setting, prefer the per-call parameters (e.g. `house_system`) on the chart tools.

**Parameters:**
- `setting_key`: Name of the setting (e.g., "house_system", "objects")
- `setting_value`: Value to set (e.g., "WHOLE_SIGN", "4000001,4000002,Chiron")

#### Common Settings:
- **House Systems**: `PLACIDUS`, `KOCH`, `WHOLE_SIGN`, `EQUAL`, `CAMPANUS`, etc. (invalid names return an error listing all valid values)
- **Objects**: Comma-separated list of celestial bodies (e.g., "Sun,Moon,Mercury,Venus,Mars,Jupiter,Saturn,Uranus,Neptune,Pluto,Chiron")
- **Orbs**: `conjunction_orb`, `opposition_orb`, `trine_orb`, etc. (numeric values)
- **MC progression method**: `NAIBOD`, `SOLAR_ARC`, `DAILY_HOUSES`
- **Orb calculation**: `MEAN`, `MAX` (key: `orb_calculation`)

Note (v0.6.0): the `lunar_phase_method` and `solar_arc_method` keys were removed — they do not exist in the immanuel library and configuring them was a silent no-op.

### `reset_immanuel_settings`
Resets the global Immanuel settings to library defaults, undoing every `configure_immanuel_settings` change made in the session.

**Parameters:** None

**Returns:** Confirmation with a summary of the restored defaults

### `list_available_settings`
Lists all available Immanuel settings and their current values.

**Parameters:** None

**Returns:** Dictionary of current settings with descriptions

## Scope and Division of Labour

This server is **tropical-zodiac only** (the underlying immanuel settings expose no zodiac/ayanamsha option) and produces **structured chart data, not chart images**. For sidereal zodiacs, rendered chart wheels/SVG, synastry scoring, or electional/event charts, use the companion kerykeion MCP server instead — reaching for this server for those jobs will not work.

## Roadmap

- **Per-call extra chart objects on `generate_natal_chart`** (asteroids, points, fixed stars): deferred. Probed 2026-07-06 — asteroid/point constants (e.g. `CERES`) work via per-call settings, but named fixed stars (e.g. `'Antares'`) raise `ValueError: Invalid object index` because immanuel's bundled ephemeris ships no `sefstars.txt` star catalogue. Revisit if a star catalogue is bundled or an ephemeris-path option is exposed.

## Troubleshooting

### Installation Issues

#### Server won't start
- **Check Python version**: `python --version` (requires 3.10+)
- **Verify uv installation**: `uv --version`
- **Install dependencies**: Run `uv sync` in the project directory
- **Verify dependencies**: Check `uv pip list` shows `immanuel` and `mcp[cli]`
- **Test manually**: Run `uv run immanuel_server.py` from the project directory

#### "Failed to spawn" errors
- **Use full path to uv**: `C:\Users\[USERNAME]\.local\bin\uv.exe` (Windows)
- **Check executable exists**: Verify the uv executable path is correct
- **Use `--directory` flag**: Don't rely on `cwd` parameter alone

#### "ModuleNotFoundError: No module named 'immanuel'"
- **Install dependencies**: Run `uv sync` in the project directory
- **Check virtual environment**: Ensure uv is using the project's `.venv`
- **Verify installation**: Run `uv pip list` to see installed packages

### Claude Desktop Configuration Issues

#### Server not recognized
- **Restart Claude Desktop**: Always restart after configuration changes
- **Check file path**: Verify the configuration file path is correct
- **Validate JSON syntax**: Use a JSON validator to check for syntax errors
- **Check paths**: Ensure all paths in the configuration exist

#### Configuration file locations
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS/Linux**: `~/.config/Claude/claude_desktop_config.json`

### Runtime Errors

#### Coordinate parsing errors
- **Supported formats**: `32n43` or `32.71` for latitude
- **Southern latitudes**: `33s45` or `-33.75`
- **Western longitudes**: `117w09` or `-117.15`
- **Eastern longitudes**: `2e20` or `2.33`

#### Chart generation errors
- **Date format**: Use "YYYY-MM-DD HH:MM:SS" (24-hour time)
- **Coordinate ranges**: Latitude (-90 to 90), Longitude (-180 to 180)
- **Year values**: Use reasonable ranges (e.g., 1900-2100)

### Testing Commands

#### Manual testing (from project directory)
```bash
# Basic server test
uv run immanuel_server.py

# Test with full directory specification
uv --directory /path/to/astro-mcp run immanuel_server.py

# Check dependencies
uv pip list

# Run the test suite
uv run pytest tests/
```

#### Verify Claude Desktop can find the server
1. **Check configuration**: Ensure JSON is valid
2. **Restart Claude Desktop**: Required after any config changes
3. **Check Claude Desktop logs**: Look for error messages in the application
4. **Test the exact command**: Run the command from the configuration manually

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This MCP server is released under the MIT License. The Immanuel library itself has its own licensing terms.

## Acknowledgments

This server is built on top of the excellent [Immanuel Python library](https://github.com/theriftlab/immanuel-python) by The Rift Lab.
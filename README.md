# Immanuel MCP Server

A Model Context Protocol (MCP) server that exposes the powerful [Immanuel Python astrology library](https://github.com/theriftlab/immanuel-python) as a set of tools accessible to MCP-compatible clients like Claude Desktop.

## Features

### Chart Generation Tools
- **Natal Charts**: Generate complete birth charts with houses, planets, and aspects
- **Compact Natal Charts**: **NEW** - Streamlined charts optimized for faster processing and reduced LLM token usage
- **Chart Summaries**: Essential information (Sun/Moon/Rising signs, chart shape, moon phase)
- **Planetary Positions**: Simplified planetary positions in signs and houses
- **Solar Returns**: Calculate solar return charts for any year
- **Compact Solar Returns**: **NEW** - Streamlined solar return charts
- **Progressions**: Create secondary progression charts
- **Compact Progressions**: **NEW** - Streamlined progressed charts
- **Composite Charts**: Generate relationship composite charts
- **Compact Composite Charts**: **NEW** - Streamlined composite charts
- **Synastry Aspects**: Calculate inter-chart aspects between two people
- **Compact Synastry Aspects**: **NEW** - Filtered synastry aspects (major objects and aspects only)
- **Transit Charts**: Show current planetary positions for any location
- **Compact Transit Charts**: **NEW** - Streamlined transit charts

### Chart Output Options
- **Full Charts**: Complete astrological data with all objects, aspects, and detailed properties
- **Compact Charts**: Filtered data focusing on major planets and aspects for LLM optimization

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
   git clone https://github.com/yourusername/immanuel-mcp-server.git
   cd immanuel-mcp-server
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
   git clone https://github.com/yourusername/immanuel-mcp-server.git
   cd immanuel-mcp-server
   ```

#### Windows Subsystem for Linux (WSL)

Follow the Linux instructions above within your WSL environment.

### Server Setup

1. **Navigate to the project directory**:
   ```bash
   cd immanuel-mcp-server
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Test the server**:
   ```bash
   uv run immanuel_server.py
   ```
   
   You should see the server start without errors. Press `Ctrl+C` to stop it.

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

### `generate_compact_solar_return_chart`
Generates a streamlined solar return chart optimized for LLM processing.

**Parameters:**
- `date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `latitude`: Birth location latitude (e.g., "32n43" or "32.71")
- `longitude`: Birth location longitude (e.g., "117w09" or "-117.15")
- `return_year`: Year for the solar return

**Output:** Same filtering as compact natal charts - major objects and aspects only

### `generate_progressed_chart`
Creates a secondary progression chart.

**Parameters:**
- `date_time`: Birth date and time
- `latitude`: Birth location latitude
- `longitude`: Birth location longitude
- `progression_date_time`: Date to progress the chart to

### `generate_compact_progressed_chart`
Generates a streamlined progressed chart optimized for LLM processing.

**Parameters:**
- `date_time`: Birth date and time (ISO format: "YYYY-MM-DD HH:MM:SS")
- `latitude`: Birth location latitude (e.g., "32n43" or "32.71")
- `longitude`: Birth location longitude (e.g., "117w09" or "-117.15")
- `progression_date_time`: Date to progress the chart to (ISO format)

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

### `configure_immanuel_settings`
Modifies global Immanuel library settings.

**Parameters:**
- `setting_key`: Name of the setting (e.g., "house_system", "objects")
- `setting_value`: Value to set (e.g., "WHOLE_SIGN", "4000001,4000002,Chiron")

#### Common Settings:
- **House Systems**: `PLACIDUS`, `KOCH`, `WHOLE_SIGN`, `EQUAL`, `CAMPANUS`, etc.
- **Objects**: Comma-separated list of celestial bodies (e.g., "Sun,Moon,Mercury,Venus,Mars,Jupiter,Saturn,Uranus,Neptune,Pluto,Chiron")
- **Orbs**: `conjunction_orb`, `opposition_orb`, `trine_orb`, etc. (numeric values)

### `list_available_settings`
Lists all available Immanuel settings and their current values.

**Parameters:** None

**Returns:** Dictionary of current settings with descriptions

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
```

#### Verify Claude Desktop can find the server
1. **Check configuration**: Ensure JSON is valid
2. **Restart Claude Desktop**: Required after any config changes
3. **Check Claude Desktop logs**: Look for error messages in the application
4. **Test the exact command**: Run the command from the configuration manually

### Common Issues and Solutions

| Problem | Solution |
|---------|----------|
| "Failed to spawn: immanuel_server.py" | Use full path to uv executable |
| "ModuleNotFoundError: No module named 'immanuel'" | Run `uv sync` to install dependencies |
| "File not found" errors | Use `--directory` flag instead of `cwd` |
| Server tools not available in Claude | Restart Claude Desktop after config changes |
| JSON syntax errors | Validate configuration file with JSON validator |

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This MCP server is released under the MIT License. The Immanuel library itself has its own licensing terms.

## Acknowledgments

This server is built on top of the excellent [Immanuel Python library](https://github.com/theriftlab/immanuel-python) by The Rift Lab.
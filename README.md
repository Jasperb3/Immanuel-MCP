# Immanuel MCP Server

A Model Context Protocol (MCP) server that exposes the powerful [Immanuel Python astrology library](https://github.com/theriftlab/immanuel-python) as a set of tools accessible to MCP-compatible clients like Claude Desktop.

## Features

### Chart Generation Tools
- **Natal Charts**: Generate complete birth charts with houses, planets, and aspects
- **Solar Returns**: Calculate solar return charts for any year
- **Progressions**: Create secondary progression charts
- **Composite Charts**: Generate relationship composite charts
- **Synastry Aspects**: Calculate inter-chart aspects between two people
- **Transit Charts**: Show current planetary positions for any location

### Configuration
- Dynamically configure all Immanuel library settings (house systems, orbs, calculation methods, etc.)

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

### Windows

1. Open the Claude Desktop configuration file:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. Add the following configuration:
   ```json
   {
     "mcpServers": {
       "immanuel-astrology": {
         "command": "C:\\path\\to\\.local\\bin\\uv.exe",
         "args": ["--directory", "C:\\path\\to\\immanuel-mcp-server", "run", "python", "immanuel_server.py"]
       }
     }
   }
   ```

### macOS and Linux (untested)

1. Open the Claude Desktop configuration file:
   ```
   ~/.config/Claude/claude_desktop_config.json
   ```

2. Add the following configuration (update the paths as needed):
   ```json
   {
     "mcpServers": {
       "immanuel-astrology": {
         "command": "/home/youruser/.local/bin/uv",
         "args": ["--directory", "/home/youruser/immanuel-mcp-server", "run", "python3", "immanuel_server.py"]
       }
     }
   }
   ```
   - On macOS, the command path may be `/Users/youruser/.local/bin/uv`
   - Use `python3` instead of `python` if needed

3. Save the file and restart Claude Desktop.

## Usage Examples

Once configured, you can use the Immanuel tools in Claude Desktop by asking Claude to generate astrological charts. Here are some examples:

### Generate a Natal Chart

```
"Generate a natal chart for someone born on January 1, 1990 at 3:30 PM in 
San Diego, California (coordinates: 32n43, 117w09)"
```

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
Generates a complete birth chart.

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

### `generate_progressed_chart`
Creates a secondary progression chart.

**Parameters:**
- `date_time`: Birth date and time
- `latitude`: Birth location latitude
- `longitude`: Birth location longitude
- `progression_date_time`: Date to progress the chart to

### `generate_composite_chart`
Generates a composite chart for two people.

**Parameters:**
- `native_date_time`: First person's birth date/time
- `native_latitude`: First person's birth latitude
- `native_longitude`: First person's birth longitude
- `partner_date_time`: Second person's birth date/time
- `partner_latitude`: Second person's birth latitude
- `partner_longitude`: Second person's birth longitude

### `generate_synastry_aspects`
Calculates aspects between two charts.

**Parameters:**
- `native_*`: First person's birth data (will receive the aspects)
- `partner_*`: Second person's birth data (planets being aspected)

### `generate_transit_chart`
Shows current planetary positions.

**Parameters:**
- `latitude`: Location latitude
- `longitude`: Location longitude

### `configure_immanuel_settings`
Modifies global Immanuel library settings.

**Parameters:**
- `setting_key`: Name of the setting (e.g., "house_system", "objects")
- `setting_value`: Value to set (e.g., "WHOLE_SIGN", "4000001,4000002,Chiron")

#### Common Settings:
- **House Systems**: `PLACIDUS`, `KOCH`, `WHOLE_SIGN`, `EQUAL`, `CAMPANUS`, etc.
- **Objects**: Comma-separated list of celestial bodies (e.g., "Sun,Moon,Mercury,Venus,Mars,Jupiter,Saturn,Uranus,Neptune,Pluto,Chiron")
- **Orbs**: `conjunction_orb`, `opposition_orb`, `trine_orb`, etc. (numeric values)

## Troubleshooting

### Server won't start
- Ensure Python 3.10+ is installed: `python --version`
- Verify uv is installed: `uv --version`
- Check you're in the correct directory with `pyproject.toml`
- Run `uv sync` to ensure dependencies are installed

### Claude Desktop doesn't see the tools
- Restart Claude Desktop after modifying the configuration
- Check the configuration file path is correct
- Ensure the `cwd` path in the config points to your server directory
- Check for JSON syntax errors in the configuration file

### Coordinate parsing errors
- Use supported formats: `32n43` or `32.71` for latitude
- Southern latitudes: `33s45` or `-33.75`
- Western longitudes: `117w09` or `-117.15`
- Eastern longitudes: `2e20` or `2.33`

### Chart generation errors
- Verify date format: "YYYY-MM-DD HH:MM:SS" (24-hour time)
- Check coordinate values are within valid ranges
- Ensure year values are reasonable (e.g., 1900-2100)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This MCP server is released under the MIT License. The Immanuel library itself has its own licensing terms.

## Acknowledgments

This server is built on top of the excellent [Immanuel Python library](https://github.com/theriftlab/immanuel-python) by The Rift Lab.
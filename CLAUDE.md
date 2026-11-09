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
- **Architecture**: FastMCP-based server with 23 astrology tools (8 chart types in full/compact pairs, 2 summary tools, 2 forecast-calendar tools, 3 configuration tools). A single shared FastMCP instance lives in `immanuel_mcp/app.py`; both entry points register the identical tool set against it.
- **Per-call settings (v0.6.0)**: every chart tool accepts `house_system` for that call only (a fresh `charts.Config` built by `build_call_config`, session Config untouched; helper in `immanuel_mcp/utils/settings.py`), and chart responses echo `applied_settings` (`{house_system, source: "per-call" | "session-global"}`) plus `status: "success" | "error"`. Progressed/solar-return/lunar-return tools expose `include_natal_aspects` (cross aspects under `natal_cross_aspects` with `progressed_object`/`return_object`/`natal_object` keys; helper in `immanuel_mcp/optimizers/cross_aspects.py`), and the return tools accept `return_latitude`/`return_longitude` for relocation (return instant preserved). Requires `immanuel>=1.7.0,<1.8` (v0.11.0).
- **Session Config (v0.9.0)**: immanuel 1.6 has no settings singleton. `utils/settings.py` owns one mutable `charts.Config` for the session; charts take it via `config=` and freeze a snapshot at construction, so sharing it is safe. **Reach it only through `get_session_config()`**: `reset_global_settings()` rebinds `_session_config` to a copy of the startup Config, so a module holding its own reference would keep the stale object and silently ignore every reset (a test greps for this). `applied_settings` reads the session Config, not the Config a chart was built with, so it cannot detect that bug on its own.
- **Serialized chart keys**: index ToJSON output with `KEY_OBJECTS`/`KEY_HOUSES`/`KEY_ASPECTS` from `immanuel_mcp/constants.py`, never `immanuel.const.data.OBJECTS` etc. Those became ints in 1.6 while the serialized keys stayed strings, so the lookups miss silently and compact charts come back empty.
- **Package Structure**:
  ```
  immanuel_mcp/
  ├── __init__.py                    # Package initialization (no eager server import)
  ├── __main__.py                    # Enables `python -m immanuel_mcp`
  ├── app.py                         # The single shared FastMCP instance
  ├── server.py                      # Modular entry point (loads all tools onto app.mcp)
  ├── constants.py                   # CELESTIAL_BODIES mapping
  ├── utils/                         # Utility functions
  │   ├── coordinates.py             # parse_coordinate
  │   ├── datetimes.py               # parse_datetime_value
  │   ├── subjects.py                # create_subject helper
  │   ├── search.py                  # ephemeris search wrappers (v0.7.0)
  │   └── errors.py                  # validate_inputs, handle_chart_error
  ├── optimizers/                    # Response optimization
  │   ├── positions.py               # format_position, optimized transit positions
  │   ├── aspects.py                 # build_optimized_aspects
  │   └── dignities.py               # extract_primary_dignity, build_dignities_section
  ├── pagination/                    # Aspect pagination
  │   └── helpers.py                 # get_actual_orb, classify_aspect_priority, build_pagination_object
  ├── serializers.py                 # CompactJSONSerializer (runtime dependency)
  ├── charts/                        # Chart generation
  │   ├── lunar_return.py            # Lunar return charts (ephemeris-based search)
  │   ├── lunations.py               # Lunation & eclipse calendar (v0.7.0)
  │   └── ingresses.py               # Sign ingress calendar (v0.7.0)
  ├── lifecycle/                     # Lifecycle events detection (v0.4.0)
  │   ├── __init__.py                # Package exports
  │   ├── attach.py                  # attach_lifecycle_section (shared by all endpoints)
  │   ├── constants.py               # Orbital periods, significance levels, keywords
  │   ├── returns.py                 # Planetary return calculations, movement helpers
  │   ├── transits.py                # Major life transit detection
  │   ├── timeline.py                # Future predictions and lifecycle stages
  │   ├── progressed.py              # Progressed Moon return detection
  │   └── lifecycle.py               # Master orchestration function
  └── interpretations/               # Aspect interpretations
      └── aspects.py                 # ASPECT_INTERPRETATIONS, context-aware interpretations
  ```

  The tool functions themselves are defined in `immanuel_server.py` (imported
  by `immanuel_mcp/server.py`); all shared helpers live in the package and
  `immanuel_server.py` imports them - there are no duplicated copies.
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
- **Custom**: `immanuel_mcp/serializers.py` (streamlined chart output for LLM optimization). This is a runtime dependency of the package, not a script — it briefly lived in the gitignored `scripts/` directory, which made a clean checkout unimportable.
- **Python**: Requires Python 3.10+
- **Version pin**: `immanuel>=1.7.0,<1.8` (pulls in `pysweph`; v0.11.0, 1.6 before). `pysweph` and `pyswisseph` install the same `swisseph` module, so this server must never share a venv with kerykeion <6 (or `kerykeion[swiss]`); the kerykeion MCP server lives in its own directory and venv. See `docs/IMMANUEL_UPGRADE_NOTES.md`.
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

### Forecast Calendar Tools (🆕 v0.7.0)
These need no birth data — they read the ephemeris directly and build no chart.
- `get_lunations_and_eclipses` - Upcoming new moons, full moons and solar/lunar eclipses, with the Moon's sign and degree and both UTC and local times. Eclipses carry their type.
- `get_sign_ingresses` - Dates planets change zodiac sign, retrograde re-entries included (a boundary is often crossed three times).

**Do not replace either tool's search with `immanuel.tools.transit.next_sign_ingress()` / `next_aspect_to()` for slow bodies.** Those bracket by stepping `1/|speed|` days, so near a station the step grows without bound and skips the crossing — `next_sign_ingress(VENUS, ARIES, ...)` asked on 2025-03-28 answers 2026-03-06, missing the real 2025-04-30 re-entry. `immanuel_mcp/utils/search.py::find_state_changes` is the one scanner both use: it brackets by degrees travelled under a day cap, then bisects. Callers pass a state function (which sign, or which side of a longitude), so a tweak to the step budget applies to both. `find_return_jd` (lunar return) uses it too since v0.10.3: `next_aspect_to` also failed for the *Moon*, whose `_fixed_aspect_search` steps a day on the unsigned distance and overshoots when the Moon accelerates during that day (6 of 528 month searches skipped a return). `find_return_jd` is one continuous `_crossings` scan from just before `from_jd`, its window doubling, then a linear interpolation across the last bisection bracket. The Moon scans at a fixed 0.25-day step (`_FIXED_STEP_DAYS`), since it never stations. Nothing calls `next_aspect_to` / `previous_aspect_to` any more; keep it that way. immanuel 1.7 rewrote those searches (a signed `_crossing` scan; both repros above now come out right), but they return one crossing, not a pass cluster, and have no grazing-station check, so ours stay. Samples come from `body_position`, which reads 1.7's `sweph.longitude()` (lon and speed only, about a third of `ephemeris.get()`'s cost). The skip bound stays our `_MAX_SPEED`, not 1.7's `calc.MAX_MOTIONS`: different numbers would move every sample, and `tests/test_search_skip.py` pins ours. **Stations (v0.10.4):** a body that stations just past a target crosses it twice, sometimes inside one scan step, where the side is the same at both ends. `find_state_changes` therefore also watches the sign of the speed: a sign change between two same-state samples is a station, bisected by `_station_crossings`, and the state at the station decides whether a pair hides there (1984 San Diego's Neptune Square lost its 2025-12-06/12-14 pair, a 17.7″ overshoot). Bisecting every station a skip jumps over cost ~200 bisections per lifecycle chart, so callers pass `may_hide_pair` from `station_pair_filter(index, distance)`: crossing a boundary and back means travelling at least both samples' distances to it, which the padded maximum speed bounds. `distance` is to the target (`_crossings`) or to the nearer sign edge (ingresses). Pass the filter from any new caller.

**Timezone echo (v0.8.1):** both transit-to-natal tools report the timezone the chart was actually built in, not the raw parameter. `Subject.timezone` holds only what the caller passed and stays `None` for an inferred zone, so use `effective_timezone()` in `immanuel_mcp/utils/subjects.py` (it reads the resolved `date_time.tzinfo`) rather than the attribute when echoing a timezone in any new tool.

### Transit-to-Natal Pagination System

The `generate_transit_to_natal` endpoint includes intelligent pagination to comply with MCP transport limits (~50 KB) while organizing aspects by astrological significance.

**Pagination Parameters:**
- `aspect_priority: str = "tight"` - Priority tier to return
  - `"tight"`: 0-2° orb aspects (most critical, peak influence)
  - `"moderate"`: >2-5° orb aspects (secondary priority, building/waning influence)
  - `"loose"`: >5° orb aspects (background influences, subtle themes)
  - `"all"`: Return all aspects (warning: may exceed MCP size limits)
- `include_all_aspects: bool = False` - Deprecated; treated as `aspect_priority="all"` (and subject to the same lifecycle size guard)

Orbs here are the **actual deviation from exactness** (Immanuel's `difference`
field), not the configured maximum orb for the aspect type. Tier boundaries
are inclusive at their upper edge (an aspect at exactly 2.0° is "tight").

**Response Structure Enhancements:**
- `aspect_summary`: Counts for tight/moderate/loose/total aspects
- `pagination`: Current page, total pages, has_more_aspects, next_page, navigation instructions
- Each aspect carries `transiting_object`/`natal_object` and a direction-aware
  `planets` label ("transit Saturn → natal Sun"). Compact synastry aspects
  carry `native_object`/`partner_object`. Immanuel's `active`/`passive` are
  speed-ordered and do NOT indicate which chart an object belongs to.

**Default Behavior:**
Without specifying `aspect_priority`, the endpoint returns only tight aspects (0-2° orb), ensuring the response stays well under MCP limits while providing the most astrologically significant transits.

### Lifecycle Events Detection System (✅ v0.4.0 - Production Ready)

All chart types (Natal, Transit-to-Natal, Solar Return, Lunar Return, Progressed) include comprehensive lifecycle events detection, automatically identifying planetary returns and major life transits to provide context about where someone is in their astrological life journey.

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
      "orb_status": "tight",
      "movement": "applying",
      "exact_date": "2025-01-15",
      "exact_date_estimated": true,
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
      "themes": ["responsibility", "maturity", "commitment"],
      "stage_basis": "ephemeris"
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
- `orb_status`: Closeness relative to the event's orb tolerance: "exact" (< 0.5°), "tight", "moderate", "loose", or "inactive" (beyond tolerance; only on future-timeline entries)
- `movement`: "applying" (moving toward exact), "exact", "separating" (past exact), or "stationary" - derived from the transiting planet's actual speed
- `exact_date` / `exact_dates` / `exact_date_estimated`: **v0.7.0** — the perfection dates come from an ephemeris search (`find_event_exact_dates` in `lifecycle/returns.py`, built on `utils/search.py`), so `exact_date_estimated` is now `false`. `exact_date` is the perfection nearest the transit moment (for an active event that pass may be in the past); `exact_dates` lists every pass, since a retrograde outer planet perfects the same aspect up to three times, and a slow square up to five. **v0.10.3:** active events get the whole sequence from `utils/search.find_pass_cluster` (a fixed ±4-year scan, grouped by `group_passes`, the cluster containing or nearest the query). The old window, sized from the current speed and capped at three hits, returned part of a long sequence, and which part depended on the query date. Multi-pass events also get their true `date_range` (first pass to last) rather than an orb-derived estimate. The **progressed Moon** is the exception: it moves at a symbolic rate, not an ephemeris one, so it keeps the linear estimate and `exact_date_estimated: true`.
- `status`: "active" (happening now), "upcoming" (future), or "past" (historical)
- `category`: "return" (planetary return) or "major_transit" (square/opposition)
- Future-timeline entries carry `prediction_basis`. **v0.10.0:** it is `"ephemeris"`. Given the natal chart, `build_future_timeline` (`lifecycle/timeline.py`) finds each event's next pass sequence with the same station-safe search, so `exact_date` (the first pass on or after the query date), `exact_dates` (the whole sequence) and `date_range` are real and don't move with the query date. Passes are grouped by the gap between consecutive hits (more than a year starts a new sequence). The old `"mean_orbital_period"` / `"typical_age"` arithmetic is only the fallback without a natal chart, and is flagged `exact_date_estimated: true`. There is no `age_range` gate any more: textbook ages are wrong for some cohorts (a 1984 Uranus Opposition perfects at 44.5). An event already reported as active is not repeated as upcoming. **v0.10.4:** the horizon decides which sequence is listed (its next pass is within `years_ahead`), not where it is cut: `find_next_pass` scans `PASS_GAP_DAYS` beyond the horizon, then `_close_sequence` keeps scanning from just after the last pass until a whole gap is empty. Before, a 1987 Saturn Return starting 2046-01-20 inside the horizon lost its 06-18 and 10-20 passes.
- `lifecycle_summary.next_major_event` (v0.10.0): the earliest pass still ahead among HIGH/CRITICAL events, active or upcoming, with `next_major_event_date` / `years_until_event` from that pass. A sooner MODERATE event (Mars Return) is skipped, and so is an active event whose passes are all behind the query date.
- `age_at_event` (v0.10.1): the age on the event's date, from `age_on()` in `lifecycle/returns.py`, the one age formula. Active events use the first pass of their cluster (computed where the event is detected, in `returns.py`/`transits.py`), upcoming ones their `exact_date` (`predicted_age`), the progressed Moon its estimated perfection. `typical_age` appears only on the flagged arithmetic fallback. Don't read the raw `age` field for this: it is the current age.
- `lifecycle_summary.current_stage` (v0.10.1): built by `_lifecycle_stage()` in `lifecycle.py`, not the age table. `stage_basis` is `"ephemeris"` (a HIGH/CRITICAL event under way: active, or the reference inside its `date_range`), `"ephemeris_past"` (the latest one whose last pass is at most `STAGE_PAST_YEARS` = 3 behind, found with `timeline.find_last_pass`, named "After ...") or `"age_band"` (`get_lifecycle_stage(age)`). The three-year cut-off matters: without it a Jupiter or North Node Return would name the stage for 12 or 18 years. `age_range` is the event's `date_range`, so a single-pass return keeps its orb-window width. The past search runs only when nothing is under way and costs a few ms.
- The ephemeris crossing search (`utils/search._crossings`) skips ahead by distance ÷ (1.5 × the body's maximum speed) when a body is far from its target. Without it, ephemeris-dating the timeline made a lifecycle chart more than ten times slower (0.25 s against 0.02 s per transit-to-natal call in WSL). A test (`tests/test_search_skip.py`) holds it to exactly the stepped scanner's results. Throughout a skip the body stays more than `_SKIP_MARGIN_DEGREES` from the target and inside the margin the skip is zero, so a grazing station always falls in an ordinary step, where the station check sees it.

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
- **Precision**: Calculated to well under 1 minute of the exact Moon return moment (Moon within ~0.001° of the natal position)
- **Application**: Used for monthly forecasting, similar to how solar returns are used for annual forecasting

**Implementation Details:**
- Uses `utils/search.find_return_jd` (station-safe signed scan plus interpolation; Moon within 0.0001″ of natal). Before v0.10.3 it delegated to `immanuel.tools.transit.next_aspect_to()`, which skipped about 1 month in 100
- A return near a month boundary is placed from the Julian date (`crossed_by` at the boundary JD), never from the formatted timestamp. The return chart is built from the Julian date (`_subject_at`), because immanuel resolves a wall-clock or aware datetime in a fall-back night's repeated hour to the first reading (an hour early)
- A 30/31-day month occasionally contains two lunar returns (~27.3-day cycle). `_find_lunar_return_jds` finds them all; `occurrence` (default 1) selects one, `lunar_return_info.returns_in_month` lists them, and a missing occurrence is an error naming the returns that exist (v0.10.2)
- Generates a standard natal chart for the return moment
- Includes metadata: return_date, natal_moon_longitude, return_year, return_month, occurrence, returns_in_month. Solar returns carry `solar_return_info.return_date` in the same form (v0.10.2)
- Includes lifecycle events context calculated at the return moment

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
# Returns: return_date: "2025-01-18T05:27:08+00:00"
#          natal_moon_longitude: 172.94
#          Full chart data...
# (Earlier docs cited 04:57:04 - that value came from the old search's
#  0.1-degree tolerance and is superseded by the verified time above.)
```

**Response Size:**
- Full version: ~40 KB (complete chart data)
- Compact version: ~18 KB (major objects and aspects only)

### Configuration Tools
- `configure_immanuel_settings` - Modify the session Config (house system, objects, aspects, locale, `default_orb`/`exact_orb`/`chart_shape_orb`, progression and orb-calculation methods). `objects` and `aspects` are validated (names via `immanuel.const.chart` / `immanuel.const.calc`; a non-constant object name must resolve as a fixed star through the ephemeris), and a rejected value leaves the session unchanged. Session-global; for one-off changes prefer the per-call `house_system` parameter on the chart tools. **House systems accept either the numeric code (`108` or `"108"`), the constant name (`PLACIDUS`) or the display name (`"Placidus"`)** — every value `list_available_settings` shows is a valid input
- `reset_immanuel_settings` - Restore the session Config to the server's **startup configuration** (immanuel's library defaults unless the server was configured at launch). This is **not** an undo of the caller's own changes: the server keeps no per-change history, so a session that was already reconfigured before you inspected it gets *changed* by a reset, not reverted. The response reports `previous_settings`, `restored_settings` and a `changed` list so this is never silent; `restored_defaults` remains as an alias for one release
- `list_available_settings` - View current Immanuel library settings. `available_systems` entries are `{code, name, accepts}`

**Locales and interpretations (v0.10.0):** a `locale` translates chart data only. Aspect keywords/interpretations and lifecycle text are English prose by design. The interpretation lookup must key on locale-proof fields: object indices (`active`/`passive`) and the compact aspect's `angle`, via `english_aspect_terms()` in `interpretations/aspects.py`, never on the displayed `type`/`object1`/`object2`, which are translated.

**Same-planet aspects (v0.10.0):** in a chart built against another chart, `active == passive` means the same planet in both charts (transit Saturn conjunct natal Saturn), not a self-aspect. Never filter them: they are the returns and major life transits. `normalize_aspects_to_list` no longer has a `filter_self_aspects` option.

**Aspect patterns (v0.10.0):** always serialize full charts with `serialize_full_chart()` (`immanuel_mcp/serializers.py`), never `json.loads(json.dumps(chart, cls=ToJSON))`. It rebuilds `aspect_patterns` from the planets and Chiron only (`PATTERN_OBJECTS`), by re-running immanuel's own search on planet-only aspects. Filtering its output would be wrong, because vertices are clusters of conjunct objects with pooled aspects. For charts built with `aspects_to` it sets `aspect_patterns` to `None`: transit and natal objects share indices, and immanuel's search merges both charts into the same vertices.

**Polar charts (v0.10.2):** immanuel hard-codes Placidus for the Part of Fortune Ascendant and the diurnal check, and pysweph raises the Swiss Ephemeris "within polar circle, switched to Porphyry" warning as `swisseph.Error`, so every chart inside a polar circle failed. `immanuel_mcp/compat/polar.py` (installed from `immanuel_mcp/__init__.py`) replaces the `swe` seen by `immanuel.tools.sweph` only, not the swisseph module, with a proxy whose `houses_ex2`/`houses_armc_ex2` retry that one error with Porphyry and record the fallback. It is version-guarded (`SUPPORTED`, now 1.7: `angles_houses_vertex` is unchanged) and raises on anything else; `tests/test_polar_charts.py` fails if immanuel changes the wrapped calls. **v0.10.5:** the full charts' top-level `house_system` (immanuel's own field) goes through `reported_house_system(chart)` in `compat/polar.py`, applied in `serialize_full_chart` and `get_chart_summary`: "Porphyrius", translated, when the call recorded a fallback and the chart's own subject is polar (re-checked per chart, since a polar natal and a return relocated out of the circle share one call). `build_applied_settings` reports a fallback only when the *requested* system's own code fell back (a Whole Sign chart still triggers immanuel's internal Placidus fallback, which doesn't matter).

**Night-chart sect (v0.11.0):** immanuel 1.7.0's `Chart.wrap_objects` computes `in_sect` only when `is_daytime` is truthy, so every night chart lost it. `immanuel_mcp/compat/sect.py` (installed next to polar) is guarded on behaviour, not version: at install it casts one known night chart with the unpatched method and wraps `wrap_objects` only if `in_sect` is missing, recomputing it with `condition.is_object_in_sect` as 1.6 did. `tests/test_sect_compat.py` covers every chart class, since nothing tested sect before. Remove the shim once the pinned immanuel is fixed (upstream issue draft pending).

**Untimed charts (v0.11.0):** every tool taking a birth time has `time_status` (`native_/partner_time_status` on composite and synastry), parsed by `validate_time_status` (`utils/errors.py`) and passed to `create_subject(..., time_status, who=)`, which adds the warning. Thread it through any new birth-data tool, and pass the status to `build_applied_settings`, which then returns `house_system: None` plus `time_status` and skips the polar check (no houses are cast). immanuel drops houses, angles, Vertex, Parts, `diurnal`, `house_system`, sect and day/night triplicity rulers; `TIME_UNKNOWN` also replaces the time with local noon. That replacement is why a derived chart cast at a computed instant must never be `TIME_UNKNOWN`: `lunar_return._subject_at` uses `TIME_APPROXIMATE` for an untimed birth, or the return would be recast at noon. `warn_on_untimed_derived_chart` (`utils/subjects.py`) explains the return/progression uncertainty, and `moon_range` gives the Moon's 00:00–23:59 span (natal tools, unknown only). Transit-to-natal applies the status to the natal chart only (`natal_time_status` in `applied_settings`).

**Per-call warnings (v0.10.2):** chart and calendar tools are decorated `@reports_warnings` (`immanuel_mcp/utils/call_context.py`), which gives each call a fresh `CallState` in a ContextVar. Helpers deep in the call record into it (`add_warning`, `note_polar_fallback`), and the decorator attaches `warnings` only when there is one, so ordinary responses are byte-identical. Decorate any new chart tool the same way, under `@mcp.tool()`. `create_subject` warns on clock-change local times, reading the offset immanuel actually used from the resolved datetime.

**Input validation (v0.10.2):** `validate_aspect_priority` and `validate_progression_date` (`utils/errors.py`) reject bad input; nothing silently becomes `tight` any more. `handle_chart_error` names an unknown zone as unknown and suggests tzdata only when `zoneinfo.available_timezones()` is empty.

**Node crossings (v0.10.2):** the true node wobbles (~1.5°, half-month period), so a node return crosses the natal node several times, days apart. `utils/search._MAX_STEP_DAYS_BY_BODY` caps the nodes' scan step at 6 hours so every crossing is found; with the 10-day cap, two fell inside one step and the reported crossing depended on the query date.

**Do not treat a house-system display name as its constant name.** They diverge: `EQUAL` displays as "Equal House", `VEHLOW_EQUAL` as "Vehlow Equal House", `POLICH_PAGE` as "Polich Page". `resolve_house_system` in `immanuel_mcp/utils/settings.py` normalizes and accepts both, plus numeric codes; anything comparing the two forms directly will reject values the tools advertise.

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
- **Flattened Houses (v0.8.0)**: house cusps are reduced to `number`, `sign`, `sign_longitude` and raw `longitude`. They were previously copied verbatim from the full chart, which left every "compact" response carrying immanuel's full nested wrapper for all twelve cusps — flattening them cuts the houses block by ~84% (8.5 KB → 1.4 KB on a natal chart)
- **Excluded**: Minor asteroids, detailed weightings, chart shape analysis, moon phase details

### Modifying Settings Support
New Immanuel settings can be added to `configure_immanuel_settings()` by extending the conditional logic that handles different setting types (constants, lists, numeric values, etc.).
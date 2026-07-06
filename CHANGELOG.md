# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-07-06

Interpretive-capability release: exposes per-call settings and the
natal-aspect cross-referencing the immanuel library already supports, and
removes the remaining mutable-global-settings hazard.

### Added
- **Per-call `house_system` on every chart tool** (e.g. `"CAMPANUS"`,
  `"WHOLE_SIGN"`), applied to all charts built within the call via an
  isolated settings object — the session-global settings are untouched.
  Invalid names return a structured error listing all 23 valid values.
  Per-call overrides start from library defaults and deliberately ignore
  session-level `configure_immanuel_settings` changes.
- **`applied_settings` echo on chart responses**
  (`{"house_system": "<display name>", "source": "per-call" |
  "session-global"}`) so the consuming LLM can verify instead of assume.
- **Progressed-to-natal and return-to-natal aspects** (`aspects_to`):
  progressed, solar return and lunar return tools gain
  `include_natal_aspects` (default true) exposing cross aspects under
  `natal_cross_aspects` with explicit `progressed_object`/`return_object`
  and `natal_object` direction keys. Compact variants filter by
  `aspect_priority` (tight/moderate/loose/all, actual-orb classification)
  with interpretation hints and a `natal_cross_aspect_summary`.
- **Relocated solar and lunar returns** via
  `return_latitude`/`return_longitude`: casts the same return instant at
  the person's actual location (probe-verified: identical UTC return
  moment, different Ascendant). Responses echo `return_location`.
- **`reset_immanuel_settings` tool** (21 tools total): restores library
  defaults, undoing session mutations.
- **`status` field on all responses**: `"success"` on success paths,
  `"error"` on error responses (existing error keys kept).

### Changed
- **`generate_synastry_aspects` response shape (breaking)**: the payload
  is now wrapped under an `aspects` key (previously the raw aspects dict
  was the top level) to make room for the response envelope.
- `configure_immanuel_settings` validates `house_system`,
  `mc_progression_method` and `orb_calculation` against the library's real
  constants (errors list every valid value), flags its session-global
  scope in the response and docstring, and accepts the legacy
  `orb_calculation_method` key as an alias for the real `orb_calculation`.
- Requires `immanuel>=1.5.4` (first version with per-call chart settings).

### Removed
- `lunar_phase_method` and `solar_arc_method` from
  `configure_immanuel_settings`: these settings do not exist in the
  immanuel library and configuring them was a silent no-op.

## [0.5.0] - 2026-07-05

Comprehensive fix release from a full codebase audit (see
`docs/BUG_REFERENCE.md` for root-cause details of each bug).

### Fixed
- **Transit-to-natal pagination classified aspects by the configured maximum
  orb, not the actual orb.** Immanuel's full serialization stores the orb
  limit in `orb` and the actual deviation in `difference`; the tight page
  omitted nearly every genuinely exact transit (measured: 1 returned vs 16
  actually within 2°) and displayed `orb: 10.0` on partile aspects.
  Classification and display now use the actual deviation.
- **`python -m immanuel_mcp` served zero tools** (its FastMCP instance never
  had anything registered, and no `__main__.py` existed), and the documented
  `immanuel_server.py` entry point never registered the lunar return tools.
  A single shared FastMCP instance (`immanuel_mcp/app.py`) now backs both
  entry points; both serve the identical 20-tool set.
- **DMS coordinates with seconds parsed to wrong positions**: `117w09'30`
  parsed as -132.5 instead of -117.158 (minutes group swallowed the seconds
  digits) with no error raised. Minutes/seconds are now bounded and
  validated (< 60).
- **Datetime parser dropped single-digit-hour times**: `2024-01-01 1:00`
  silently became midnight (the timezone-token heuristic matched short time
  strings).
- **`timezone` parameter was silently ignored** in both transit-to-natal
  endpoints; it now applies to natal and transit datetimes.
- **Aspect direction was lost and cross-aspects were dropped**: labels were
  built from speed-ordered `active`/`passive` (a transit Saturn conjunct
  natal Sun rendered as "Sun → Saturn"), and the compact dedup collapsed
  distinct synastry double-whammy contacts (A's Saturn–B's Neptune AND A's
  Neptune–B's Saturn) into one. Aspects now carry
  `transiting_object`/`natal_object` (or `native_object`/`partner_object`),
  and dedup keys include the orb.
- **Lifecycle `orb_status` labelled separating events "applicative"** and
  `exact_date` echoed the request date. A new `movement` field derives
  applying/exact/separating/stationary from the transiting planet's speed,
  and `exact_date` is now a speed-based perfection estimate flagged with
  `exact_date_estimated: true`.
- **Lunar return search was ~11 minutes imprecise** (0.1° early-exit
  tolerance vs a documented 1-minute claim - enough to change the return
  chart's rising sign) and built ~130 full charts per call. The search now
  runs against the ephemeris directly: ~50x faster, Moon within ~0.001° at
  the returned moment.
- Natal endpoints' lifecycle reference chart interpreted a UTC timestamp as
  local time at the birth coordinates (up to ±12 h off); it now uses an
  explicit UTC-zoned Subject.
- `list_available_settings` hardcoded 13 house systems; it now reads all 23
  from `immanuel.const.names.HOUSE_SYSTEMS`.
- Five test files hardcoded a Windows working-copy path into `sys.path`,
  poisoning the suite with stale modules when run from another clone.

### Changed
- ~1,200 lines of inline helper copies in `immanuel_server.py` replaced by
  imports from the `immanuel_mcp` package (single source of truth; the
  package copies previously drifted, one to the point of a syntax error).
- The lifecycle import is unconditional: a broken lifecycle package fails
  the server at startup instead of silently nulling `lifecycle_events`.
- `include_all_aspects` (deprecated) is folded into `aspect_priority="all"`
  and respects the lifecycle size guard.
- Future-timeline predictions carry `prediction_basis`
  (`mean_orbital_period` / `typical_age`) and past-event summaries carry
  `approximate: true` - these are age arithmetic, not ephemeris searches.

### Added
- Lifecycle events on lunar return charts (previously documented but not
  implemented).
- `python -m immanuel_mcp` entry point (`immanuel_mcp/__main__.py`).
- Regression test suite `tests/test_audit_regressions.py` (33 tests) pinning
  every fix above.

### Removed
- `immanuel_mcp/charts/_legacy_import.py` (stub fallbacks masked import
  failures and printed to stdout, which corrupts the MCP stdio transport).
- Dead `estimate_response_size()` helper.

## [0.1.0] - 2025-12-03

### Added
- Natal chart generation (full and compact versions)
- Solar return charts (full and compact versions)
- Progressed charts (full and compact versions)
- Composite charts (full and compact versions)
- Synastry aspects (full and compact versions)
- Transit charts (full and compact versions)
- Chart summaries with essential information (Sun/Moon/Rising signs, chart shape, moon phase)
- Planetary positions with simplified format
- Configuration management for Immanuel library settings
- Comprehensive input validation and error handling
- Support for multiple coordinate formats (decimal, traditional DMS)
- Custom compact JSON serializer for optimized LLM token usage
- Comprehensive test suite with detailed result tracking

### Features
- MCP server integration for Claude Desktop and other MCP-compatible clients
- Flexible coordinate parsing (supports formats like "32n43", "32.71", "51°23'30\"N")
- Dynamic settings configuration (house systems, orbs, calculation methods)
- Detailed error messages with helpful suggestions
- Full logging support for debugging and monitoring

[0.1.0]: https://github.com/Jasperb3/Immanuel-MCP/releases/tag/v0.1.0

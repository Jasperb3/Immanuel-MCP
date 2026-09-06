# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-09-06

Adopts the ephemeris search functions immanuel 1.5.4 added but this server
never used, replacing two approximations with real searches and adding two
forecasting tools. No library upgrade: 1.5.4 is the newest release.

### Added
- **`get_lunations_and_eclipses`**: upcoming new moons, full moons and solar
  and lunar eclipses from a given moment, each with the Moon's sign and
  degree and both UTC and local times. Eclipses carry their type (Total,
  Annular, Partial, Annular total, Penumbral). Needs no birth data.
- **`get_sign_ingresses`**: dates planets change zodiac sign, defaulting to
  the slow bodies. Takes the earlier of the forward and backward crossing at
  each step, so retrograde re-entries are included and the sequence stays in
  date order — Saturn's 2025-26 move into Aries is three crossings, not one.
  Needs no birth data.
- **`exact_dates`** on lifecycle events: every perfection of a return or
  major transit, not just one. A retrograde outer planet perfects the same
  aspect up to three times.

### Changed
- **Lifecycle `exact_date` is now searched, not estimated.** It was a linear
  extrapolation from the transiting planet's instantaneous speed, flagged
  `exact_date_estimated: true`; it now comes from an ephemeris search and
  `exact_date_estimated` is `false`. Multi-pass events also get their true
  `date_range` (first perfection to last) in place of the orb-derived
  estimate. The progressed Moon keeps the estimate and its flag — it moves at
  a symbolic rate, not an ephemeris one, so there is nothing to search.
- **Lunar return search** now delegates to the library's fixed-point aspect
  search, converging to within 1e-6° instead of the previous under-a-minute
  bisection. Returned instants are unchanged to within ~20 seconds.
- **`immanuel` pinned to `>=1.5.4,<1.6`.** Upstream master already carries a
  breaking overhaul behind the next version (`ImmanuelSettings` renamed to
  `Config`, a module reshuffle, and a pyswisseph to pysweph migration) that
  an open-ended constraint would pull in unreviewed.
- Tool count 21 → 23; test count 112 → 124.

### Fixed
- **Sign ingresses and lifecycle perfections near a station.** immanuel's
  own searches bracket by stepping `1/|speed|` days, so as a planet
  approaches a station the step grows without bound and leaps over the
  crossing. Asked for Venus's next Aries ingress on 2025-03-28,
  `next_sign_ingress()` answers 2026-03-06, skipping the real re-entry on
  2025-04-30; Pluto's first crossing out of Aquarius was dropped the same
  way. Both searches here bracket by degrees travelled under a day cap
  instead, which a station cannot inflate.
- **The package could not be imported from a clean checkout.** `03c1809`
  removed `scripts/` from tracking and from disk, but
  `scripts/compact_serializer.py` was a runtime import of `immanuel_server`
  and of the lunar return module. It is restored byte-identical as
  `immanuel_mcp/serializers.py`, a tracked module of the package. The wheel
  `include` — which pointed at a root-level `compact_serializer.py` that has
  never existed at that path — is fixed alongside it.

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

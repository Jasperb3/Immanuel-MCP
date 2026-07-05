# Bug Reference

Root-cause documentation for significant bugs found and fixed. Each entry
records what future developers need to avoid reintroducing the same class of
defect. Regression tests for all entries live in
`tests/test_audit_regressions.py`.

---

## 2026-07-05 Audit Fixes (v0.5.0)

### 1. Aspect pagination classified by configured maximum orb (Critical)

**Symptom:** The default "tight" page of `generate_transit_to_natal` returned
almost no aspects (measured: 1) while many transits were genuinely partile
(16 within 2°). Every aspect displayed `orb: 10.0` or similar.

**Root cause:** In Immanuel's full (`ToJSON`) serialization, the aspect field
`orb` is the *configured maximum orb* for the aspect type
(`immanuel/reports/aspect.py` line 89: `"orb": orb` where `orb` comes from
settings). The *actual deviation from exactness* lives in `difference`.
`classify_aspect_priority` and `build_optimized_aspects` read `orb`. The
compact serializer was unaffected because it already copied
`difference.raw` into its own `orb` field.

**Solution:** `get_actual_orb()` in `immanuel_mcp/pagination/helpers.py`
resolves both serializer shapes; classification and display go through it.

**Lesson:** When consuming a library's serialized structures, verify field
semantics against the library source, not against the field name.

### 2. Tool registration split across FastMCP instances (Critical)

**Symptom:** `python -m immanuel_mcp` served 0 tools (and could not even be
launched - no `__main__.py`). `uv run immanuel_server.py` served 18 tools
with the lunar return tools missing. Importing `immanuel_server` as a module
silently disabled lifecycle events and printed to stdout.

**Root cause:** Three FastMCP instances existed (`immanuel_server.py`,
`immanuel_mcp/server.py`, plus a duplicate module created when
`_legacy_import.py` re-imported `immanuel_server` while it ran as
`__main__`). FastMCP registration is per-instance; importing already-
decorated functions does not register them on a different instance. The
circular chain `immanuel_server → immanuel_mcp/__init__ → server →
_legacy_import → immanuel_server` failed when immanuel_server was partially
initialized, and the `except ImportError` fallback installed stub functions
and printed a warning to stdout (which corrupts MCP stdio transport).

**Solution:** Single shared instance in `immanuel_mcp/app.py` (a leaf
module). `immanuel_mcp/__init__.py` no longer imports `.server` eagerly.
`_legacy_import.py` deleted. Lifecycle import is unconditional (fail fast).

**Lesson:** Decorator-based registration must target exactly one registry
object, defined in a leaf module. Never put fallback stubs behind an import
failure - they convert a loud startup error into silent wrong behavior.

### 3. DMS coordinates with seconds silently corrupted (Critical)

**Symptom:** `parse_coordinate("117w09'30")` returned **-132.5** instead of
-117.158 - no error, chart Ascendant/houses wrong by roughly a full sign.

**Root cause:** Quote delimiters were normalized to spaces, then the DMS
regex ran on the *space-stripped* string, so the greedy minutes group
consumed the seconds digits: `117w09 30` → `117w0930` → 117° 930' = 132.5°.
Latitudes usually tripped the ±90 range check; longitudes within ±180 did
not.

**Solution:** The regex matches the delimiter-normalized string directly
with bounded 2-digit minutes/seconds groups; both DMS branches validate
minutes/seconds < 60; digit-fused ambiguous input (`117w0930`) is rejected.

### 4. Datetime parser dropped short times as timezone tokens (Critical)

**Symptom:** `parse_datetime_value("2024-01-01 1:00")` returned midnight.

**Root cause:** The heuristic for stripping a trailing timezone token
(`token.upper() == token and len(token) <= 4`) also matched time strings -
digits are their own uppercase.

**Solution:** The token must contain `/` (IANA zone) or be purely alphabetic
(UTC, GMT, BST).

### 5. `timezone` parameter ignored in transit-to-natal (Major)

**Symptom:** Passing `timezone='UTC'` vs `'America/Los_Angeles'` produced
identical charts; the parameter was only echoed back in the response.

**Root cause:** Both `Subject`s were constructed without the timezone
argument, so Immanuel always inferred the zone from coordinates.

**Solution:** Both subjects go through `create_subject(..., timezone)`.

### 6. Aspect direction lost; cross-aspects deduplicated away (Major)

**Symptom:** Transit aspects labelled "Sun → Saturn" regardless of which
planet was transiting. In compact synastry, mirrored double-whammy contacts
(A's Saturn–B's Neptune AND A's Neptune–B's Saturn) collapsed to one entry.

**Root cause:** Immanuel assigns `active`/`passive` by *speed*, not by
chart. The only record of which chart each object belongs to is the nested
`{from: {to: aspect}}` key structure, which the flattening discarded. The
dedup key `(sorted planet names, type)` cannot distinguish distinct
cross-chart contacts.

**Solution:** The nesting keys are preserved as `from`/`to` fields and
surfaced as `transiting_object`/`natal_object` (transit-to-natal) or
`native_object`/`partner_object` (synastry). Dedup keys include the orb, so
identical mirrored duplicates still collapse while distinct cross-aspects
survive.

### 7. Lifecycle timing semantics wrong (Major)

**Symptom:** Events past exact and separating were labelled "applicative";
`exact_date` was just the request's transit date.

**Root cause:** No code computed separating status (it requires the
transiting planet's speed), and no perfection-date estimation existed.

**Solution:** `determine_movement()` and `estimate_exact_datetime()` in
`immanuel_mcp/lifecycle/returns.py` derive movement and a linear perfection
estimate from the planet's speed. Estimates are suppressed near stations and
flagged `exact_date_estimated: true` everywhere (retrograde passes can
produce several exact hits, which a single date cannot represent).

### 8. Lunar return imprecise and slow (Major)

**Symptom:** Return times up to ~11 minutes off (docs claimed 1-minute
accuracy) - enough to shift the return chart's Ascendant ~3° and potentially
change its rising sign. Each call built ~130 full Natal charts.

**Root cause:** The binary search early-exited at a 0.1° tolerance (the Moon
covers 0.1° in ~11 minutes), and every probe constructed a complete chart
just to read one Moon longitude.

**Solution:** The search runs in Julian-day space against
`immanuel.tools.ephemeris.get_planet` directly and bisects to under a minute.
Verified: Moon within ~0.001° at the returned moment; ~50x faster. Note the
previously documented example result (2025-01-18T04:57) was an artifact of
the old tolerance; the verified time is 05:27.

### 9. Lifecycle "now" reference off by the birth location's UTC offset (Major)

**Symptom:** Natal endpoints' current-transit reference chart was computed
for the wrong instant (up to ±12 h).

**Root cause:** `datetime.utcnow()` (naive, deprecated) formatted into a
`Subject` with no timezone, so the UTC timestamp was interpreted as local
time at the birth coordinates.

**Solution:** Aware UTC timestamp paired with an explicit `'UTC'` timezone.

### 10. Test suite poisoned by a hardcoded Windows path (Major, tests only)

**Symptom:** Running the full suite in the WSL clone imported modules from
`/mnt/c/Users/BJJ/Documents/MCP/astro-mcp` (the old Windows working copy),
so tests validated stale code.

**Root cause:** Five test files did
`sys.path.insert(0, '/mnt/c/Users/BJJ/Documents/MCP/astro-mcp')`.

**Solution:** They derive the repo root from their own file location.

**Lesson:** Never hardcode absolute machine paths in tests; with two working
copies of the same repo on one machine, the suite can silently test the
wrong one.

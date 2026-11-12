# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.12.2] - 2026-11-12

Fixes from testing in Claude Desktop.

### Fixed
- **Composite houses out of order.** immanuel takes each house cusp's
  midpoint on its own shorter arc, so when a pair of cusps is nearly 180°
  apart some composite cusps land on the far side of the circle (11 of 64
  London 1985 + Svalbard 1990 time pairs). The averaged house sizes also
  stopped matching the cusps, which put an MC sitting exactly on cusp 10 in
  house 9 (18 of 48 same-moment London/Svalbard pairs). Composite cusps now
  keep each chart's order (`immanuel_mcp/compat/composite.py`), sizes are
  recomputed from the cusps, and the MC, IC and Descendant are placed from
  the Ascendant the same way. Pairs whose midpoints don't wrap, and Whole
  Sign composites, are unchanged.
- **Charts at exactly 90°N or 90°S.** The Ascendant and houses are undefined
  there, but the Swiss Ephemeris returned 0° Aries (or a point tied to the
  Sun) with no error, giving spurious exact aspects such as Sun–Asc at
  0.01°. A chart with a known time at either pole (birth, partner, transit
  location or relocated return) is now an error, `type: "PoleError"`,
  suggesting `time_status="unknown"` or 89.99°. Untimed charts there still
  build, with their lifecycle section.
- **Custom object lists.** When the session object list is customised with
  `configure_immanuel_settings`, compact charts include every object in it
  (e.g. Chiron, Ceres, the nodes); they were silently dropped. Lifecycle events no longer depend on the session's
  object list: a list without Uranus or Chiron lost those events and pushed
  the timeline onto estimated dates.
- **Input errors.** An impossible date (1990-02-30) is reported as one, not
  as a format error. Every bad input (date, latitude, longitude, timezone)
  is reported in one message, where a bad timezone used to show only after
  the coordinates were fixed. Coordinate errors suggest the accepted formats
  instead of "Check the Immanuel documentation".

### Changed
- **Compact JSON text.** Tool results' text content is compact JSON instead
  of FastMCP's indent=2 (structured content is unchanged). A full natal
  chart's text drops from about 122k characters to 82k.
- **`include_lifecycle_events`** on natal, solar return, progressed and
  lunar return tools (full and compact), as transit-to-natal already had.
  Default `true`; `false` returns `lifecycle_events: null`.

## [0.12.1] - 2026-11-12

### Fixed
- **Polar charts with reversed house cusps.** At some moments inside a
  polar circle the Swiss Ephemeris returns Regiomontanus, Campanus and
  Polich Page cusps in reverse (clockwise) order, with the MC and IC
  swapped. Over 60 random moments per place, Regiomontanus and Campanus
  were reversed at 12 of 60 at Tromsø, 24 at Longyearbyen and 17 at
  McMurdo; Polich Page more often. immanuel's house lookup assumes
  zodiacal order, so these returned the error message `'index'`, or, for
  Polich Page, sometimes a chart with the houses scrambled. They are now
  an error with `type: "PolarHouseError"`, a message naming the system and
  latitude, and a suggestion to use Porphyry, Equal or Whole Sign. No other
  system and no chart outside the polar circles is affected.

## [0.12.0] - 2026-11-12

Requires immanuel 1.8 (`immanuel>=1.8.0,<1.9`), which fixes three of the
issues filed against 1.7. Tool output is unchanged: 22 representative
responses (day/night, polar, untimed, every chart type) are identical to
0.11.0's.

### Changed
- **Night-chart sect is immanuel's own again.** 1.8.0 restores `in_sect` on
  night charts ([theriftlab/immanuel-python#31](https://github.com/theriftlab/immanuel-python/issues/31)),
  so `compat/sect.py` is removed. Its tests stay as `tests/test_sect.py`.
- **Aspect patterns come from immanuel's `aspect_pattern_objects`.** 1.8
  added the setting (default Sun to Pluto) and stopped searching
  `aspects_to` charts ([#34](https://github.com/theriftlab/immanuel-python/issues/34)).
  Every Config the server builds sets it to the planets and Chiron, which
  replaces the serializer's own re-run of the search. On 1.8 that re-run
  would have silently dropped Chiron, because immanuel's default now
  filters it out. Cross-chart outputs still report `aspect_patterns: None`.
- **Polar shim narrowed.** 1.8 no longer hard-codes Placidus internally
  ([#32](https://github.com/theriftlab/immanuel-python/issues/32)), so polar
  Whole Sign, Equal, Porphyry etc. build without help. Placidus and Koch
  now raise `ValueError` upstream; the shim still retries them with
  Porphyry, because Placidus is the default.
- The fall-back clock-change warning ends with the two offset spellings
  that choose each reading, unless the input already carried one.

### Fixed
- **UTC offsets in `date_time` were dropped.** Given coordinates, immanuel
  replaces a time's own zone with the one it looks up from them (by design,
  [theriftlab/immanuel-python#33](https://github.com/theriftlab/immanuel-python/issues/33)),
  so `2026-06-01T12:00:00+05:00` in London was cast at 12:00 BST, five hours
  out, and `2026-10-25T01:30:00Z` at the first 01:30 (BST), an hour early.
  An offset now has to be one the location's zone has at that local time.
  On a clock-change night it chooses the reading, which makes the second
  01:30 of a fall-back night castable for the first time; any other offset
  is an error naming the offsets that fit. Times without an offset are
  unchanged. Applies to every birth and transit time passed to a chart
  tool, both people in composite and synastry included.
  `progression_date_time` still drops its offset (it goes to immanuel
  directly; the error there is minutes of arc at most).
- **Solar return lifecycle reference off by the zone difference.** The
  chart that lifecycle events are measured against was rebuilt from the
  return time as a zone-less clock string, read back in the coordinates'
  zone. A `timezone` other than that zone moved it by the difference (an
  hour for London with `timezone="UTC"`, five for `America/New_York`), a
  return in a fall-back night's repeated hour landed on the first reading,
  and every call lost the return's fractional second. It is now built from
  the return's Julian date, and the silent fallback to 1 January of the
  return year is gone. Lifecycle separations move by thousandths of a
  degree at most; the solar return chart itself was never affected.

## [0.11.0] - 2026-11-09

Migration to immanuel 1.7.0, released the same day. Known-time output is
identical to 0.10.5 apart from immanuel's own new `date_time.time_status`
field (below) and float noise of at most 6e-14 (True South Node), checked
over the 90-case snapshot set.

### Added
- **`time_status` on every tool that takes a birth time**: `"known"`
  (default), `"approximate"` or `"unknown"`, passed to immanuel 1.7's new
  `Subject(time_status=...)`. Composite and synastry take
  `native_time_status` and `partner_time_status`; transit-to-natal applies
  it to the natal chart only. Without a known time the chart omits houses,
  angles, the Vertex, the Parts of Fortune/Spirit/Eros, sect, day/night
  triplicity rulers and quadrant weightings, and `"unknown"` casts it for
  local noon. `applied_settings.house_system` is then `null` with a
  `time_status` key (`natal_time_status` on transit-to-natal, whose transit
  chart keeps its houses), a warning lists what is missing, and
  `get_chart_summary` returns `rising_sign`, `house_system` and `diurnal`
  as `null`. An invalid value is an error.
- **`moon_range`** on `generate_natal_chart` and
  `generate_compact_natal_chart` for an unknown time: the Moon at 00:00 and
  23:59 local on the birth date, and `sign_change`. The warning says when
  the Moon's sign itself is uncertain.
- **Untimed returns and progressions.** The return instant comes from the
  natal Sun or Moon, so the tools warn that it is uncertain (up to ~12 h
  for `"unknown"`), and the return chart omits houses and angles. Lunar
  return charts are cast as `TIME_APPROXIMATE` at the computed instant: as
  `TIME_UNKNOWN` immanuel would recast the instant at noon. Progressed
  charts warn about the progressed Moon's timing.

### Changed
- **Requires `immanuel>=1.7.0,<1.8`** (1.6 is no longer supported; scipy
  leaves the lock). Every full chart now carries immanuel's
  `date_time.time_status` (`"Known time"`, translated) on `native`,
  `partner`, `progressed_date_time`, `progression_date_time` and
  `solar_return_date_time`.
- Ephemeris searches read samples from 1.7's `sweph.longitude()`: same
  values, a third of the cost. A warm compact transit-to-natal call went
  from 49.3 to 42.1 ms.

### Fixed
- **`in_sect` on night charts.** immanuel 1.7.0 drops `in_sect` from every
  object in a chart with `diurnal: false` (`Chart.wrap_objects` only
  computes it for day charts). `compat/sect.py` probes one known night
  chart at startup and, only if the bug shows, recomputes it with
  immanuel's own `condition.is_object_in_sect`, as 1.6 did. Nothing tested
  sect before; all 402 tests passed on 1.7.0 with the bug in place.
- `get_planetary_positions` returns `house: null` instead of failing on a
  chart without houses.
- An untimed chart inside a polar circle no longer warns about a Porphyry
  fallback: it casts no houses.

## [0.10.5] - 2026-11-09

### Fixed
- **The top-level `house_system` names the polar fallback.** Inside a polar
  circle the cusps are Porphyry, and `applied_settings` and the warning
  said so, but the full chart tools' top-level `house_system` still read
  the requested system. Tromsø 1988-12-21 09:00 (69n39 18e57) with default
  houses: `get_chart_summary`, `generate_natal_chart`,
  `generate_solar_return_chart`, `generate_progressed_chart` and
  `generate_lunar_return_chart` read `"Placidus"`; they now read
  `"Porphyrius"`, immanuel's own name for the system (translated by
  locale), which is also the value `house_system=` accepts. A chart
  outside the polar circle, including a return relocated out of it within
  the same call, is unchanged. Compact tools have no such field.

## [0.10.4] - 2026-11-09

Fixes for the two gaps Ben's wider check of 0.10.3 found. Both are rare;
neither is a regression.

### Fixed
- **Both passes at a grazing station.** A planet that stations just past a
  target crosses it, turns, and crosses back. When both crossings fell
  inside one scan step the pair was lost, or not, depending on where the
  query date put the samples. 1984-01-01 San Diego's Neptune Square (target
  359.3776°, Neptune stationing 17.7″ past it) listed 2024-05-17 / 08-18 /
  2025-03-14 when queried on 2024-08-15, missing 2025-12-06 and 12-14. The
  scanner now also watches the sign of the speed and checks the side at
  each station that could hide a pair. It applies to every search on the
  scanner: lifecycle dates, returns and the sign-ingress calendar. Cost:
  about +4 ms per lifecycle chart (~46 → 50 ms warm), and a few ms on the
  default ingress calendar. 1,584 ingresses over 11 start dates are
  unchanged.
- **Sequences that cross the 20-year horizon are listed whole.** The
  future-timeline search stopped at the horizon, cutting a sequence that
  started inside it. Queried 2026-06-15 for London births: 1987-02-12
  Saturn Return Cycle 2 gained 2046-06-18 and 10-20; 2006-10-26 Neptune
  Square gained 2046-12-15 and 2047-03-08; 1971-01-19 Chiron Opposition
  gained 2046-08-21. The horizon still decides which events are listed (the
  first pass on or after the query must fall within it).

## [0.10.3] - 2026-11-09

Fixes from Ben's independent check of 0.10.2.

### Fixed
- **Active events report their whole pass sequence.** The active search
  sized its window from the planet's current speed and kept at most three
  hits, so a long sequence came back partial and moved with the query date.
  1990-05-15 London's Pluto Square (2033-03-25 / 07-11 / 2034-01-30 / 09-27 /
  11-29) read passes 2-3 on 2034-01-15 and the last two on 2035-03-01, and
  `date_range`, `age_at_event` and `current_stage.age_range` moved with it.
  It now lists all five whenever it is active, with `age_at_event` 42.9.
  **Correction to 0.10.1:** the 1984 San Diego Pluto Square also has five
  passes, from 2024-03-28 (age 40.2), not three from 2025-01-24 (41.1). The
  same chart's Neptune Square, which had no dates at all in one context,
  now lists its five. Where the full sequence shows a pass still ahead,
  `next_major_event` can now name the active event.
- **No lunar return is skipped.** The search used immanuel's
  `transit.next_aspect_to`, which steps a day on the unsigned distance and
  overshoots when the Moon accelerates during that day. 6 of 528 month
  searches (four charts, 2020-2030) skipped a return, e.g. 1990 London
  February 2026 errored ("No lunar return found"), though the Moon returns
  2026-02-14 23:51 UTC. It is now the station-safe signed scan, with a
  month-by-month sweep test against a brute-force scan. Return moments are
  also more exact (the Moon within 0.0001″ of natal, against 0.0035″), which
  moves them by a few milliseconds.
- **A lunar return in a fall-back night's repeated hour is cast at the right
  instant.** The chart was rebuilt from the local wall-clock time, which
  immanuel resolves to the first reading. A 1995-03-04 07:31:37 London
  birth's return at 01:30 GMT on 2026-10-25 was cast at 01:30 BST, an hour
  early, with a clock-change warning. It is now built from the Julian date.
- **One timestamp format.** `lunar_return_info.return_date` and
  `returns_in_month`, `solar_return_info.return_date`, and the lunation and
  ingress `date_time_utc`/`date_time_local` are ISO 8601 with whole seconds
  and an explicit offset (e.g. `2026-07-28T20:07:33+01:00`; previously
  `2026-07-28T20:07:33.143294`). Seconds are truncated, so a return at
  23:59:59.8 on the last day of a month still reads as that day.

## [0.10.2] - 2026-11-09

Fixes from a sweep of all 23 tools against independent Swiss Ephemeris
calculations on seven charts. Everything else matched.

### Added
- **Lunar return `occurrence`.** About one month in three holds two lunar
  returns, and the second was unreachable: 1990-05-15 London's July 2026 has
  1 July 13:51 BST and 28 July, and August gives 25 August. Both lunar-return
  tools take `occurrence` (default 1). `lunar_return_info.returns_in_month`
  lists every return of the month, and `lunar_return_info.occurrence` echoes
  the choice. A missing occurrence is an error naming the returns that exist.
- **`solar_return_info.return_date`** on both solar-return tools: the return
  moment, naive ISO in the birth timezone, like the lunar one. The compact
  tool reported no moment at all.
- A **`warnings`** list on chart and calendar responses, present only when
  there is something to report (polar fallback, clock changes).

### Fixed
- **Charts inside the polar circles.** Every chart tool failed with
  "swisseph.houses_ex2: within polar circle, switched to Porphyry" (e.g.
  1988-12-21 Tromsø), Whole Sign included, because immanuel hard-codes
  Placidus for the Part of Fortune and the diurnal check, and pysweph raises
  the Swiss Ephemeris warning as an error. A version-guarded shim retries that
  error with Porphyry. Placidus and other polar-sensitive systems get
  Porphyry cusps, `applied_settings.house_system` reads "Porphyry (polar
  fallback from Placidus)", and a warning says why. A non-polar system such
  as Whole Sign gets that system with no warning. Non-polar charts are
  byte-identical.
- **North Node returns list every crossing.** The true node wobbles, so
  1990-05-15 London's node crosses the natal node on 2027-09-22, 25 and 26.
  `exact_dates` held one of them, chosen by the query date (09-22 from
  2026-11-08, 09-26 from 2019-12-01). The nodes now scan at 6-hour steps:
  `exact_dates` lists all three, `exact_date` is the first ahead,
  `date_range` spans them (2027-09-22 to 2027-09-26, where it used to be a
  mean-speed orb window), and none of it depends on the query date.
- **Validation.**
  - An unknown `aspect_priority` is rejected with the valid list, instead of
    silently becoming `tight`.
  - A `progression_date_time` before birth is rejected.
  - An unknown timezone reads "Unknown IANA timezone 'Mars/Olympus'"; tzdata
    is suggested only when no zone database is installed.
  - A local time inside a clock change is still accepted, but now carries a
    warning naming the reading used. Example: "01:30 did not exist on
    1990-03-25 in Europe/London (the clocks went forward); using 01:30 GMT
    (UTC+0), the same instant as 02:30 BST (UTC+1)".

## [0.10.1] - 2026-11-08

Follow-ups from the 0.10.0 smoke test. Two lifecycle fields now come from
the ephemeris-dated events instead of textbook ages.

### Fixed
- **`age_at_event` is the age on the event's date.** Future major transits
  reported the textbook `typical_age`, because the formatter read an `age`
  field only active events carry. Active events reported today's age.
  Examples: a 1990-05-15 London chart's Neptune Square (2031-05-09), Pluto
  Square (2033-03-25) and Uranus Opposition (2034-08-19) read 39 / 36 / 41
  and now read 41.0 / 42.9 / 44.3. A 1984-01-01 San Diego chart's Uranus
  Opposition (2028-06-19) read 41 and now reads 44.5. Its active Pluto
  Square, queried 2026-11-08, read 42.9 (the current age) and now reads
  41.1, the first pass of its sequence (2025-01-24). Upcoming events use
  their `exact_date`, the progressed Moon its estimated perfection (it
  showed the current age), and only the arithmetic fallback
  (`exact_date_estimated: true`) keeps `typical_age`.
- **`lifecycle_summary.current_stage` follows the chart.** It came from a
  fixed age table, so the 1984 chart at 42.9 read "Uranus Opposition"
  (band 41–43) while `next_major_event` dated that opposition 2028–29. The
  stage is now the most significant HIGH/CRITICAL event under way, else one
  that ended within three years, else the age band. A new `stage_basis` field
  says which: `"ephemeris"` ("Pluto Square", `age_range` [41.1, 41.9]),
  `"ephemeris_past"` ("After Saturn Return Cycle 1", for the 1990 chart in
  mid-2022) or `"age_band"` ("Post-Saturn Return", [31, 36]). `age_range` is
  the event's `date_range` in years of age. The response shape is otherwise
  unchanged.
- `configure_immanuel_settings` lists `en_US` among the locales, and a
  fixed-star rejection explains that the star catalogue (`sefstars.txt`) is
  not shipped.

### Investigated
- **Cold start.** Desktop's launch command, timed with a stdio client on
  Windows: `initialize` in 1.3–2.4 s, first lifecycle call in 0.06–0.07 s,
  warm or right after a reinstall, on 0.10.0 and 0.10.1 alike. The 60 s
  first-call timeouts came from the remote bridge or Desktop's reconnect. No
  server change; see the README's troubleshooting section.

## [0.10.0] - 2026-11-08

Follow-ups from the 0.9.0 Claude Desktop smoke test. Lifecycle date fields
change meaning (they are now real perfections) and compact aspects gain a
field, hence the minor bump.

### Changed
- **Future lifecycle events are dated by the ephemeris.** Upcoming returns and
  major transits used to be age arithmetic: once a native passed a transit's
  typical age, its `exact_date` was simply the query date (flagged estimated),
  and `date_range` was ±orb/mean-speed around it, so both moved with the query
  date. Each event's next pass sequence is now searched, so `exact_date` is the
  first pass on or after the query date, `exact_dates` the whole sequence,
  `date_range` first-to-last pass, `exact_date_estimated: false` and
  `prediction_basis: "ephemeris"`. Example: a 1 Jan 1984 chart's Uranus
  Opposition is 2028-06-19 / 2028-12-29 / 2029-04-05 whatever the query date.
  The `age_range` gate is gone: that perfection is at age 44.5, and the old
  gate dropped the event from the timeline after 43. Mean-period returns are
  real too: that chart's next Mars Return is 2027-08-25, not the
  arithmetic's 2027-03-29, when Mars is 64° away. The arithmetic remains only
  as a fallback without a natal chart.
- **`lifecycle_summary.next_major_event`** is the earliest pass still ahead
  among HIGH/CRITICAL events, with `next_major_event_date` and
  `years_until_event` from that pass. It used to be the first active event,
  dated with the query date: for the 1984 chart, a Pluto Square whose passes
  were all behind it. A sooner MODERATE event (that Mars Return) is skipped.
- **Aspect patterns are built from the ten planets and Chiron only.** immanuel
  used every chart aspect, so the Asc, MC, Part of Fortune and Lilith became
  vertices. Patterns are recomputed with immanuel's own search from
  planet-only aspects; given all aspects this reproduces immanuel's output
  exactly, and the shape is unchanged. Charts built against another chart get
  `aspect_patterns: null`. Transit and natal objects share indices, so the
  search merged both charts into the same vertices; no tool output exposed
  those, and now none can.
- Compact aspects carry an `angle` field (e.g. `120.0`), the locale-proof
  identity of the aspect.

### Fixed
- **Same-planet transits are back.** Transit-to-natal removed every aspect
  between the same planet in both charts as a "self-aspect": transit Saturn
  conjunct natal Saturn (the Saturn Return), the Uranus opposition, the Pluto
  square, Sun–Sun synastry. The full tool always dropped them; compact
  transit-to-natal and compact synastry dropped them only with
  `include_interpretations=True`, the default, so results depended on that
  flag. A single chart never aspects an object to itself, so the filter is
  gone. On a 1990 chart queried at 2019-12-01, the 0.7° Saturn Return now
  appears in every transit-to-natal output.
- **Interpretations no longer go generic in a non-English session.** The
  lookup keyed on the translated aspect and planet names, so under `pt_BR`
  every aspect fell back to "energy, connection, influence". It now keys on
  the object indices and the aspect angle. English output is unchanged. The
  interpretive prose itself (aspect keywords and interpretations, lifecycle
  text) stays English by design, so a localized response mixes translated
  chart data with English text.

### Performance
- The ephemeris crossing search may skip ahead when a body is far from its
  target (distance ÷ 1.5 × the body's maximum speed, measured over
  1900–2100). Without it the new lifecycle dating made a transit-to-natal call
  0.25 s instead of 0.02 s; with it, 0.05 s. A body cannot reach the target
  sooner, so no crossing can be skipped. The only differences from the
  stepped scanner (3 in 792 searches) are station pairs inside one step, its
  documented blind spot. One of those was a Venus pair that only the skip
  found.

### Not changed
- The slow first call after the 0.9.0 restart could not be reproduced. On
  Windows the server answers `initialize` in ~1.5 s (~3 s after a
  `pyproject.toml` change triggers a `uv run` rebuild), and the first natal
  chart takes 0.05 s, including straight after a fresh immanuel install. The
  wait happens in Claude Desktop while it starts its servers. Documented under
  Troubleshooting.

## [0.9.0] - 2026-11-08

Moves to immanuel 1.6. Response content changes (more aspects, a new key,
arcsecond drift), so this is a minor bump.

### Changed
- **Requires `immanuel>=1.6.0,<1.7`.** immanuel 1.6 replaces `pyswisseph` with
  `pysweph`. Both install the same `swisseph` module, so **run this server in
  its own environment and never co-install it with kerykeion <6** (or
  `kerykeion[swiss]`): with `pysweph` present, kerykeion silently returns
  `house = None` for some planets.
- **Settings are a per-session `charts.Config`, not immanuel's global
  singleton** (1.6 removes `immanuel.setup`). `configure_immanuel_settings`
  edits one session Config, `reset_immanuel_settings` replaces it with a copy
  of the startup Config, and every chart takes `config=` and freezes it at
  construction. Tool names, parameters and response shapes are unchanged.
  `build_call_settings` is kept as an alias of `build_call_config` for one
  release.
- **More aspects: Chiron (and Ceres, if configured) now gets planet-sized
  orbs**, e.g. 5.5° → 10° and 3.5° → 6°. On the four reference charts this
  added 104 aspects and removed none; every added one involves Chiron. These
  are upstream's defaults, accepted unchanged.
- **Positions drift by about ±1 arcsecond** (new ephemeris build). The
  `formatted`/`seconds` fields of longitudes, declinations and aspect
  distances can change by a second. Ingress times move by that drift divided
  by the planet's speed: seconds for Jupiter and Saturn, minutes for Uranus
  and Neptune, up to ~3 hours for Pluto. Lunation times move by under 0.1 s.
- Full charts carry a new top-level `aspect_patterns` key (T-square, grand
  trine, yod, grand cross, kite, mystic rectangle, cradle, grand sextile,
  grand quintile).
- In single-chart compact aspects (natal, returns, progressed, composite)
  `from_object`/`to_object` can be swapped relative to 0.8.x: 1.6 orders the
  active/passive pair consistently. The direction-carrying cross-chart tools
  (synastry, transit-to-natal, `natal_cross_aspects`) are unaffected.
- The configure tool's `angles` key is removed: it is not an immanuel setting
  and configuring it was a silent no-op.

### Fixed
- **Compact charts no longer come back empty under 1.6.** immanuel 1.6 turned
  `immanuel.const.data.OBJECTS/HOUSES/ASPECTS` into ints while serialized
  charts kept the string keys, so the compact serializer missed every lookup:
  `objects`, `houses` and `aspects` (and transit-to-natal's
  `transit_positions`/`transit_to_natal_aspects`) were empty with
  `status: success`. Keys are now the string constants in `constants.py`.
- **`locale` works without an OS locale and no longer breaks the session.**
  On 1.5.4, `configure_immanuel_settings("locale", "pt_BR")` failed on a host
  without that OS locale, and every later chart call failed with it. 1.6
  translates per chart from its own files; the locale/cache workaround is
  deleted and reset restores English. Values are validated against the
  locales immanuel ships (`de_DE`, `es_ES`, `pt_BR`, plus `en_US` for
  English): 1.6 silently falls back to English for an unknown locale, so a
  typo used to report success and change nothing. `list_available_settings`
  lists them.
- **Compact charts keep their major aspects in a non-English locale.** The
  compact serializer chose major aspects by English name, so with
  `locale=de_DE` a natal chart kept 3 of its 17 major aspects (only
  "Opposition" is spelled the same). It now matches on the aspect angle.
  English output is byte-identical.
- **`configure_immanuel_settings("aspects", ...)` accepts names.**
  `"CONJUNCTION,TRINE"` failed with `invalid literal for int()`. Names now
  resolve via `immanuel.const.calc` or immanuel's display names, ignoring
  case, hyphens and spaces (`"Semi-sextile"` works), angles from 0 to 180
  (`"120"`, `"54.3"`) are accepted, and anything else is rejected with the
  valid names. `list_available_settings` now shows immanuel's own aspect names
  under `aspects.available` (its hand-kept table spelled "Sesquiquadrate",
  which nothing accepted).
- **`configure_immanuel_settings("objects", ...)` resolves names.** `"SUN,MOON"`
  was stored as fixed-star strings, so the next chart failed with
  `Invalid object index`. Names and codes now resolve via
  `immanuel.const.chart`. Anything else is accepted only if immanuel's
  ephemeris can resolve it: an asteroid's official number whose ephemeris file
  is installed (`"433"`), or a fixed-star name. Otherwise the call is rejected
  and the session left unchanged.
- **`reset_immanuel_settings` reports every change it makes.** Its diff left
  out the orb settings and `orb_calculation`, and compared `objects` and
  `aspects` only by count, so resetting `default_orb` from 5 back to 1 said
  "Nothing changed". The summaries now include every configurable key, and
  `changed` compares the full lists.
- **`*_orb` keys are limited to the real orbs** (`default_orb`, `exact_orb`,
  `chart_shape_orb`). Any key ending `_orb` used to be set on the config,
  real or not.
- **North Node returns work.** Lifecycle looked up the mean node, which charts
  do not contain, and raised `'NoneType' object has no attribute 'longitude'`
  on every call. The ephemeris scanner also could not search the nodes at all
  (`ephemeris.get_planet` knows only planets), which broke the nodal return's
  exact dates and `get_sign_ingresses(planets=["North Node"])`.
  **Visible output change:** nodal returns now appear in lifecycle output, and
  future-timeline "North Node Return" entries carry `current_angular_separation`,
  `orb_status` and `movement` where they used to be null. "North Node" /
  "South Node" now mean the true nodes everywhere (they already did in chart
  output), so explicitly requested node ingresses report the true node.
  Because the nodes normally move backwards, their ordinary ingresses are not
  flagged `retrograde_re_entry`; the flag marks a move against that motion.

### Tests
- `test_lifecycle_fixes.py` reported failure by returning 1, which pytest
  ignores; it now asserts. The README banner counts only tests expected to
  pass (strict xfails are deselected).
- `test_immanuel_server.py` recorded failures instead of raising, so it always
  passed. It now re-raises. The 9 tests that were already failing on 0.8.1
  (checked against a clean `main`) are strict `xfail`s with the reason.
- New regression tests: every compact tool returns populated blocks; reset
  changes the next chart's actual cusps; `_session_config` is referenced only
  inside `utils/settings.py`; locale round-trip; per-call isolation;
  configure validation; node returns and ingresses.
- Suite runs in ~5 s instead of ~21 s.

## [0.8.1] - 2026-09-06

### Fixed
- **`generate_transit_to_natal` no longer reports `timezone: null`.** Both the
  full and compact tools echoed the raw `timezone` parameter, which is None
  whenever the caller omits it - even though immanuel had already inferred a
  zone from the coordinates and built the chart with it. The field now reports
  the zone the chart was actually built in. An explicitly passed timezone is
  echoed unchanged, as before.

### Added
- `effective_timezone(subject)` in `immanuel_mcp/utils/subjects.py`, which
  reads the resolved zone from the parsed datetime's tzinfo. `Subject.timezone`
  holds only what the caller passed and is not a reliable source for it.

## [0.8.0] - 2026-09-06

Fixes four defects reported from live use against Claude Desktop. Two change
response shapes, hence the minor rather than patch bump.

### Fixed
- **Compact charts now compact the `houses` block.** The compact serializer
  flattened `objects` and `aspects` but copied `houses` verbatim from the full
  chart, so every "compact" response carried immanuel's full nested wrapper for
  all twelve cusps — direction, degrees/minutes/seconds, decan, speed,
  declination, size. Houses are now flattened to `number`, `sign`,
  `sign_longitude` and raw `longitude`, matching the shape `objects` already
  used: **8550 → 1370 bytes on a natal chart (84% smaller, 7.2 KB saved)**.
  Affects every compact tool, lunar returns included.
- **Seconds in `generate_transit_to_natal` no longer carry a minutes mark.**
  `format_position` trimmed seconds by splitting on the arcsecond mark — which
  sits *after* the digits — then re-appended an apostrophe, turning immanuel's
  correct `12°21'42"` into `12°21'42'`. The digits survived wearing the wrong
  symbol, so the docstring's promised `28°51'` was never produced either.
  `format_declination` had the identical defect. Both now pass immanuel's
  already-correct string through untouched.
- **`reset_immanuel_settings` no longer changes settings silently.** It rebuilt
  a fresh `ImmanuelSettings` (library defaults: Placidus, no locale) and
  reported only the restored values, so a session already reconfigured before
  the caller inspected it was *changed* rather than reverted — and
  `house_system` is global state affecting every subsequent chart's cusps.
- **House-system numeric codes are accepted.** `list_available_settings`
  displayed codes such as `108` that `configure_immanuel_settings` rejected.

### Added
- Settings are snapshotted at server import, so `reset_immanuel_settings`
  restores the server's **startup configuration** rather than library defaults;
  a server configured at launch now resets to its launch configuration.
- `reset_immanuel_settings` returns `previous_settings`, `restored_settings`
  and `changed`. `restored_defaults` is retained as an alias for one release.
- `resolve_house_system` accepts numeric codes (`108`, `"108"`), constant names
  (`PLACIDUS`) and display names (`"Placidus"`, `"Equal House"`). Display names
  diverge from constant names for `EQUAL`, `VEHLOW_EQUAL` and `POLICH_PAGE`, so
  the names the tool advertised were themselves being rejected.
- `list_available_settings` reports `available_systems` as `{code, name,
  accepts}`, so every displayed value is a valid input.
- `tests/test_issue_followups.py` pins all four fixes (15 tests).
- Release-stamp guards: tests asserting `immanuel_mcp.__version__` and the
  README banner both match `pyproject.toml`, and that the banner's tool and
  test counts match reality. The version and counts live in four places and
  had twice drifted apart; these fail loudly rather than shipping a stale
  banner.

### Changed
- `immanuel_mcp.__version__` is single-sourced: it reads package metadata via
  `importlib.metadata`, falling back to parsing `pyproject.toml` when the
  package is imported from a source checkout that was never installed. The
  version is no longer a duplicated literal, so it cannot drift again.
- `configure_immanuel_settings` reports `old_value` and `new_value` in one
  vocabulary; `old_value` used to be a raw numeric code against a name.
- Restoring the locale now clears immanuel's `Localize` state, which otherwise
  kept serving the previous language while `settings.locale` reported the
  restored value.

### Removed
- Dead, byte-identical copy of `build_optimized_transit_positions` in
  `optimizers/dignities.py`. It called `format_position`/`format_declination`
  without importing them and would have raised `NameError`; leaving it would
  have kept the seconds bug alive in a second copy.

### Breaking
- The compact `houses` block changed shape (nested wrapper → four flat keys).
- `reset_immanuel_settings` returns new top-level keys; `restored_defaults`
  still works but is deprecated.

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
- **Lifecycle response schema.** No field is removed or renamed: `exact_dates`
  is added, and `exact_date_estimated` now reports `false` on return and
  major-transit events (it stays `true` on the progressed Moon). Clients
  reading `exact_date` keep working, but any that branch on
  `exact_date_estimated` will now take the other branch.
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
- Tool count 21 → 23; test count 112 → 127.

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

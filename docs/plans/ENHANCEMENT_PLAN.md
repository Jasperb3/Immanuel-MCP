# Immanuel MCP Server Enhancement Plan

This document outlines planned enhancements for the Immanuel MCP Server, organized by priority and implementation effort.

## Current Status

- **Version**: 0.2.1
- **MCP SDK**: 1.10.1
- **Immanuel Library**: 1.5.0
- **Tools**: 18 (9 full + 9 compact chart tools)
- **Recent Changes**: Bug fixes for coordinate parsing and chart summary functionality

---

## Priority 1: Quick Wins (Low Effort, High Impact)

### 1.1 Transit-to-Natal Tool
**Status**: ✓ Completed (v0.2.0)

Calculate transiting planets' aspects to natal chart positions for any given date.

**Use Cases**:
- Daily transit analysis
- Event timing
- Predictive astrology

**Implementation**:
- `generate_transit_to_natal()` - Full transit aspects to natal chart
- `generate_compact_transit_to_natal()` - Filtered major aspects only

---

### 1.2 Timezone Parameter
**Status**: ✓ Completed (v0.2.0)

Add explicit timezone support to all chart generation functions.

**Current Behavior**: Relies on coordinates for timezone inference
**Proposed**: Accept optional `timezone` parameter (IANA format, e.g., "America/New_York")

**Benefits**:
- More precise calculations for historical dates
- Handle daylight saving time edge cases
- Support locations without clear timezone inference

---

### 1.3 Aspect Interpretation Hints
**Status**: ✓ Completed (v0.2.0)

Include brief interpretive keywords for each aspect in chart output.

**Example Output**:
```json
{
  "type": "trine",
  "object1": "Sun",
  "object2": "Moon",
  "orb": 2.5,
  "keywords": ["harmony", "flow", "ease"],
  "nature": "benefic"
}
```

**Benefits**:
- Better context for LLM interpretation
- Reduces need for aspect lookup
- Consistent interpretive framework

---

## Priority 2: New Chart Types (Medium Effort)

### 2.1 Davison Relationship Chart
Calculate the midpoint in time (not space) between two birth charts.

**Difference from Composite**:
- Composite: Midpoint of planetary positions
- Davison: Chart for midpoint date/time at midpoint location

### 2.2 Lunar Return Chart
Monthly chart when Moon returns to natal position.

**Parameters**:
- Natal data
- Return month/year

### 2.3 Harmonic Charts
Support for harmonic analysis (5th, 7th, 9th, etc.)

**Use Cases**:
- 5th harmonic: Creativity, pleasure
- 7th harmonic: Inspiration, mysticism
- 9th harmonic: Joy, spiritual gifts

### 2.4 Profection Chart
Annual profections using traditional time-lord technique.

**Output**:
- Profected house lord
- Activated planets
- Time lord periods

---

## Priority 3: Architecture Improvements (Medium-High Effort)

### 3.1 Structured Output Support
Return typed Pydantic models instead of raw dictionaries.

**Benefits**:
- Type safety
- IDE autocompletion
- JSON Schema generation for MCP

**Example**:
```python
class NatalChartResponse(BaseModel):
    sun_sign: str
    moon_sign: str
    rising_sign: str
    planets: List[PlanetPosition]
    aspects: List[Aspect]
```

### 3.2 Caching Layer
Cache ephemeris calculations for repeated queries.

**Implementation**:
- LRU cache for ephemeris data
- Time-based cache invalidation
- Optional Redis backend for multi-instance deployments

**Expected Performance**: 50-70% speed improvement for repeated calculations

### 3.3 Batch Operations Tool
Process multiple charts in a single request.

**Use Cases**:
- Compare multiple natal charts
- Generate family/group analysis
- Bulk historical event analysis

**Example**:
```python
@mcp.tool()
def generate_batch_natal_charts(charts: List[ChartInput]) -> List[NatalChart]:
    ...
```

### 3.4 MCP Resources
Expose configuration as MCP resources for dynamic access.

**Resources**:
- `settings://house-system` - Current house system
- `settings://orbs` - Aspect orb configuration
- `settings://objects` - Enabled celestial objects

---

## Priority 4: Advanced Features (High Effort)

### 4.1 Fixed Stars Support
Include major fixed stars in chart calculations.

**Stars to Include**:
- Royal stars (Regulus, Aldebaran, Antares, Fomalhaut)
- Prominent stars (Spica, Algol, Sirius, etc.)

### 4.2 Arabic Parts Calculator
Calculate traditional Arabic parts (lots).

**Built-in Parts**:
- Part of Fortune
- Part of Spirit
- Part of Marriage
- Part of Death

**Custom Parts**: Allow user-defined formulas

### 4.3 Dignity Scoring
Calculate essential and accidental dignities.

**Essential Dignities**:
- Domicile, Exaltation, Triplicity, Term, Face
- Detriment, Fall

**Accidental Dignities**:
- House placement strength
- Aspects received
- Speed and direction

### 4.4 PDF Chart Generation
Generate visual wheel chart images.

**Options**:
- Traditional wheel
- Modern bi-wheel (for synastry/transits)
- Aspect grid

**Format**: PDF or PNG output

---

## Priority 5: Distribution Improvements

### 5.1 Desktop Extension (.mcpb)
Package as installable Claude Desktop extension.

**Benefits**:
- One-click installation
- Automatic dependency management
- No manual configuration required

**Requirements**:
- Create `manifest.json`
- Bundle dependencies
- Test with Claude Desktop extension installer

### 5.2 Docker Container
Containerized deployment option.

**Dockerfile**:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uv", "run", "python", "immanuel_server.py"]
```

### 5.3 PyPI Publication
Publish to Python Package Index.

**Installation**:
```bash
pip install immanuel-mcp
immanuel-mcp  # Run server
```

---

## Implementation Timeline

### Phase 1 (Completed)
- [x] Fix stdio transport logging issue
- [x] Transit-to-Natal tool (both full and compact versions)
- [x] Timezone parameter (added to all chart functions)
- [x] Aspect interpretation hints (keywords and nature for each aspect type)

### Phase 2 (Next Release)
- [ ] Lunar Return chart
- [ ] Caching layer
- [ ] Batch operations

### Phase 3 (Future)
- [ ] Desktop Extension packaging
- [ ] Docker container
- [ ] Structured output with Pydantic

---

## Contributing

When implementing enhancements:

1. Follow existing code patterns in `immanuel_server.py`
2. Add both full and compact versions of new chart tools
3. Include comprehensive docstrings for MCP tool discovery
4. Update tests in the test suite
5. Update this document when completing features

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2024 | Initial release with 16 tools |
| 0.1.1 | 2024-12 | Fixed stdio logging issue |
| 0.2.0 | 2024-12-18 | Priority 1 enhancements: Transit-to-Natal tools, timezone parameter, aspect interpretations |
| 0.2.1 | 2024-12-20 | Bug fixes: coordinate parsing (DMS with 'E' direction), natal_summary returning "Unknown", enhanced error handling and logging |

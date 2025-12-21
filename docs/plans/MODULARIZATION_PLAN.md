# Code Modularization Plan

**Date**: 2025-12-21
**Current State**: Single file (2,534 lines, 98 KB)
**Goal**: Modular architecture + Add Lunar Return Chart

## Executive Summary

Refactor `immanuel_server.py` (2,534 lines) into a modular package structure while simultaneously adding Lunar Return Chart functionality. This will improve maintainability, testability, and make future feature additions easier.

## Current Problems

1. **Single Large File**: 2,534 lines in one file is difficult to navigate
2. **Mixed Concerns**: Utilities, validators, chart generators, optimizers all in one place
3. **Hard to Test**: Cannot easily unit test individual components
4. **Difficult to Extend**: Adding new features requires navigating entire file
5. **No Clear Organization**: Functions scattered throughout file

## Proposed Structure

```
immanuel_mcp/
├── __init__.py                      # Package initialization
├── server.py                        # MCP server setup and registration
├── constants.py                     # CELESTIAL_BODIES, chart constants
│
├── utils/                           # Utility functions
│   ├── __init__.py
│   ├── coordinates.py               # parse_coordinate, validate_inputs
│   ├── subjects.py                  # create_subject helper
│   └── errors.py                    # handle_chart_error
│
├── optimizers/                      # Response optimization
│   ├── __init__.py
│   ├── positions.py                 # format_position, build_optimized_transit_positions
│   ├── aspects.py                   # build_optimized_aspects, classification
│   └── dignities.py                 # extract_primary_dignity, build_dignities_section
│
├── pagination/                      # Aspect pagination
│   ├── __init__.py
│   └── helpers.py                   # classify_aspect_priority, build_pagination_object
│
├── charts/                          # Chart generation (one file per chart type)
│   ├── __init__.py
│   ├── base.py                      # Base chart generation logic
│   ├── natal.py                     # Natal charts (full + compact)
│   ├── solar_return.py              # Solar return charts
│   ├── lunar_return.py              # 🆕 Lunar return charts
│   ├── progressed.py                # Progressed charts
│   ├── composite.py                 # Composite charts
│   ├── synastry.py                  # Synastry aspects
│   ├── transit.py                   # Transit charts
│   └── transit_to_natal.py          # Transit-to-natal aspects
│
└── interpretations/                 # Aspect interpretations
    ├── __init__.py
    └── aspects.py                   # ASPECT_INTERPRETATIONS, get_context_aware_interpretation
```

## Benefits

### Immediate
- ✅ **Easier Navigation**: Find code faster (e.g., all natal chart code in one file)
- ✅ **Better Organization**: Related functions grouped together
- ✅ **Clearer Responsibilities**: Each module has a single, clear purpose

### Long-term
- ✅ **Easier Testing**: Can test individual modules in isolation
- ✅ **Better Maintainability**: Changes localized to specific modules
- ✅ **Simpler Feature Addition**: New chart types = new file in charts/
- ✅ **Easier Onboarding**: New developers can understand structure quickly
- ✅ **Reusability**: Modules can be reused in other projects

## Implementation Plan

### Phase 1: Setup Module Structure (30 minutes)

**Step 1.1: Create Directory Structure**
```bash
mkdir -p immanuel_mcp/{utils,optimizers,pagination,charts,interpretations}
touch immanuel_mcp/__init__.py
touch immanuel_mcp/{utils,optimizers,pagination,charts,interpretations}/__init__.py
```

**Step 1.2: Create Empty Module Files**
```bash
# Utils
touch immanuel_mcp/utils/{coordinates,subjects,errors}.py

# Optimizers
touch immanuel_mcp/optimizers/{positions,aspects,dignities}.py

# Pagination
touch immanuel_mcp/pagination/helpers.py

# Charts
touch immanuel_mcp/charts/{base,natal,solar_return,lunar_return,progressed,composite,synastry,transit,transit_to_natal}.py

# Interpretations
touch immanuel_mcp/interpretations/aspects.py

# Server
touch immanuel_mcp/server.py
touch immanuel_mcp/constants.py
```

### Phase 2: Extract Constants (15 minutes)

**File**: `immanuel_mcp/constants.py`

**Move**:
- `CELESTIAL_BODIES` mapping (lines 56-84)
- Any other constants

**Why First**: Constants have no dependencies, safest to move

### Phase 3: Extract Utilities (30 minutes)

**File**: `immanuel_mcp/utils/coordinates.py`
**Move**:
- `parse_coordinate()` (lines 296-396)

**File**: `immanuel_mcp/utils/subjects.py`
**Move**:
- `create_subject()` helper function

**File**: `immanuel_mcp/utils/errors.py`
**Move**:
- `handle_chart_error()` (lines 461-479)
- `validate_inputs()` function

### Phase 4: Extract Optimizers (45 minutes)

**File**: `immanuel_mcp/optimizers/positions.py`
**Move**:
- `format_position()` (lines 91-110)
- `format_declination()` (lines 113-128)
- `build_optimized_transit_positions()` (lines 170-204)

**File**: `immanuel_mcp/optimizers/dignities.py`
**Move**:
- `extract_primary_dignity()` (lines 131-167)
- `build_dignities_section()` (lines 207-233)

**File**: `immanuel_mcp/optimizers/aspects.py`
**Move**:
- `build_optimized_aspects()` (lines 236-293)

### Phase 5: Extract Pagination (30 minutes)

**File**: `immanuel_mcp/pagination/helpers.py`
**Move**:
- `classify_aspect_priority()` (lines 1820-1841)
- `filter_aspects_by_priority()` (lines 1844-1862)
- `classify_all_aspects()` (lines 1865-1884)
- `build_aspect_summary()` (lines 1887-1922)
- `build_pagination_object()` (lines 1925-1973)
- `estimate_response_size()` (lines 1976-1987)

### Phase 6: Extract Interpretations (20 minutes)

**File**: `immanuel_mcp/interpretations/aspects.py`
**Move**:
- `ASPECT_INTERPRETATIONS` dict (lines 1278-1532)
- `get_context_aware_interpretation()` (lines 1535-1577)
- `normalize_aspects_to_list()` (lines 1764-1777)
- `add_context_aware_interpretations()` (lines 1780-1813)

### Phase 7: Extract Chart Generation (2 hours)

**File**: `immanuel_mcp/charts/base.py`
**Create**: Base class/helpers for common chart generation patterns

**File**: `immanuel_mcp/charts/natal.py`
**Move**:
- `generate_natal_chart()` (lines 483-535)
- `generate_compact_natal_chart()` (lines 538-589)
- `get_chart_summary()` (lines 592-649)
- `get_planetary_positions()` (lines 652-707)

**File**: `immanuel_mcp/charts/solar_return.py`
**Move**:
- `generate_solar_return_chart()` (lines 710-770)
- `generate_compact_solar_return_chart()` (lines 773-838)

**File**: `immanuel_mcp/charts/progressed.py`
**Move**:
- `generate_progressed_chart()` (lines 841-906)
- `generate_compact_progressed_chart()` (lines 909-974)

**File**: `immanuel_mcp/charts/composite.py`
**Move**:
- `generate_composite_chart()` (lines 977-1052)
- `generate_compact_composite_chart()` (lines 1055-1130)

**File**: `immanuel_mcp/charts/synastry.py`
**Move**:
- `generate_synastry_aspects()` (lines 1133-1219)
- `generate_compact_synastry_aspects()` (lines 1222-1275)

**File**: `immanuel_mcp/charts/transit.py`
**Move**:
- `generate_transit_chart()` (lines 398-444)
- `generate_compact_transit_chart()` (lines 447-458)

**File**: `immanuel_mcp/charts/transit_to_natal.py`
**Move**:
- `generate_transit_to_natal()` (lines 1990-2211)
- `generate_compact_transit_to_natal()` (lines 2214-2375)

**File**: `immanuel_mcp/charts/lunar_return.py`
**Create**: 🆕 New Lunar Return implementation
- `generate_lunar_return_chart()` - Full lunar return
- `generate_compact_lunar_return_chart()` - Optimized version

### Phase 8: Create Server (30 minutes)

**File**: `immanuel_mcp/server.py`

**Content**:
```python
#!/usr/bin/env python3
"""MCP Server for Immanuel Astrology Library."""

import logging
from mcp.server.fastmcp import FastMCP

# Import all chart generation functions
from .charts import natal, solar_return, lunar_return, progressed, composite, synastry, transit, transit_to_natal
from .utils import coordinates, subjects, errors

# Configure logging
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("immanuel-astrology-server")

# Register all tools (imported from chart modules)
# Each chart module will have @mcp.tool() decorated functions
```

**Pattern**: Each chart module exports its tools, server imports and registers them

### Phase 9: Update Imports (30 minutes)

**File**: `immanuel_mcp/__init__.py`

**Content**:
```python
"""Immanuel MCP Server - Modular astrology chart generation."""

from .server import mcp
from .constants import CELESTIAL_BODIES

__version__ = "0.3.0"
__all__ = ["mcp", "CELESTIAL_BODIES"]
```

## Lunar Return Implementation

### Function Signatures

**Full Version**:
```python
@mcp.tool()
def generate_lunar_return_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    return_year: int,
    return_month: int,
    timezone: str | None = None
) -> Dict[str, Any]:
    """
    Calculate lunar return chart for specified month/year.

    A lunar return occurs when the Moon returns to its natal position,
    happening approximately every 27-28 days. This is a monthly predictive
    technique showing themes and energies for the coming month.

    Args:
        date_time: Birth date and time (ISO format)
        latitude: Birth location latitude
        longitude: Birth location longitude
        return_year: Year for the lunar return (e.g., 2025)
        return_month: Month for the lunar return (1-12)
        timezone: Optional IANA timezone

    Returns:
        Full lunar return chart with all positions and aspects
    """
```

**Compact Version**:
```python
@mcp.tool()
def generate_compact_lunar_return_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    return_year: int,
    return_month: int,
    timezone: str | None = None
) -> Dict[str, Any]:
    """
    Calculate compact lunar return chart with optimized response.

    Same as generate_lunar_return_chart but with streamlined output:
    - Major objects only (Sun through Pluto, angles)
    - Major aspects only (conjunction, opposition, square, trine, sextile)
    - Optimized position format (84.9% smaller)

    Args:
        date_time: Birth date and time (ISO format)
        latitude: Birth location latitude
        longitude: Birth location longitude
        return_year: Year for the lunar return (e.g., 2025)
        return_month: Month for the lunar return (1-12)
        timezone: Optional IANA timezone

    Returns:
        Compact lunar return chart optimized for LLM processing
    """
```

### Implementation Strategy

**Reuse Solar Return Pattern**:
1. Calculate natal Moon position
2. Find date in specified month when Moon returns to that position
3. Generate chart for that moment
4. Apply optimizations (for compact version)

**Key Differences from Solar Return**:
- Track Moon's position instead of Sun
- Return happens monthly (every ~27-28 days)
- Need to find exact Moon return time within specified month

## Testing Strategy

### Unit Tests
Create tests for each module:
```
tests/
├── unit/
│   ├── test_coordinates.py         # Test parse_coordinate
│   ├── test_optimizers.py          # Test optimization functions
│   ├── test_pagination.py          # Test pagination helpers
│   └── test_interpretations.py     # Test aspect interpretations
├── integration/
│   ├── test_natal.py               # Test natal chart generation
│   ├── test_lunar_return.py        # 🆕 Test lunar return
│   └── test_transit_to_natal.py    # Test transit-to-natal
└── test_server.py                   # Test MCP server setup
```

### Integration Tests
- Test that all chart types still work after refactoring
- Test that lunar return produces valid results
- Test that compact lunar return uses optimizations

## Migration Path

### Backward Compatibility

**Option 1: Maintain Old Entry Point** (Recommended)
Keep `immanuel_server.py` as a shim that imports from new structure:
```python
#!/usr/bin/env python3
"""Backward compatibility shim for immanuel_server.py"""

from immanuel_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
```

**Option 2: Direct Migration**
Update all references to use new package structure directly

### Configuration Updates

**Claude Desktop Config** (no changes needed if using shim):
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

**Direct Package Usage** (if migrating fully):
```json
{
  "mcpServers": {
    "immanuel-astrology": {
      "command": "C:\\Users\\[USERNAME]\\.local\\bin\\uv.exe",
      "args": ["--directory", "C:\\Users\\[USERNAME]\\Documents\\MCP\\astro-mcp", "run", "python", "-m", "immanuel_mcp"]
    }
  }
}
```

## Implementation Timeline

### Day 1: Setup & Core Refactoring (4 hours)
- ✅ Phase 1: Setup structure (30 min)
- ✅ Phase 2: Extract constants (15 min)
- ✅ Phase 3: Extract utilities (30 min)
- ✅ Phase 4: Extract optimizers (45 min)
- ✅ Phase 5: Extract pagination (30 min)
- ✅ Phase 6: Extract interpretations (20 min)
- ✅ Phase 8: Create server (30 min)
- ✅ Phase 9: Update imports (30 min)

### Day 2: Chart Extraction + Lunar Return (4 hours)
- ✅ Phase 7: Extract all chart types (2 hours)
- ✅ Implement Lunar Return (1 hour)
- ✅ Test all endpoints (30 min)
- ✅ Create backward compatibility shim (30 min)

### Day 3: Testing & Documentation (2 hours)
- ✅ Write unit tests for new modules (1 hour)
- ✅ Test lunar return functionality (30 min)
- ✅ Update documentation (30 min)

## Success Criteria

✅ **All existing tests pass**
✅ **New modular structure is in place**
✅ **Lunar return charts working (full + compact)**
✅ **No breaking changes for users**
✅ **Code is more maintainable (smaller files, clear organization)**
✅ **Documentation updated**

## Risks & Mitigation

### Risk 1: Breaking Changes
**Mitigation**: Keep `immanuel_server.py` as backward compatibility shim

### Risk 2: Import Cycles
**Mitigation**: Use absolute imports, keep dependencies unidirectional

### Risk 3: Testing Overhead
**Mitigation**: Start with integration tests, add unit tests incrementally

### Risk 4: MCP Tool Registration
**Mitigation**: Ensure @mcp.tool() decorators work across modules

## File Size Comparison

| Current | After Refactoring |
|---------|-------------------|
| `immanuel_server.py`: 2,534 lines | `server.py`: ~100 lines |
| - | `charts/natal.py`: ~200 lines |
| - | `charts/lunar_return.py`: ~150 lines |
| - | `charts/solar_return.py`: ~150 lines |
| - | `charts/transit_to_natal.py`: ~250 lines |
| - | Other modules: ~50-100 lines each |

**Result**: No single file over 300 lines!

## Next Steps After Completion

1. **Add Caching Layer**: Easier with modular structure
2. **Add More Chart Types**: Just add new file in charts/
3. **Improve Testing**: Unit tests for each module
4. **Documentation**: Module-level docs for each component
5. **PyPI Package**: Easier to publish with proper package structure

---

**Created**: 2025-12-21
**Status**: Ready for implementation
**Estimated Total Time**: 10 hours
**Expected Benefit**: Massive improvement in maintainability and extensibility

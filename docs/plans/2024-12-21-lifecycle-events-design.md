# Lifecycle Events Detection System - Design Specification

**Date**: 2024-12-21
**Status**: Design Validation Phase
**Priority**: High
**Estimated Effort**: 8-12 hours
**Target**: Immanuel MCP Server v0.4.0

---

## Executive Summary

Implement a comprehensive lifecycle events detection system that automatically identifies and surfaces all significant planetary returns and life cycle transitions in transit readings. This transforms the tool from "transit calculator" to "lifecycle analysis platform."

### Key Features
- **Planetary Returns**: Detect when transiting planets return to natal positions (Saturn Return, Jupiter Return, etc.)
- **Major Life Transits**: Identify critical aspects (Uranus Opposition, Neptune Square, Pluto Square, Chiron Return)
- **Future Timeline**: Predict upcoming major events 10-20 years ahead
- **Lifecycle Context**: Show where someone is in their life journey

### Success Criteria
- ✅ Detect all planetary returns with <1° accuracy
- ✅ Identify major life transits automatically
- ✅ Response size increase <5 KB
- ✅ No regression in existing functionality
- ✅ User-friendly output for Claude Desktop

---

## 1. Architecture Overview

### 1.1 System Flow

```
generate_transit_to_natal()
         ↓
┌─────────────────────────────────┐
│  Existing: Generate Charts      │
└─────────────────────────────────┘
         ↓
┌─────────────────────────────────┐
│  Existing: Calculate Aspects    │
└─────────────────────────────────┘
         ↓
┌─────────────────────────────────┐
│  NEW: Detect Lifecycle Events   │
│  ├─ Calculate returns           │
│  ├─ Detect major transits       │
│  ├─ Build future timeline       │
│  └─ Generate summary            │
└─────────────────────────────────┘
         ↓
┌─────────────────────────────────┐
│  Build Optimized Response       │
└─────────────────────────────────┘
```

### 1.2 Module Structure

**New Module**: `immanuel_mcp/lifecycle/`

```
lifecycle/
├── __init__.py
├── returns.py          # Planetary return calculations
├── transits.py         # Major life transit detection
├── constants.py        # Orbital periods, significance levels
├── timeline.py         # Future event predictions
└── interpretations.py  # Lifecycle event descriptions
```

### 1.3 Integration Point

Modify `generate_transit_to_natal()` in `immanuel_server.py`:

```python
def generate_transit_to_natal(
    natal_date_time: str,
    natal_latitude: str,
    natal_longitude: str,
    transit_date_time: str,
    transit_latitude: str | None = None,
    transit_longitude: str | None = None,
    timezone: str | None = None,
    aspect_priority: str = "all",
    include_all_aspects: bool = False,
    include_lifecycle_events: bool = True  # NEW PARAMETER (default True)
) -> Dict[str, Any]:
```

**Key Design Decision**: Make `include_lifecycle_events=True` by default to provide maximum value without requiring users to know about this feature.

---

## 2. Core Data Structures

### 2.1 Response Structure

Add new top-level section to transit response:

```json
{
  "natal_summary": {...},
  "transit_date": "...",
  "transit_positions": {...},
  "dignities": {...},

  "lifecycle_events": {              // NEW SECTION
    "current_events": [...],
    "past_events": [...],
    "future_timeline": [...],
    "lifecycle_summary": {...}
  },

  "transit_to_natal_aspects": [...],
  "aspect_summary": {...},
  "pagination": {...}
}
```

### 2.2 Lifecycle Event Object

Unified structure for all events:

```typescript
interface LifecycleEvent {
  // Core identification
  type: string;                    // "saturn_return", "jupiter_return", etc.
  celestial_body: string;          // "Saturn", "Jupiter", etc.
  is_active: boolean;              // Currently happening?
  status: "active" | "upcoming" | "past";

  // If active
  orb?: number;                    // Degrees from exact
  orb_status?: "exact" | "tight" | "moderate" | "loose";
  natal_position?: string;         // "15°14' Scorpio"
  transit_position?: string;       // "14°46' Scorpio"
  date_of_exactness?: string;      // "2013-11-08"
  phase?: "direct" | "retrograde" | "stationary";

  // Return-specific
  return_number?: number;          // Which cycle (1st, 2nd, 3rd Saturn Return)
  orbital_period?: number;         // Years per cycle

  // If upcoming/past
  next_exact?: string;             // Date of next occurrence
  age_at_next?: number;            // Age when it happens
  years_until_next?: number;       // Time remaining

  // Metadata
  significance: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  keywords: string[];              // ["maturity", "responsibility", ...]
  interpretation?: string;         // Human-readable description
}
```

### 2.3 Future Timeline Entry

```typescript
interface TimelineEvent {
  event: string;                   // "Saturn Return #2"
  date: string;                    // "2042-06-15"
  age: number;                     // 58.4
  years_away: number;              // 28.6
  significance: "CRITICAL" | "HIGH" | "MODERATE";
}
```

---

## 3. Configuration System

### 3.1 Orbital Periods

All planetary cycles in years:

```python
ORBITAL_PERIODS = {
    "Sun": 1.0,
    "Moon": 0.0747,      # ~27.3 days
    "Mercury": 0.24,      # ~88 days
    "Venus": 0.615,       # ~225 days
    "Mars": 1.88,         # ~687 days
    "Jupiter": 11.86,
    "Saturn": 29.46,
    "Uranus": 83.75,
    "Neptune": 164.79,
    "Pluto": 247.94,
    "Chiron": 50.67,
    "North Node": 18.6,
}
```

### 3.2 Return Significance Levels

Context-aware significance based on cycle number:

```python
RETURN_SIGNIFICANCE = {
    "Saturn": {
        1: "CRITICAL",    # Age 29-30 (First Saturn Return)
        2: "CRITICAL",    # Age 58-60 (Second Saturn Return)
        3: "CRITICAL",    # Age 87-90 (Third Saturn Return)
        "default": "HIGH"
    },
    "Jupiter": {
        1: "HIGH",        # Age 12 (coming of age)
        2: "HIGH",        # Age 24 (young adult expansion)
        3: "HIGH",        # Age 36 (mature expansion)
        "default": "MODERATE"
    },
    "Uranus": {
        0.5: "CRITICAL",  # Uranus Opposition (age 41-42)
        "default": "MODERATE"
    },
    "Neptune": {
        0.5: "CRITICAL",  # Neptune Square (age 39-40)
        "default": "MODERATE"
    },
    "Pluto": {
        0.5: "CRITICAL",  # Pluto Square (age 36-37)
        "default": "MODERATE"
    }
}
```

### 3.3 Return Orb Tolerance

Different planets have different acceptable orbs:

```python
RETURN_ORB_TOLERANCE = {
    "Sun": 0.5,          # Solar return (tight)
    "Moon": 2.0,         # Lunar return (moderate)
    "Mars": 1.5,
    "Jupiter": 2.0,      # Wider orb (slower planet)
    "Saturn": 2.0,       # Wider orb (3 passages typical)
    "Uranus": 1.5,
    "Neptune": 1.5,
    "Pluto": 1.5,
    "Chiron": 2.0,
}
```

---

## 4. Core Algorithms

### 4.1 Generic Return Calculator

Single function handles all planetary returns:

```python
def calculate_planetary_return(
    planet_name: str,
    natal_chart: Chart,
    transit_chart: Chart,
    birth_datetime: datetime,
    transit_datetime: datetime
) -> Dict[str, Any]:
    """
    Universal return calculator for any celestial body.

    Returns:
        Unified lifecycle event structure
    """

    # 1. Get orbital period
    orbital_period = ORBITAL_PERIODS[planet_name]

    # 2. Calculate age
    age = (transit_datetime - birth_datetime).days / 365.25

    # 3. Get positions
    natal_position = get_planet_longitude(natal_chart, planet_name)
    transit_position = get_planet_longitude(transit_chart, planet_name)

    # 4. Calculate orb (signed, accounting for 360° wrap)
    orb = calculate_signed_orb(natal_position, transit_position)

    # 5. Determine return cycle number
    return_number = int(age / orbital_period) + 1

    # 6. Check if in return window
    orb_tolerance = RETURN_ORB_TOLERANCE.get(planet_name, 2.0)
    in_return_window = abs(orb) < orb_tolerance

    if in_return_window:
        return build_active_return(
            planet_name, return_number, orb,
            natal_position, transit_position,
            age, transit_datetime
        )
    else:
        return build_upcoming_return(
            planet_name, return_number, age,
            orbital_period, transit_datetime
        )
```

### 4.2 Orb Calculation

Accounts for 360° circular nature:

```python
def calculate_signed_orb(natal_pos: float, transit_pos: float) -> float:
    """
    Calculate signed orb between two positions.

    Returns:
        Orb in degrees (-180 to +180)
        Positive = applying, Negative = separating
    """
    diff = transit_pos - natal_pos

    # Normalize to -180 to +180
    if diff > 180:
        diff -= 360
    elif diff < -180:
        diff += 360

    return diff
```

### 4.3 Major Life Transits

Non-return events (Uranus Opposition, etc.):

```python
MAJOR_LIFE_TRANSITS = [
    {
        "name": "Uranus Opposition",
        "natal_object": "Uranus",
        "transit_object": "Uranus",
        "aspect_type": "Opposition",
        "typical_age": 41,
        "age_range": (40, 43),
        "significance": "CRITICAL",
        "keywords": ["midlife", "freedom", "awakening", "revolution"]
    },
    {
        "name": "Neptune Square",
        "natal_object": "Neptune",
        "transit_object": "Neptune",
        "aspect_type": "Square",
        "typical_age": 39,
        "age_range": (38, 41),
        "significance": "CRITICAL",
        "keywords": ["spirituality", "confusion", "faith", "illusion"]
    },
    {
        "name": "Pluto Square",
        "natal_object": "Pluto",
        "transit_object": "Pluto",
        "aspect_type": "Square",
        "typical_age": 36,
        "age_range": (35, 38),
        "significance": "CRITICAL",
        "keywords": ["transformation", "power", "crisis", "rebirth"]
    }
]
```

---

## 5. Validation & Edge Cases

### 5.1 Design Validation Checklist

**Compatibility**:
- [ ] No changes to existing function signatures (except optional param)
- [ ] New parameter has safe default (`include_lifecycle_events=True`)
- [ ] Graceful degradation if lifecycle detection fails
- [ ] Response size increase acceptable (<5 KB)

**Accuracy**:
- [ ] Orb calculations account for 360° circular nature
- [ ] Return cycle numbers accurate across all ages
- [ ] Future event predictions within ±1 day
- [ ] Phase detection (direct/retrograde/stationary) correct

**Performance**:
- [ ] Lifecycle detection adds <200ms to response time
- [ ] No redundant chart generations
- [ ] Efficient lookup structures (no O(n²) operations)

**Edge Cases**:
- [ ] Birth near year boundaries (Dec 31, Jan 1)
- [ ] Retrograde planets during returns
- [ ] Multiple simultaneous returns (rare but possible)
- [ ] Very young ages (no completed cycles yet)
- [ ] Very old ages (3rd+ Saturn Return)
- [ ] Planets near 0° or 360° (sign boundaries)

### 5.2 Known Limitations

**Out of Scope** (for v1):
- Progressed chart analysis (progressed Sun/Moon sign changes)
- Eclipse cycles
- Planetary stations (stationary points)
- Harmonic returns (half-returns, quarter-returns)
- Composite chart lifecycle events

**Intentional Exclusions**:
- Mercury/Venus returns (too frequent, not significant)
- Asteroid returns (except Chiron)
- Fixed star transits

---

## 6. User Experience Design

### 6.1 Claude Desktop Integration

**Automatic Context**:
When a user asks about transits, Claude will automatically receive lifecycle context:

```
User: "What are my transits for today?"

Claude receives:
{
  "lifecycle_events": {
    "current_events": [
      {
        "type": "saturn_return",
        "status": "active",
        "orb": 0.8,
        ...
      }
    ],
    "lifecycle_summary": {
      "current_life_stage": "Saturn Return (Age 29-30)",
      ...
    }
  }
}

Claude responds: "You're currently in your Saturn Return! This is one
of the most significant astrological transits of your life..."
```

**Natural Language Output**:
Claude can translate the structured data into user-friendly explanations:

- "You're in your Saturn Return" (not "saturn_return event detected")
- "Your next major event is Jupiter Return in 11.7 years" (not "return_number: 3")
- "You're approaching your Uranus Opposition at age 41" (not "aspect_type: opposition")

### 6.2 Default Behavior

**Opt-out, not opt-in**:
- `include_lifecycle_events=True` by default
- Users get maximum value automatically
- Can disable if only want standard aspects

**Progressive Enhancement**:
- Core transit functionality unchanged
- Lifecycle events add contextual richness
- No breaking changes to existing workflows

---

## 7. Implementation Plan

### Phase 1: Core Infrastructure (3-4 hours)

**File**: `immanuel_mcp/lifecycle/constants.py`
- [ ] ORBITAL_PERIODS
- [ ] RETURN_SIGNIFICANCE
- [ ] RETURN_KEYWORDS
- [ ] RETURN_ORB_TOLERANCE
- [ ] MAJOR_LIFE_TRANSITS

**File**: `immanuel_mcp/lifecycle/returns.py`
- [ ] calculate_signed_orb()
- [ ] calculate_planetary_return()
- [ ] get_return_significance()
- [ ] determine_orb_status()

**File**: `immanuel_mcp/lifecycle/transits.py`
- [ ] detect_major_life_transit()
- [ ] is_transit_active()

### Phase 2: Timeline & Summary (2-3 hours)

**File**: `immanuel_mcp/lifecycle/timeline.py`
- [ ] build_future_timeline()
- [ ] predict_next_event()
- [ ] sort_timeline_events()

**File**: `immanuel_mcp/lifecycle/lifecycle.py`
- [ ] detect_lifecycle_events() (master function)
- [ ] build_lifecycle_summary()
- [ ] determine_life_stage()

### Phase 3: Integration (1-2 hours)

**File**: `immanuel_server.py`
- [ ] Add `include_lifecycle_events` parameter
- [ ] Import lifecycle detection
- [ ] Add lifecycle_events to response
- [ ] Error handling / graceful degradation

### Phase 4: Testing (2-3 hours)

**Test Cases**:
- [ ] Saturn Return (Jan 11, 1984 → Nov 11, 2013)
- [ ] Jupiter Return detection
- [ ] No active returns (age 22)
- [ ] Multiple simultaneous returns
- [ ] Future timeline accuracy
- [ ] Edge cases (retrograde, sign boundaries)

---

## 8. Risk Assessment

### High Risk
- ❌ **Breaking existing functionality**: Mitigated by optional parameter with safe default
- ❌ **Response size bloat**: Mitigated by efficient data structures (~3-5 KB addition)
- ❌ **Performance regression**: Mitigated by single-pass calculations

### Medium Risk
- ⚠️ **Astronomical calculation errors**: Mitigated by comprehensive testing against known dates
- ⚠️ **Complex edge cases**: Mitigated by defensive programming and error handling

### Low Risk
- ✅ **User confusion**: Clear documentation and natural language output
- ✅ **Maintenance burden**: Well-structured, modular code

---

## 9. Success Metrics

### Functional
- ✅ Saturn Return detected with <1° orb accuracy
- ✅ All planetary returns calculated correctly
- ✅ Major life transits identified automatically
- ✅ Future timeline predictions accurate within ±3 days

### Performance
- ✅ Response time increase <200ms
- ✅ Response size increase <5 KB
- ✅ No memory leaks or resource issues

### Quality
- ✅ 100% test coverage for core functions
- ✅ All edge cases handled gracefully
- ✅ No regressions in existing tests

### User Experience
- ✅ Natural language output in Claude Desktop
- ✅ Automatic context provided without user request
- ✅ Zero configuration required for basic use

---

## 10. Documentation Updates Required

### README.md
- Add lifecycle events to features list
- Update `generate_transit_to_natal` documentation
- Add example showing lifecycle context

### CLAUDE.md
- Document `include_lifecycle_events` parameter
- Add lifecycle events to data flow diagram
- Update response structure examples

### New Documentation
- `docs/LIFECYCLE_EVENTS.md` - Complete lifecycle system guide
- `docs/examples/SATURN_RETURN_EXAMPLE.md` - Detailed example

---

## Appendix A: Example Response

**Input**:
- Birth: Jan 11, 1984, 18:45 GMT
- Transit: Nov 11, 2013, 00:50 CET

**Output** (lifecycle_events section only):

```json
{
  "lifecycle_events": {
    "current_events": [
      {
        "type": "saturn_return",
        "celestial_body": "Saturn",
        "is_active": true,
        "status": "active",
        "return_number": 1,
        "orb": 0.78,
        "orb_status": "exact",
        "natal_position": "15°14'27\" Scorpio",
        "transit_position": "14°36'15\" Scorpio",
        "age": 29.84,
        "date_of_exactness": "2013-11-08",
        "phase": "direct",
        "orbital_period": 29.46,
        "significance": "CRITICAL",
        "keywords": ["maturity", "responsibility", "karma", "restructuring"],
        "interpretation": "First Saturn Return exact at age 29.8. Peak karmic reckoning and life restructuring period."
      }
    ],

    "past_events": [],

    "future_timeline": [
      {
        "event": "Jupiter Return #3",
        "date": "2020-08-15",
        "age": 36.6,
        "years_away": 6.76,
        "significance": "HIGH"
      },
      {
        "event": "Pluto Square",
        "date": "2021-06-10",
        "age": 37.4,
        "years_away": 7.58,
        "significance": "CRITICAL"
      },
      {
        "event": "Neptune Square",
        "date": "2024-11-15",
        "age": 40.9,
        "years_away": 11.01,
        "significance": "CRITICAL"
      },
      {
        "event": "Uranus Opposition",
        "date": "2026-03-20",
        "age": 42.2,
        "years_away": 12.36,
        "significance": "CRITICAL"
      }
    ],

    "lifecycle_summary": {
      "current_age": 29.84,
      "current_life_stage": "Saturn Return (Age 29-30)",
      "major_events_next_5_years": 0,
      "major_events_next_10_years": 2,
      "next_major_event": "Jupiter Return #3 in 6.8 years",
      "next_critical_event": "Pluto Square in 7.6 years"
    }
  }
}
```

---

## Design Status: READY FOR VALIDATION

**Next Steps**:
1. ✅ Design documented
2. ⏳ **Validate with team** ← YOU ARE HERE
3. ⏳ Create git worktree for implementation
4. ⏳ Implement according to plan
5. ⏳ Test comprehensively
6. ⏳ Update documentation
7. ⏳ Commit and deploy

**Questions for Validation**:
1. Does the data structure fit well with the existing optimized response format?
2. Should `include_lifecycle_events` default to `True` or `False`?
3. Are there any missing edge cases we should handle?
4. Should we implement all planets or start with major ones only (Saturn, Jupiter, Uranus, Neptune, Pluto, Chiron)?

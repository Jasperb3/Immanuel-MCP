"""
Lifecycle Events Configuration Constants

All orbital periods, significance levels, keywords, and transit definitions.
"""

from typing import Dict, Any, List

# ============================================================================
# Orbital Periods (in years)
# ============================================================================

ORBITAL_PERIODS: Dict[str, float] = {
    "Sun": 1.0,
    "Moon": 0.0747,       # ~27.3 days
    "Mercury": 0.24,       # ~88 days (not typically used for returns)
    "Venus": 0.615,        # ~225 days (not typically used for returns)
    "Mars": 1.88,          # ~687 days
    "Jupiter": 11.86,
    "Saturn": 29.46,
    "Uranus": 83.75,
    "Neptune": 164.79,
    "Pluto": 247.94,
    "Chiron": 50.67,
    "North Node": 18.6,    # Nodal cycle
    "South Node": 18.6,
}

# ============================================================================
# Return Significance Levels
# ============================================================================
# Context-aware significance based on cycle number and life stage

RETURN_SIGNIFICANCE: Dict[str, Dict[Any, str]] = {
    "Sun": {
        "default": "MODERATE"  # Solar return - yearly theme
    },
    "Moon": {
        "default": "LOW"  # Monthly check-in (too frequent for major significance)
    },
    "Mercury": {
        "default": "LOW"  # Too frequent to track
    },
    "Venus": {
        "default": "LOW"  # ~8 months, not major
    },
    "Mars": {
        "default": "MODERATE"  # ~2 year cycle
    },
    "Jupiter": {
        1: "HIGH",         # First Jupiter Return - age 12 (coming of age)
        2: "HIGH",         # Second - age 24 (young adult expansion)
        3: "HIGH",         # Third - age 36 (mature expansion)
        4: "HIGH",         # Fourth - age 48
        "default": "MODERATE"
    },
    "Saturn": {
        1: "CRITICAL",     # First Saturn Return - age 29-30
        2: "CRITICAL",     # Second - age 58-60
        3: "CRITICAL",     # Third - age 87-90 (if reached)
        "default": "HIGH"
    },
    "Uranus": {
        0.5: "CRITICAL",   # Uranus Opposition - age 41-42 (midlife)
        1: "CRITICAL",     # Uranus Return - age 84 (rarely experienced)
        "default": "MODERATE"
    },
    "Neptune": {
        0.5: "CRITICAL",   # Neptune Square - age 39-40
        "default": "MODERATE"
    },
    "Pluto": {
        0.5: "CRITICAL",   # Pluto Square - age 36-37
        1: "CRITICAL",     # Pluto Return - age 247 (impossible in human lifespan)
        "default": "MODERATE"
    },
    "Chiron": {
        0.5: "HIGH",       # Chiron Opposition - age 25-26 (wounded healer awakening)
        1: "HIGH",         # Chiron Return - age 50+ (healing mastery)
        "default": "MODERATE"
    },
    "North Node": {
        1: "HIGH",         # First Nodal Return - age 18-19
        2: "HIGH",         # Second - age 37-38
        3: "HIGH",         # Third - age 56-57
        "default": "MODERATE"
    }
}

# ============================================================================
# Return Keywords
# ============================================================================
# Archetypal themes for each celestial body's return

RETURN_KEYWORDS: Dict[str, List[str]] = {
    "Sun": ["identity", "vitality", "new year", "birthday", "self-expression"],
    "Moon": ["emotions", "instincts", "cycles", "home", "nurturing"],
    "Mercury": ["communication", "learning", "connections", "commerce"],
    "Venus": ["love", "values", "beauty", "harmony", "pleasure"],
    "Mars": ["action", "energy", "desire", "courage", "assertion"],
    "Jupiter": ["luck", "expansion", "belief", "wisdom", "opportunity", "growth"],
    "Saturn": ["maturity", "responsibility", "karma", "restructuring", "mastery", "limits"],
    "Uranus": ["freedom", "rebellion", "innovation", "awakening", "revolution", "change"],
    "Neptune": ["spirituality", "dreams", "illusion", "surrender", "transcendence", "compassion"],
    "Pluto": ["transformation", "power", "death/rebirth", "depths", "regeneration", "intensity"],
    "Chiron": ["healing", "wounds", "wisdom", "wholeness", "teacher", "wounded healer"],
    "North Node": ["soul growth", "destiny", "evolution", "purpose", "future direction"],
    "South Node": ["past patterns", "release", "karma", "comfort zone", "letting go"]
}

# ============================================================================
# Return Orb Tolerance
# ============================================================================
# Maximum orb (in degrees) to consider a return "active"

RETURN_ORB_TOLERANCE: Dict[str, float] = {
    "Sun": 0.5,           # Solar return: very tight (exact day)
    "Moon": 2.0,          # Lunar return: moderate
    "Mercury": 1.0,
    "Venus": 1.0,
    "Mars": 1.0,          # Phase 2 requirement: ±1° orb
    "Jupiter": 2.0,       # Wider orb (slower planet, longer influence)
    "Saturn": 1.5,        # tightened to match lifecycle spec
    "Uranus": 1.5,
    "Neptune": 1.5,
    "Pluto": 1.5,
    "Chiron": 1.0,        # tighter precision for healing cycle
    "North Node": 1.0,    # nodal return ±1°
    "South Node": 1.0,
}

# ============================================================================
# Major Life Transits (Non-Returns)
# ============================================================================
# Significant astrological events that aren't returns to natal position

MAJOR_LIFE_TRANSITS: List[Dict[str, Any]] = [
    {
        "name": "Uranus Opposition",
        "natal_object": "Uranus",
        "transit_object": "Uranus",
        "aspect_type": "Opposition",
        "typical_age": 41,
        "age_range": (40, 43),
        "significance": "CRITICAL",
        "keywords": ["midlife", "freedom", "awakening", "revolution", "liberation", "authenticity"],
        "description": "Uranus opposes natal Uranus. The classic 'midlife crisis' transit. "
                      "A powerful awakening to personal freedom and authentic self-expression."
    },
    {
        "name": "Neptune Square",
        "natal_object": "Neptune",
        "transit_object": "Neptune",
        "aspect_type": "Square",
        "typical_age": 39,
        "age_range": (38, 41),
        "significance": "CRITICAL",
        "keywords": ["spirituality", "confusion", "faith", "illusion", "surrender", "compassion"],
        "description": "Neptune squares natal Neptune. A spiritual crisis or awakening. "
                      "Confrontation with illusion vs reality, requiring faith and surrender."
    },
    {
        "name": "Pluto Square",
        "natal_object": "Pluto",
        "transit_object": "Pluto",
        "aspect_type": "Square",
        "typical_age": 36,
        "age_range": (35, 38),
        "significance": "CRITICAL",
        "keywords": ["transformation", "power", "crisis", "rebirth", "intensity", "depth"],
        "description": "Pluto squares natal Pluto. Deep personal transformation and power recalibration. "
                      "Often involves crisis that leads to profound rebirth."
    },
    {
        "name": "Chiron Opposition",
        "natal_object": "Chiron",
        "transit_object": "Chiron",
        "aspect_type": "Opposition",
        "typical_age": 25,
        "age_range": (24, 27),
        "significance": "HIGH",
        "keywords": ["healing", "vulnerability", "medicine person", "wisdom", "teacher", "wounds"],
        "description": "Chiron opposes natal Chiron. First major wound healing crisis. "
                      "Potential emergence as wounded healer and teacher."
    },
]

# ============================================================================
# Lifecycle Stage Definitions
# ============================================================================
# Human-readable life stages based on age and major transits

LIFECYCLE_STAGES: Dict[int, tuple] = {
    0: ("Infancy", "Building foundations", 0, 2),
    1: ("Early Childhood", "Developing self", 2, 7),
    2: ("Late Childhood", "Learning and growth", 7, 12),
    3: ("First Jupiter Return", "Expansion and discovery", 12, 13),
    4: ("Adolescence", "Identity formation", 13, 18),
    5: ("Early Adulthood", "Independence and exploration", 18, 25),
    6: ("Chiron Opposition", "First wound healing", 25, 27),
    7: ("Late Twenties", "Career and relationships", 27, 29),
    8: ("Saturn Return", "Karmic maturation", 29, 31),
    9: ("Post-Saturn Return", "Authentic path", 31, 36),
    10: ("Pluto Square", "Power and transformation", 36, 38),
    11: ("Neptune Square", "Spiritual awakening", 38, 41),
    12: ("Uranus Opposition", "Midlife awakening", 41, 43),
    13: ("Mature Adult", "Wisdom integration", 43, 50),
    14: ("Chiron Return", "Wounded healer emerges", 50, 52),
    15: ("Late Adulthood", "Mastery and teaching", 52, 58),
    16: ("Second Saturn Return", "Elder wisdom", 58, 60),
    17: ("Elder Years", "Legacy and completion", 60, 120),
}

# ============================================================================
# Tracked Planets for Returns
# ============================================================================
# Planets we calculate returns for (excludes too-frequent returns)

TRACKED_RETURN_PLANETS: List[str] = [
    "Mars",      # 2-year action cycle
    "Jupiter",
    "Saturn",
    "Chiron",
    "North Node",
    "Uranus",
    "Neptune",
    "Pluto",
]

# Optional: lower priority but available for future expansion
OPTIONAL_RETURN_PLANETS: List[str] = [
    "Sun",        # Solar return (every year)
    "Mercury",
    "Venus",
    "South Node"
]

# ============================================================================
# Return Interpretations (used for lifecycle event descriptions)
# ============================================================================

RETURN_INTERPRETATIONS: Dict[str, Dict[Any, str]] = {
    "Saturn": {
        1: "First major Saturn Return – maturation, accountability, and restructuring.",
        2: "Second Saturn Return – elder mastery, legacy review, and completion of long cycles.",
        3: "Third Saturn Return – wisdom keeper threshold and preparation for spiritual legacy.",
        "default": "Saturnian restructuring phase demanding responsibility and integrity."
    },
    "Chiron": {
        1: "Chiron Return – integration of the wounded healer archetype at midlife.",
        0.5: "Chiron Opposition – awakening to core wounds and the medicine you carry.",
        "default": "Chiron cycle emphasizing healing, wholeness, and mentorship."
    },
    "Jupiter": {
        1: "First Jupiter Return – rite of passage expanding belief systems and opportunities.",
        2: "Second Jupiter Return – new growth cycle in adulthood and renewed optimism.",
        "default": "Jupiter expansion phase bringing fresh wisdom, abundance, and faith."
    },
    "Mars": {
        "default": "Mars Return – reboot of motivation, courage, and how you assert your will."
    },
    "North Node": {
        1: "First Nodal Return – alignment with soul mission and destiny pivot.",
        2: "Second Nodal Return – recalibration of karmic path and life direction.",
        "default": "Nodal Return – reminders to lean into your evolutionary edge."
    },
    "Uranus": {
        0.5: "Uranus Opposition – midlife awakening demanding authentic freedom.",
        1: "Uranus Return – revolutionary reinvention of identity and destiny.",
        "default": "Uranian cycle prompting liberation and innovation."
    },
    "Neptune": {
        0.5: "Neptune Square – fog vs. faith initiation reshaping spiritual compass.",
        "default": "Neptunian cycle encouraging surrender, compassion, and imagination."
    },
    "Pluto": {
        0.5: "Pluto Square – deep alchemical transformation of power dynamics.",
        "default": "Plutonian metamorphosis requiring total honesty and regeneration."
    }
}

# Specialized interpretations for progressed Moon tracking
PROGRESSED_MOON_INTERPRETATION = (
    "Progressed Moon Return – emotional reset that reboots intuition, needs, and inner rhythm."
)
PROGRESSED_MOON_KEYWORDS = [
    "emotional reset",
    "intuition",
    "inner rhythm",
    "soul nourishment",
    "sensitivity"
]

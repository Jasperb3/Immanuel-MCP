"""
Lifecycle Events Detection System

This module provides comprehensive detection of planetary returns and major life
transits, helping users understand where they are in their astrological life cycle.

Main components:
- returns.py: Planetary return calculations (Saturn Return, Jupiter Return, etc.)
- transits.py: Major life transit detection (Uranus Opposition, Neptune Square, etc.)
- timeline.py: Future event predictions
- lifecycle.py: Master detection function that orchestrates all calculations
- constants.py: Orbital periods, significance levels, and configurations
"""

from .lifecycle import detect_lifecycle_events, format_lifecycle_event_feed
from .progressed import detect_progressed_moon_return
from .constants import (
    ORBITAL_PERIODS,
    RETURN_SIGNIFICANCE,
    RETURN_KEYWORDS,
    RETURN_ORB_TOLERANCE,
    RETURN_INTERPRETATIONS,
    PROGRESSED_MOON_INTERPRETATION,
    PROGRESSED_MOON_KEYWORDS,
    MAJOR_LIFE_TRANSITS
)

__all__ = [
    'detect_lifecycle_events',
    'detect_progressed_moon_return',
    'format_lifecycle_event_feed',
    'ORBITAL_PERIODS',
    'RETURN_SIGNIFICANCE',
    'RETURN_KEYWORDS',
    'RETURN_ORB_TOLERANCE',
    'RETURN_INTERPRETATIONS',
    'PROGRESSED_MOON_INTERPRETATION',
    'PROGRESSED_MOON_KEYWORDS',
    'MAJOR_LIFE_TRANSITS'
]

__version__ = '0.1.0'

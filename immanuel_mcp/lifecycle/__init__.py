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

from .lifecycle import detect_lifecycle_events
from .constants import (
    ORBITAL_PERIODS,
    RETURN_SIGNIFICANCE,
    RETURN_KEYWORDS,
    RETURN_ORB_TOLERANCE,
    MAJOR_LIFE_TRANSITS
)

__all__ = [
    'detect_lifecycle_events',
    'ORBITAL_PERIODS',
    'RETURN_SIGNIFICANCE',
    'RETURN_KEYWORDS',
    'RETURN_ORB_TOLERANCE',
    'MAJOR_LIFE_TRANSITS'
]

__version__ = '0.1.0'

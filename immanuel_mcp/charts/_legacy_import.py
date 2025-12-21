"""
Temporary legacy imports from original immanuel_server.py

This allows the modular structure to work while we incrementally migrate chart functions.
TODO: Remove this file once all functions are migrated to their respective modules.
"""

import sys
import os

# Add parent directory to path to import original server
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import all chart generation functions from original server
try:
    from immanuel_server import (
        # Natal
        generate_natal_chart,
        generate_compact_natal_chart,
        get_chart_summary,
        get_planetary_positions,

        # Solar Return
        generate_solar_return_chart,
        generate_compact_solar_return_chart,

        # Progressed
        generate_progressed_chart,
        generate_compact_progressed_chart,

        # Composite
        generate_composite_chart,
        generate_compact_composite_chart,

        # Synastry
        generate_synastry_aspects,
        generate_compact_synastry_aspects,

        # Transit
        generate_transit_chart,
        generate_compact_transit_chart,

        # Transit to Natal
        generate_transit_to_natal,
        generate_compact_transit_to_natal,

        # Configuration
        configure_immanuel_settings,
        list_available_settings,
    )
except ImportError as e:
    print(f"Warning: Could not import from immanuel_server: {e}")
    # Define stub functions that return errors
    def _stub(*args, **kwargs):
        return {"error": True, "message": "Function not yet migrated to modular structure"}

    generate_natal_chart = _stub
    generate_compact_natal_chart = _stub
    get_chart_summary = _stub
    get_planetary_positions = _stub
    generate_solar_return_chart = _stub
    generate_compact_solar_return_chart = _stub
    generate_progressed_chart = _stub
    generate_compact_progressed_chart = _stub
    generate_composite_chart = _stub
    generate_compact_composite_chart = _stub
    generate_synastry_aspects = _stub
    generate_compact_synastry_aspects = _stub
    generate_transit_chart = _stub
    generate_compact_transit_chart = _stub
    generate_transit_to_natal = _stub
    generate_compact_transit_to_natal = _stub
    configure_immanuel_settings = _stub
    list_available_settings = _stub

__all__ = [
    'generate_natal_chart',
    'generate_compact_natal_chart',
    'get_chart_summary',
    'get_planetary_positions',
    'generate_solar_return_chart',
    'generate_compact_solar_return_chart',
    'generate_progressed_chart',
    'generate_compact_progressed_chart',
    'generate_composite_chart',
    'generate_compact_composite_chart',
    'generate_synastry_aspects',
    'generate_compact_synastry_aspects',
    'generate_transit_chart',
    'generate_compact_transit_chart',
    'generate_transit_to_natal',
    'generate_compact_transit_to_natal',
    'configure_immanuel_settings',
    'list_available_settings',
]

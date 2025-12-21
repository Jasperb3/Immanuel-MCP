# Immanuel MCP Server Updates

## Version 1.1.0 - Feature Update

### New Feature: Compact Natal Chart

To provide a more streamlined and focused user experience, we have introduced a new tool for generating a summarized version of a natal chart.

-   **New Tool:** A `generate_compact_natal_chart` tool has been added to `immanuel_server.py`. This tool is designed to return only the most essential astrological information, making the output significantly smaller and easier to parse for quick interpretations.

-   **Optional Functionality:** The original `generate_natal_chart` tool remains unchanged, providing the full, detailed chart data. Users can now choose between the full chart and the new compact version based on their needs.

### Changes in Compact Chart Output

The compact chart includes:
-   **Major Celestial Objects:** Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Ascendant, and Midheaven.
-   **Essential Object Data:** For each object, the output includes its name, sign, degree, and house placement.
-   **Major Aspects:** Conjunction, Opposition, Square, Trine, and Sextile.
-   **House Cusps:** The full list of house cusps and their positions is retained.

The following data is **excluded** from the compact output to ensure brevity:
-   Minor objects and asteroids (e.g., Chiron, Ceres).
-   Detailed properties like `weightings`, `chart_shape`, `diurnal`, and `moon_phase`.

### Implementation Details

-   A new `compact_serializer.py` file was created to handle the custom JSON serialization for the compact chart, providing fine-grained control over the output.
-   Unit tests were added to `test_immanuel_server.py` to validate the functionality and structure of the new compact chart tool.

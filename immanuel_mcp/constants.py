"""Shared constant mappings."""

from immanuel.const import chart as chart_const

CELESTIAL_BODIES = {
    # Angles
    3000001: "Asc",
    3000002: "Desc",
    3000003: "MC",
    3000004: "IC",

    # Planets
    4000001: "Sun",
    4000002: "Moon",
    4000003: "Mercury",
    4000004: "Venus",
    4000006: "Mars",
    4000007: "Jupiter",
    4000008: "Saturn",
    4000009: "Uranus",
    4000010: "Neptune",
    4000011: "Pluto",

    # Minor bodies
    5000001: "Chiron",

    # Points
    6000003: "North Node",
    6000004: "South Node",
    6000005: "Vertex",
    6000007: "Lilith",
    6000010: "Part of Fortune"
}


# Planet names to Immanuel chart constants. Shared by the lifecycle detector
# and the forecast calendars, so it lives here rather than inside either.
PLANET_CONSTANTS = {
    "Sun": chart_const.SUN,
    "Moon": chart_const.MOON,
    "Mercury": chart_const.MERCURY,
    "Venus": chart_const.VENUS,
    "Mars": chart_const.MARS,
    "Jupiter": chart_const.JUPITER,
    "Saturn": chart_const.SATURN,
    "Uranus": chart_const.URANUS,
    "Neptune": chart_const.NEPTUNE,
    "Pluto": chart_const.PLUTO,
    "Chiron": chart_const.CHIRON,
    "North Node": chart_const.NORTH_NODE,
    "South Node": chart_const.SOUTH_NODE,
}

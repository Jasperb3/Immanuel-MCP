"""Shared constant mappings."""

from immanuel.const import chart as chart_const

# Keys of a ToJSON-serialized chart. Do not use immanuel.const.data.OBJECTS
# etc. for these: in 1.6 those became ints (12/14/13) while the serialized
# keys stayed strings, so lookups with them silently miss.
KEY_OBJECTS = "objects"
KEY_HOUSES = "houses"
KEY_ASPECTS = "aspects"

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
    # The true nodes: they are what immanuel's default object list contains
    # and what CELESTIAL_BODIES labels "North Node"/"South Node". The mean
    # nodes are absent from charts, so looking them up returned None.
    "North Node": chart_const.TRUE_NORTH_NODE,
    "South Node": chart_const.TRUE_SOUTH_NODE,
}

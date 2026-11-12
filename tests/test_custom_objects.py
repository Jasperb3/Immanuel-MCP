"""A custom session object list: compact output keeps added objects, and
lifecycle doesn't lose bodies the list leaves out."""

import pytest

import immanuel_server
from immanuel_mcp.utils.settings import reset_global_settings

BIRTH = dict(date_time="1985-06-21 14:30:00", latitude="51.5", longitude="-0.13", timezone="Europe/London")
OBJECTS = "SUN,MOON,MERCURY,VENUS,MARS,JUPITER,SATURN,CERES,ASC,MC"


@pytest.fixture(autouse=True)
def clean_session():
    reset_global_settings()
    yield
    reset_global_settings()


def _names(result):
    return {o["name"] for o in result["objects"].values()}


def test_added_object_appears_in_compact_output():
    assert immanuel_server.configure_immanuel_settings("objects", OBJECTS)["status"] == "success"
    result = immanuel_server.generate_compact_natal_chart(**BIRTH)
    assert result["status"] == "success", result
    assert "Ceres" in _names(result)
    assert "Uranus" not in _names(result)  # left out of the list, so not in the chart


def test_default_objects_compact_output_unchanged():
    names = _names(immanuel_server.generate_compact_natal_chart(**BIRTH))
    assert "Ceres" not in names and "Chiron" not in names
    assert {"Sun", "Pluto", "Asc", "MC"} <= names


def test_lifecycle_keeps_bodies_the_list_leaves_out():
    immanuel_server.configure_immanuel_settings("objects", OBJECTS)
    custom = immanuel_server.generate_compact_natal_chart(**BIRTH)
    reset_global_settings()
    default = immanuel_server.generate_compact_natal_chart(**BIRTH)

    def events(result):
        return {(e["event_type"], e.get("exact_date")) for e in result["lifecycle_events"]}

    assert events(custom) == events(default)
    planets = {e.get("natal_object") or e.get("planet") for e in custom["lifecycle_events"]}
    assert {"Uranus", "Neptune", "Pluto", "Chiron"} & planets
    assert all(e.get("prediction_basis", "ephemeris") == "ephemeris" for e in custom["lifecycle_events"])


def test_listed_default_object_appears_in_compact_output():
    # Chiron is in immanuel's default list, so "added to the defaults" missed it.
    immanuel_server.configure_immanuel_settings("objects", OBJECTS + ",CHIRON,TRUE_NORTH_NODE")
    names = _names(immanuel_server.generate_compact_natal_chart(**BIRTH))
    assert {"Chiron", "Ceres", "True North Node"} <= names

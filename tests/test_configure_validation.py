#!/usr/bin/env python3
"""
Regression tests for configure_immanuel_settings input handling and the
lifecycle North Node return. All of these reproduced on immanuel 1.5.4 too:

- aspect names were looked up on immanuel.const.chart, where they don't
  exist, so 'CONJUNCTION,TRINE' failed with int('CONJUNCTION')
- object names were looked up on immanuel.const.data, so 'SUN,MOON' were
  stored as strings (fixed-star names) and the next chart call failed
- 'angles' was accepted but is not an immanuel setting (a silent no-op)
- any '*_orb' key was setattr'd onto the config, real attribute or not
- the North Node return looked up the mean node, which charts don't contain
"""

from datetime import datetime

import pytest
from immanuel import charts
from immanuel.const import calc as calc_const
from immanuel.const import chart as chart_const

import immanuel_server
from immanuel_mcp.charts.ingresses import get_sign_ingresses
from immanuel_mcp.lifecycle.returns import calculate_planetary_return
from immanuel_mcp.utils.settings import get_session_config, reset_global_settings
from immanuel_mcp.utils.subjects import create_subject

BIRTH = ("1990-01-15 14:30:00", "32.71", "-117.15")
TZ = "America/Los_Angeles"
configure = immanuel_server.configure_immanuel_settings


@pytest.fixture(autouse=True)
def clean_session():
    reset_global_settings()
    yield
    reset_global_settings()


def _chart_still_works():
    result = immanuel_server.generate_compact_natal_chart(*BIRTH, timezone=TZ)
    assert result["status"] == "success", result.get("message")


# --- aspects ----------------------------------------------------------------

def test_aspects_accept_names():
    result = configure("aspects", "CONJUNCTION, trine")
    assert result["status"] == "success", result.get("message")
    assert get_session_config().aspects == [calc_const.CONJUNCTION, calc_const.TRINE]
    _chart_still_works()


def test_aspects_accept_numeric_angles():
    result = configure("aspects", "120,54.3")
    assert result["status"] == "success", result.get("message")
    assert get_session_config().aspects == [120.0, 54.3]
    _chart_still_works()


@pytest.mark.parametrize("value", ["TRINEE", "200", "-5"])
def test_aspects_reject_unknowns_and_list_valid_names(value):
    before = list(get_session_config().aspects)
    result = configure("aspects", value)
    assert result["error"] is True
    assert "TRINE" in result["message"] and "QUINCUNX" in result["message"]
    assert get_session_config().aspects == before


# --- objects ----------------------------------------------------------------

def test_objects_accept_constant_names_and_codes():
    result = configure("objects", "SUN, moon, CERES, 4000006, true_north_node")
    assert result["status"] == "success", result.get("message")
    assert get_session_config().objects == [
        chart_const.SUN, chart_const.MOON, chart_const.CERES,
        chart_const.MARS, chart_const.TRUE_NORTH_NODE]
    _chart_still_works()


@pytest.mark.parametrize("value", ["SUN,Notastar", "SUN,99", "SUN,5000433"])
def test_objects_reject_what_the_ephemeris_cannot_resolve(value):
    before = list(get_session_config().objects)
    result = configure("objects", value)
    assert result["error"] is True
    assert "fixed star" in result["message"]
    assert get_session_config().objects == before
    _chart_still_works()


# --- angles / *_orb ---------------------------------------------------------

def test_angles_is_not_a_setting():
    result = configure("angles", "ASC")
    assert result["status"] == "warning"
    assert result["applied"] is False
    assert not hasattr(get_session_config(), "angles")


def test_real_orb_settings_are_set_as_floats():
    result = configure("exact_orb", "0.5")
    assert result["status"] == "success", result.get("message")
    assert get_session_config().exact_orb == 0.5


def test_unknown_orb_settings_are_rejected():
    result = configure("made_up_orb", "3")
    assert result["status"] == "warning"
    assert result["applied"] is False
    assert not hasattr(get_session_config(), "made_up_orb")


# --- lifecycle North Node ---------------------------------------------------

def test_north_node_return_reads_the_node_the_chart_contains():
    natal = charts.Natal(create_subject(*BIRTH, TZ))
    # ~18.7 years on: the first nodal return for this chart
    transit = charts.Natal(create_subject("2008-10-15 12:00:00", "32.71", "-117.15", TZ))
    result = calculate_planetary_return(
        "North Node", natal, transit,
        datetime(1990, 1, 15, 14, 30), datetime(2008, 10, 15, 12))
    assert result is not None
    # The perfection date comes from the ephemeris search, which used to
    # raise KeyError for the nodes (get_planet knows only planets).
    assert result["exact_dates"], "nodal return has no ephemeris-searched dates"


@pytest.mark.parametrize("node", ["North Node", "South Node"])
def test_node_ingresses_are_searchable(node):
    result = get_sign_ingresses("2026-11-08 00:00:00", planets=[node], count=2,
                                timezone="UTC")
    assert result["status"] == "success", result.get("message")
    assert len(result["ingresses"][node]) == 2


# --- review follow-ups --------------------------------------------------------

def test_compact_major_aspects_survive_a_non_english_locale():
    english = immanuel_server.generate_compact_natal_chart(*BIRTH, timezone=TZ)["aspects"]
    configure("locale", "de_DE")
    german = immanuel_server.generate_compact_natal_chart(*BIRTH, timezone=TZ)["aspects"]
    assert len(german) == len(english) > 5


@pytest.mark.parametrize("value", ["fr_FR", "de-DE", "xx"])
def test_unknown_locales_are_rejected(value):
    result = configure("locale", value)
    assert result["error"] is True
    assert "pt_BR" in result["message"]
    assert get_session_config().locale is None


def test_every_listed_aspect_name_is_accepted_back():
    listed = immanuel_server.list_available_settings()["settings"]["aspects"]["available"]
    for name in listed:
        result = configure("aspects", name)
        assert result["status"] == "success", (name, result.get("message"))


@pytest.mark.parametrize("value", ["Semi-sextile", "semisextile", "SEMISEXTILE"])
def test_aspect_spellings_resolve(value):
    assert configure("aspects", value)["status"] == "success"
    assert get_session_config().aspects == [calc_const.SEMISEXTILE]


def test_object_codes_that_the_ephemeris_resolves_are_accepted():
    # 1 is asteroid (1) Ceres by its official number, read from the bundled files
    result = configure("objects", "SUN,1")
    assert result["status"] == "success", result.get("message")
    assert get_session_config().objects == [chart_const.SUN, 1]
    _chart_still_works()


@pytest.mark.parametrize("key,value", [
    ("default_orb", "5"), ("exact_orb", "0.1"), ("chart_shape_orb", "9"),
    ("orb_calculation", "MAX"), ("objects", "SUN,MOON,MERCURY,VENUS,MARS,JUPITER,SATURN,"
     "URANUS,NEPTUNE,PLUTO,CERES,PALLAS,JUNO,VESTA,ASC,DESC,MC,IC,VERTEX,PART_OF_FORTUNE"),
    ("aspects", "0,180,90,120,60,72"),
])
def test_reset_reports_every_configurable_change(key, value):
    assert configure(key, value)["status"] == "success"
    result = immanuel_server.reset_immanuel_settings()
    assert key in result["changed"], result["changed"]


def test_node_ingresses_are_not_flagged_as_re_entries_for_moving_backwards():
    events = get_sign_ingresses("2025-01-01 00:00:00", planets=["North Node"], count=3,
                                timezone="UTC")["ingresses"]["North Node"]
    assert [e["retrograde_re_entry"] for e in events] == [False, False, False]

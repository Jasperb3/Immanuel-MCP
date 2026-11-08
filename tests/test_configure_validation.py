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


@pytest.mark.parametrize("value", ["SUN,Notastar", "SUN,99"])
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

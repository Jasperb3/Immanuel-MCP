"""Composite houses stay in order when the two charts' cusps are far apart.

immanuel midpoints each cusp on its own shorter arc, so when a pair of cusps
is nearly 180 degrees apart some composite cusps land on the far side of the
circle (London 1985 + Svalbard 1990), and the averaged house sizes stop
matching the cusps, which put the MC in house 9.
"""

import itertools

import pytest
from immanuel import charts
from immanuel.const import chart

from immanuel_mcp.compat.composite import CoherentComposite
from immanuel_mcp.utils.settings import new_config
from immanuel_mcp.utils.subjects import create_subject
from immanuel_server import generate_compact_composite_chart, generate_composite_chart

LONDON = ("51.5", "-0.13")
SVALBARD = ("78.22", "15.63")
SYDNEY = ("-33.87", "151.2")
HOURS = range(0, 24, 3)


def _cusps(result):
    houses = sorted(result["houses"].values(), key=lambda h: h["number"])
    return [h["longitude"]["raw"] for h in houses]


def _in_order(cusps):
    return sum((cusps[(i + 1) % 12] - cusps[i]) % 360 for i in range(12)) < 361


def _object(result, name):
    return next(o for o in result["objects"].values() if o["name"] == name)


def _composite(native_hour, partner_hour, partner=SVALBARD, **kwargs):
    return generate_composite_chart(
        f"1985-06-21 {native_hour:02d}:00:00", *LONDON,
        f"1990-01-15 {partner_hour:02d}:00:00", *partner, **kwargs)


@pytest.mark.parametrize("native_hour,partner_hour", list(itertools.product(HOURS, HOURS)))
def test_london_svalbard_cusps_in_order(native_hour, partner_hour):
    result = _composite(native_hour, partner_hour)
    assert result["status"] == "success", result
    assert _in_order(_cusps(result))


@pytest.mark.parametrize("house_system", ["PLACIDUS", "REGIOMONTANUS", "PORPHYRIUS", "KOCH"])
@pytest.mark.parametrize("hour", range(0, 24, 2))
def test_mc_on_cusp_10_is_in_house_10(house_system, hour):
    moment = f"1985-06-21 {hour:02d}:00:00"
    result = generate_composite_chart(
        moment, *LONDON, moment, *SVALBARD,
        native_timezone="UTC", partner_timezone="UTC", house_system=house_system)
    if result["status"] == "error":
        # Regiomontanus cusps can come back reversed at Svalbard.
        assert result["type"] == "PolarHouseError"
        return
    mc, asc = _object(result, "MC"), _object(result, "Asc")
    cusps = _cusps(result)
    assert mc["longitude"]["raw"] == pytest.approx(cusps[9], abs=1e-9)
    assert asc["longitude"]["raw"] == pytest.approx(cusps[0], abs=1e-9)
    assert mc["house"]["number"] == 10
    assert asc["house"]["number"] == 1


@pytest.mark.parametrize("native_hour,partner_hour", [(0, 0), (6, 15), (12, 3), (21, 18)])
def test_unwrapped_pairs_match_immanuel(native_hour, partner_hour):
    native = create_subject(f"1985-06-21 {native_hour:02d}:00:00", 51.5, -0.13)
    partner = create_subject(f"1990-01-15 {partner_hour:02d}:00:00", -33.87, 151.2)
    config = new_config()
    ours = CoherentComposite(native, partner, config=config)
    theirs = charts.Composite(native, partner, config=config)
    for index, house in theirs._houses.items():
        assert ours._houses[index]["lon"] == pytest.approx(house["lon"], abs=1e-9)
        assert ours._houses[index]["size"] == pytest.approx(house["size"], abs=1e-9)
    for index in (chart.ASC, chart.DESC, chart.MC, chart.IC):
        assert ours._objects[index]["lon"] == pytest.approx(theirs._objects[index]["lon"], abs=1e-9)


def test_polar_fallback_still_reported():
    result = generate_compact_composite_chart(
        "1985-06-21 00:00:00", *LONDON, "1990-01-15 15:00:00", *SVALBARD)
    assert result["status"] == "success", result
    assert "fallback" in result["applied_settings"]["house_system"]
    houses = sorted(result["houses"].values(), key=lambda h: h["number"])
    assert _in_order([h["longitude"] for h in houses])
    assert set(houses[0]) == {"number", "sign", "sign_longitude", "longitude"}


def test_whole_sign_unchanged():
    native = create_subject("1985-06-21 00:00:00", 51.5, -0.13)
    partner = create_subject("1990-01-15 15:00:00", 78.22, 15.63)
    config = new_config()
    config.house_system = chart.WHOLE_SIGN
    ours = CoherentComposite(native, partner, config=config)
    theirs = charts.Composite(native, partner, config=config)
    assert {i: h["lon"] for i, h in ours._houses.items()} == {i: h["lon"] for i, h in theirs._houses.items()}

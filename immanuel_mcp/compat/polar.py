"""
Let Placidus and Koch charts inside the polar circles build.

immanuel 1.6 and 1.7 hard-coded Placidus for the Part of Fortune Ascendant
and the diurnal check, so every polar chart failed, Whole Sign included.
1.8 fixed that (theriftlab/immanuel-python#32): those calculations now use
Equal houses, and only a chart whose own system is Placidus or Koch fails.
It fails on purpose: immanuel.tools.sweph.angles_houses_vertex turns the
Swiss Ephemeris "within polar circle, switched to Porphyry" error into a
ValueError. Placidus is the default house system, so without this shim a
default chart for Tromso would be an error.

install() replaces the `swe` that immanuel.tools.sweph sees (only there, not
the swisseph module itself) with a proxy whose two house functions retry
that error with Porphyry, which is what the C library had already switched
to, and record the fallback for the response. The retry happens inside the
call, so immanuel's own `except swe.Error` (which resolves to swisseph's
Error through the proxy) never sees it. Every other call, and every other
error, passes straight through.

The proxy also rejects reversed cusps. At some moments inside a polar
circle the Swiss Ephemeris returns Regiomontanus, Campanus and Polich Page
cusps in clockwise order, with the MC and IC swapped. immanuel's house
lookup assumes zodiacal order, so it raised KeyError('index') or, for Polich
Page, built a chart with the houses scrambled. Those casts now raise
PolarHouseError, which names the systems that work. They are not swapped
for Porphyry: the Swiss Ephemeris doesn't refuse these systems, so a
fallback would override a valid request.
"""

import logging
from importlib import metadata

import swisseph as swe
from immanuel.const import chart as chart_const
from immanuel.const import names
from immanuel.support.localize import localize
from immanuel.tools import sweph

from ..utils.call_context import note_polar_fallback, polar_fell_back
from ..utils.errors import PolarHouseError

logger = logging.getLogger(__name__)

# The immanuel releases whose sweph.py this was checked against. The pin is
# immanuel>=1.8.0,<1.9 (1.8 wraps the two house calls in try/except swe.Error
# but keeps their arguments); widen this only after re-reading
# angles_houses_vertex.
SUPPORTED = ("1.8.",)
POLAR_MESSAGE = "polar circle"
PORPHYRY = b"O"
_HSYS_POSITION = 3  # houses_ex2(jd, lat, lon, hsys) / houses_armc_ex2(armc, lat, eps, hsys)
_LAT_POSITION = 1


def cusps_reversed(cusps) -> bool:
    """Whether twelve cusps run clockwise. The binding returns 13 values,
    the first a placeholder. In zodiacal order the forward gaps add up to one
    turn; reversed, they add up to eleven."""
    cusps = cusps[-12:]
    return sum((cusps[(i + 1) % 12] - cusps[i]) % 360 for i in range(12)) > 361


def _argument(args, kwargs, position, name):
    return kwargs[name] if name in kwargs else args[position]


def _polar_safe(function):
    def call(*args, **kwargs):
        requested = _argument(args, kwargs, _HSYS_POSITION, "hsys")
        try:
            result = function(*args, **kwargs)
        except swe.Error as error:
            if POLAR_MESSAGE not in str(error):
                raise
            if "hsys" in kwargs:
                kwargs = {**kwargs, "hsys": PORPHYRY}
            else:
                args = (*args[:_HSYS_POSITION], PORPHYRY, *args[_HSYS_POSITION + 1:])
            note_polar_fallback(requested)
            result = function(*args, **kwargs)
        if cusps_reversed(result[0]):
            raise PolarHouseError(
                f"{_system_name(requested)} houses can't be cast at latitude "
                f"{_argument(args, kwargs, _LAT_POSITION, 'lat'):.4f} at this moment: "
                f"inside the polar circle the Swiss Ephemeris returns them in reverse "
                f"order, with the MC below the horizon.")
        return result
    call.__name__ = function.__name__
    return call


def _system_name(code: bytes) -> str:
    for system, swe_code in sweph._SWE.items():
        if swe_code == code:
            return names.HOUSE_SYSTEMS[system]
    return code.decode()


class _PolarSafeSwisseph:
    """swisseph, with the two house functions made polar-safe."""

    houses_ex2 = staticmethod(_polar_safe(swe.houses_ex2))
    houses_armc_ex2 = staticmethod(_polar_safe(swe.houses_armc_ex2))

    def __getattr__(self, name):
        return getattr(swe, name)


PROXY = _PolarSafeSwisseph()


def installed() -> bool:
    return sweph.swe is PROXY


def install() -> None:
    version = metadata.version("immanuel")
    if not version.startswith(SUPPORTED):
        raise RuntimeError(
            f"immanuel {version} is not one the polar-circle shim was checked "
            f"against ({', '.join(SUPPORTED)}x). Re-check "
            f"immanuel.tools.sweph.angles_houses_vertex and update "
            f"immanuel_mcp/compat/polar.py.")
    if sweph.swe is not swe and not installed():
        raise RuntimeError("immanuel.tools.sweph.swe is not the swisseph module")
    sweph.swe = PROXY


def reported_house_system(chart) -> str:
    """
    The chart's house_system as immanuel serialises it (the configured
    system's name, translated), except Porphyrius (immanuel's name for
    Porphyry, which resolve_house_system accepts back) when this chart's own
    houses fell back to it.

    The fallback is recorded per call, and one call can build a polar chart
    and a non-polar one (a Tromsø natal with a return relocated to London),
    so the chart's own subjects are re-checked. Placidus and its kin fail on
    latitude and obliquity alone, which is what that check sees. Only runs
    when the call recorded a fallback for this system, so every other chart
    is untouched.
    """
    system = chart._config.house_system
    code = sweph._SWE.get(system)
    if not polar_fell_back(code):
        return chart.house_system
    subjects = [getattr(chart, name, None) for name in ("_native", "_partner")]
    if not any(falls_back(subject, code) for subject in subjects if subject is not None):
        return chart.house_system
    return localize(names.HOUSE_SYSTEMS[chart_const.PORPHYRIUS], chart._config.locale)


def falls_back(subject, code: bytes) -> bool:
    """Whether this subject's houses fall back to Porphyry for this system."""
    try:
        swe.houses_ex2(subject.julian_date, subject.latitude, subject.longitude, code)
    except swe.Error as error:
        return POLAR_MESSAGE in str(error)
    return False

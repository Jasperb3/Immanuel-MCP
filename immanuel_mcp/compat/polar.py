"""
Let charts inside the polar circles build.

immanuel 1.6 and 1.7 hard-code Placidus for the Part of Fortune Ascendant
(tools/part.py) and the diurnal check (tools/condition.py), and uses the
chart's own system for the houses. All three go through
immanuel.tools.sweph.angles_houses_vertex, which calls swe.houses_ex2 or
swe.houses_armc_ex2. Inside a polar circle the Swiss Ephemeris C library
falls back to Porphyry and reports a warning, which pysweph raises as
swisseph.Error, so every chart failed, Whole Sign included.

install() replaces the `swe` that immanuel.tools.sweph sees (only there, not
the swisseph module itself) with a proxy whose two house functions retry
that error with Porphyry, which is what the C library had already switched
to, and record the fallback for the response. The Ascendant and MC do not
depend on the house system, so the Part of Fortune and diurnal results are
unaffected. Every other call, and every other error, passes straight
through.
"""

import logging
from importlib import metadata

import swisseph as swe
from immanuel.const import chart as chart_const
from immanuel.const import names
from immanuel.support.localize import localize
from immanuel.tools import sweph

from ..utils.call_context import note_polar_fallback, polar_fell_back

logger = logging.getLogger(__name__)

# The immanuel releases whose sweph.py this was checked against. The pin is
# immanuel>=1.7.0,<1.8 (angles_houses_vertex is unchanged from 1.6); widen
# this only after re-reading angles_houses_vertex.
SUPPORTED = ("1.7.",)
POLAR_MESSAGE = "polar circle"
PORPHYRY = b"O"
_HSYS_POSITION = 3  # houses_ex2(jd, lat, lon, hsys) / houses_armc_ex2(armc, lat, eps, hsys)


def _polar_safe(function):
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except swe.Error as error:
            if POLAR_MESSAGE not in str(error):
                raise
            if "hsys" in kwargs:
                requested = kwargs["hsys"]
                kwargs = {**kwargs, "hsys": PORPHYRY}
            else:
                requested = args[_HSYS_POSITION]
                args = (*args[:_HSYS_POSITION], PORPHYRY, *args[_HSYS_POSITION + 1:])
            note_polar_fallback(requested)
            return function(*args, **kwargs)
    call.__name__ = function.__name__
    return call


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
    if not any(_falls_back(subject, code) for subject in subjects if subject is not None):
        return chart.house_system
    return localize(names.HOUSE_SYSTEMS[chart_const.PORPHYRIUS], chart._config.locale)


def _falls_back(subject, code: bytes) -> bool:
    try:
        swe.houses_ex2(subject.julian_date, subject.latitude, subject.longitude, code)
    except swe.Error as error:
        return POLAR_MESSAGE in str(error)
    return False

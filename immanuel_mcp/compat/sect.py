"""
Restore in_sect on night charts.

immanuel 1.7.0's Chart.wrap_objects computes

    in_sect = (condition.is_object_in_sect(...)
               if self._time_known and is_daytime else None)

so every nocturnal chart (diurnal False) omits in_sect for all seven sect
planets (wrap.Object sets the attribute only when it is not None). 1.6
reported True/False. The intended test is `is_daytime is not None` (no sect
without a known time).

install() is guarded on behaviour, not on a version list: it casts one
known night chart with the unpatched method, and wraps Chart.wrap_objects
only if in_sect comes back missing. A release that fixes the bug leaves
the shim off by itself; one that keeps it keeps the shim on.
tests/test_sect_compat.py checks the result on every chart class either way. Remove this module once
the pinned immanuel no longer shows the bug.

Only Chart defines wrap_objects (no subclass overrides it), and charts bind
it at construction, so patching the class covers Natal, SolarReturn,
Progressed, Composite and Transits.
"""

import functools
import logging

from immanuel import charts
from immanuel.const import chart as chart_const
from immanuel.tools import condition

logger = logging.getLogger(__name__)

# A known-time night chart (diurnal False): Sydney, 2001-03-21 23:59.
_PROBE = ("2001-03-21 23:59:00", -33.87, 151.21, "Australia/Sydney")

STATE = "not-installed"  # then "patched" or "not-needed"
_original = None


def unpatched_wrap_objects():
    return _original or charts.Chart.wrap_objects


def probe_shows_bug(wrap_objects) -> bool:
    """Whether wrap_objects leaves the probe night chart's Sun without in_sect."""
    dt, lat, lon, tz = _PROBE
    natal = charts.Natal(charts.Subject(dt, lat, lon, timezone=tz))
    if natal._diurnal is not False:
        raise RuntimeError("sect probe chart is no longer a night chart")
    wrap_objects(natal)
    return getattr(natal.objects[chart_const.SUN], "in_sect", None) is None


def _restore_sect(wrap_objects):
    @functools.wraps(wrap_objects)
    def wrapped(self):
        wrap_objects(self)
        if not (self._time_known and self._diurnal is False):
            return
        sun = self._triad[chart_const.SUN]
        for index, obj in self.objects.items():
            in_sect = condition.is_object_in_sect(
                object=self._objects[index], is_daytime=False, sun=sun)
            # As wrap.Object does: the attribute exists only when not None.
            if in_sect is not None:
                obj.in_sect = in_sect

    return wrapped


def install() -> None:
    global STATE, _original
    if _original is not None:
        return
    original = charts.Chart.wrap_objects
    if probe_shows_bug(original):
        _original = original
        charts.Chart.wrap_objects = _restore_sect(original)
        STATE = "patched"
        logger.info("immanuel drops in_sect on night charts; sect shim installed")
    else:
        STATE = "not-needed"
        logger.info("immanuel reports in_sect on night charts; sect shim not needed")

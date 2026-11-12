"""Composite houses that stay in zodiacal order.

immanuel's ``Composite`` midpoints every house cusp on its own shorter arc
(``swe.deg_midp``) and averages the house sizes. When a pair of cusps is
nearly 180 degrees apart, some midpoints land on the far side of the circle,
so the cusps run out of order, and the averaged sizes no longer match the
cusps: an MC sitting exactly on cusp 10 was placed in house 9.

``CoherentComposite`` keeps cusp 1 (the shorter-arc midpoint, as before) and
places every other cusp at the mean of the two charts' distances from their
own cusp 1, so the cusps keep each chart's order. The MC is placed the same
way from the Ascendant, with the IC and Descendant opposite. Sizes are
recomputed from the new cusps as immanuel does for any chart. Where no
midpoint wraps, this is algebraically the same as immanuel's result.
Whole Sign composites (built from the ARMC midpoint) are left alone.

When either chart is inside a polar circle, where Placidus or Koch fall back
to Porphyry, both charts' cusps are cast in Porphyry. Otherwise the
composite took the midpoint of one chart's real Placidus cusps and the
other's Porphyry ones, which is neither system (London + Svalbard put the
composite Moon a house away from kerykeion's all-Porphyry composite).
"""

import swisseph as swe
from immanuel import charts
from immanuel.const import chart
from immanuel.tools import ephemeris, sweph

from .polar import falls_back


def _mean_offset(native: float, native_ref: float, partner: float, partner_ref: float) -> float:
    return (swe.degnorm(native - native_ref) + swe.degnorm(partner - partner_ref)) / 2


def _dec(lon: float, obliquity: float) -> float:
    return swe.cotrans((lon, 0, 1), -obliquity)[1]


class CoherentComposite(charts.Composite):
    """immanuel's Composite with house cusps and angles kept in order."""

    def generate(self) -> None:
        super().generate()
        if not self._time_known or self._config.house_system == chart.WHOLE_SIGN:
            return
        self._rebuild_houses()
        self._rebuild_angles()

    def _subject_kwargs(self, subject, house_system=None) -> dict:
        return dict(jd=subject.julian_date, lat=subject.latitude, lon=subject.longitude,
                    house_system=house_system or self._config.house_system)

    def _house_system(self) -> int:
        """The configured system, or Porphyry for both charts when either
        falls back to it, so the midpoints come from one system."""
        code = sweph._SWE[self._config.house_system]
        if falls_back(self._native, code) or falls_back(self._partner, code):
            return chart.PORPHYRIUS
        return self._config.house_system

    def _rebuild_houses(self) -> None:
        system = self._house_system()
        native = ephemeris.get_houses(**self._subject_kwargs(self._native, system))
        partner = ephemeris.get_houses(**self._subject_kwargs(self._partner, system))
        first = chart.HOUSE + 1
        n1, p1 = native[first]["lon"], partner[first]["lon"]
        anchor = swe.deg_midp(n1, p1)
        lons = {
            index: swe.degnorm(anchor + _mean_offset(native[index]["lon"], n1, partner[index]["lon"], p1))
            for index in self._houses
        }
        lons[first] = anchor
        for number in range(1, 13):
            index = chart.HOUSE + number
            following = chart.HOUSE + (number % 12) + 1
            house = self._houses[index]
            house["lon"] = lons[index]
            house["size"] = swe.difdeg2n(lons[following], lons[index])
            house["dec"] = _dec(lons[index], self._obliquity)

    def _rebuild_angles(self) -> None:
        if chart.MC not in self._objects or chart.ASC not in self._objects:
            return
        native = ephemeris.get_angles(**self._subject_kwargs(self._native))
        partner = ephemeris.get_angles(**self._subject_kwargs(self._partner))
        asc = self._objects[chart.ASC]["lon"]
        mc = swe.degnorm(asc + _mean_offset(
            native[chart.MC]["lon"], native[chart.ASC]["lon"],
            partner[chart.MC]["lon"], partner[chart.ASC]["lon"]))
        self._set_angle(chart.MC, mc)
        self._set_angle(chart.IC, swe.degnorm(mc + 180))
        self._set_angle(chart.DESC, swe.degnorm(asc + 180))

    def _set_angle(self, index: int, lon: float) -> None:
        if index not in self._objects:
            return
        angle = self._objects[index]
        angle["lon"] = lon
        if "dec" in angle:
            angle["dec"] = _dec(lon, self._obliquity)

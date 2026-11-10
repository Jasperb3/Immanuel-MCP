#!/usr/bin/env python3
"""
The solar return tools cast a second chart at the return instant as the
lifecycle reference. It used to be rebuilt from the return time formatted
as a zone-less clock string and read back in the coordinates' zone, so a
caller's timezone other than that zone moved it by the difference (an hour
for London with timezone="UTC"), and a return in a fall-back night's
repeated hour was read as the first reading.
"""

import pytest
from immanuel import charts

import immanuel_server

BIRTH = ("1990-05-15 12:00:00", "51n30", "0w07")


@pytest.mark.parametrize("build", [
    immanuel_server.generate_solar_return_chart,
    immanuel_server.generate_compact_solar_return_chart,
], ids=["full", "compact"])
@pytest.mark.parametrize("timezone", [None, "Europe/London", "UTC", "America/New_York"])
def test_the_lifecycle_reference_is_the_return_instant(build, timezone, monkeypatch):
    seen = {}

    def capture(result, natal_chart, comparison_chart, birth_datetime, comparison_datetime, **_):
        seen["julian"] = comparison_chart._native.julian_date
        seen["local"] = comparison_datetime

    monkeypatch.setattr(immanuel_server, "attach_lifecycle_section", capture)
    result = build(*BIRTH, 2026, timezone)
    assert result["status"] == "success", result.get("message")

    kwargs = {"timezone": timezone} if timezone else {}
    expected = charts.SolarReturn(
        charts.Subject(BIRTH[0], 51.5, -7 / 60, **kwargs), 2026).solar_return_date_time
    assert seen["julian"] == pytest.approx(expected.julian, abs=1e-9)
    # Ages are worked out against the birth time as a local wall clock, so
    # the reference is passed the same way, in the birth zone.
    assert seen["local"] == expected.datetime.replace(tzinfo=None)

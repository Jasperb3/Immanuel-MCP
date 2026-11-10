"""create_subject helper function"""

import re
from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from immanuel import charts
from immanuel.const import chart as chart_const
from immanuel.const import names as names_const
from immanuel.support.localize import localize
from immanuel.tools import convert, position, sweph
from immanuel.tools import date as date_tools

from .call_context import add_warning

TIME_STATUS_NAMES = {
    chart_const.TIME_KNOWN: "known",
    chart_const.TIME_APPROXIMATE: "approximate",
    chart_const.TIME_UNKNOWN: "unknown",
}

# What immanuel 1.7 leaves out of a chart whose birth time isn't known.
_OMITTED = (
    "houses, the angles (Ascendant, MC and their opposites), the Vertex, the "
    "Parts of Fortune, Spirit and Eros, sect and day/night triplicity rulers "
    "are omitted")


# A UTC offset (or Z) right after the clock time: 01:30Z, 01:30:00+01:00,
# 01:30:00.5-0330, 01:30 +05.
_EXPLICIT_OFFSET = re.compile(
    r"\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?\s*(Z|[+-]\d{2}(?::?\d{2})?)$", re.IGNORECASE)


def _format_offset(offset: timedelta) -> str:
    minutes = int(offset.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    hours, rest = divmod(abs(minutes), 60)
    return f"UTC{sign}{hours}" + (f":{rest:02d}" if rest else "")


def _utc_offset(local: datetime) -> str:
    return _format_offset(local.utcoffset())


def _explicit_offset(date_time) -> timedelta | None:
    """The UTC offset written into a date_time string, or None."""
    if not isinstance(date_time, str):
        return None
    match = _EXPLICIT_OFFSET.search(date_time.strip())
    if not match:
        return None
    token = match.group(1)
    if token.upper() == "Z":
        return timedelta(0)
    digits = token[1:].replace(":", "")
    offset = timedelta(hours=int(digits[:2]), minutes=int(digits[2:] or 0))
    return -offset if token[0] == "-" else offset


def _honour_offset(subject: charts.Subject, subject_kwargs: dict, offset: timedelta,
                   date_time: str, who: str = None) -> charts.Subject:
    """
    The Subject for the reading of the local time that `offset` names.

    immanuel replaces a datetime's own zone with the one it looks up from
    the coordinates (by design, theriftlab/immanuel-python#33), so an offset
    in the string is dropped: 12:00+05:00 in London is cast at 12:00 BST.
    An offset that is one reading of the local time picks that reading
    (`time_is_dst=False` is immanuel's switch to the second, fold=1, of a
    fall-back night or the later offset across a spring-forward gap). One
    that is neither contradicts the zone, and is an error rather than a
    guess at which of the two the caller meant.
    """
    local = subject.date_time
    if local.utcoffset() == offset:
        return subject
    other = local.replace(fold=1 - local.fold)
    if other.utcoffset() == offset:
        return charts.Subject(**subject_kwargs, time_is_dst=other.fold == 0)
    readings = [local] + ([other] if other.utcoffset() != local.utcoffset() else [])
    zone = local.tzinfo
    label = f"{who}'s date_time" if who else "date_time"
    raise ValueError(
        f"{label} {date_time} gives {_format_offset(offset)}, but {local:%H:%M} on "
        f"{local:%Y-%m-%d} in {getattr(zone, 'key', zone)} is "
        f"{' or '.join(f'{_utc_offset(r)} ({r.tzname()})' for r in readings)}. "
        f"Drop the offset to use the local time there, or pass the timezone the "
        f"offset belongs to (e.g. timezone='UTC' for a Z time).")


def _warn_on_clock_change(subject: charts.Subject, offset_given: bool = False) -> None:
    """
    Say which reading was used when a local time falls in a clock change.

    A time inside a spring-forward gap never happened, and one inside a
    fall-back overlap happened twice. immanuel accepts both silently and
    flags them only as `date_time_ambiguous`; the offset it actually used is
    on the resolved datetime, which is what this reports. Without an offset
    in the input, the fall-back warning says how to choose the other reading.
    """
    local = subject.date_time
    zone = local.tzinfo
    if not isinstance(zone, ZoneInfo):
        return
    wall = local.replace(tzinfo=None)
    same_instant = local.astimezone(dt_timezone.utc).astimezone(zone)
    clock, day = f"{wall:%H:%M}", wall.date().isoformat()
    used = f"{clock} {local.tzname()} ({_utc_offset(local)})"
    if same_instant.replace(tzinfo=None) != wall:
        add_warning(
            f"{clock} did not exist on {day} in {zone.key} (the clocks went "
            f"forward); using {used}, the same instant as {same_instant:%H:%M} "
            f"{same_instant.tzname()} ({_utc_offset(same_instant)})")
    elif local.replace(fold=1 - local.fold).utcoffset() != local.utcoffset():
        choose = "" if offset_given else (
            ". Write the UTC offset to choose: " + " or ".join(
                f"{reading.isoformat()} ({reading.tzname()})"
                for reading in (local.replace(fold=0), local.replace(fold=1))))
        add_warning(
            f"{clock} occurred twice on {day} in {zone.key} (the clocks went "
            f"back); using {used}, the {'first' if local.fold == 0 else 'second'} "
            f"of the two{choose}")


def _moon_at(local: datetime, locale: str = None) -> dict:
    lon, _ = sweph.longitude(chart_const.MOON, date_tools.to_jd(local))
    return {
        "time": local.isoformat(),
        "longitude": lon,
        "sign": localize(names_const.SIGNS[position.sign(lon)], locale),
        "sign_longitude": convert.dec_to_string(position.sign_longitude(lon)),
    }


def moon_range(subject: charts.Subject, locale: str = None) -> dict:
    """
    Where the Moon is over the subject's local birth day, 00:00 to 23:59.

    For an unknown birth time the chart's Moon is the noon Moon, while the
    real one could be anywhere along this span (12-15 degrees). sign_change
    says whether the Moon's sign itself is in doubt.
    """
    day = subject.date_time
    start = _moon_at(day.replace(hour=0, minute=0, second=0, microsecond=0), locale)
    end = _moon_at(day.replace(hour=23, minute=59, second=0, microsecond=0), locale)
    start_sign = position.sign(start["longitude"])
    return {
        "start": start,
        "end": end,
        "sign_change": position.sign(end["longitude"]) != start_sign,
    }


def _warn_on_time_status(subject: charts.Subject, who: str = None) -> None:
    """Say what an approximate or unknown birth time leaves out. `who`
    ("Native", "Partner") names the person in a two-chart call."""
    label = f"{who}'s birth time" if who else "Birth time"
    status = subject.time_status
    local = subject.date_time
    if status == chart_const.TIME_APPROXIMATE:
        add_warning(
            f"{label} approximate: the chart is cast at {local:%Y-%m-%d %H:%M} "
            f"{local.tzname()}, but {_OMITTED}, since they depend on an exact time.")
    elif status == chart_const.TIME_UNKNOWN:
        span = moon_range(subject)
        start, end = span["start"], span["end"]
        moon = (
            f"The Moon changes sign that day ({start['sign']} {start['sign_longitude']} "
            f"at 00:00 to {end['sign']} {end['sign_longitude']} at 23:59), so its "
            f"sign is uncertain."
            if span["sign_change"] else
            f"It stays in {start['sign']} all day ({start['sign_longitude']} at "
            f"00:00 to {end['sign_longitude']} at 23:59).")
        add_warning(
            f"{label} unknown: the chart is cast for local noon "
            f"({local:%Y-%m-%d} 12:00 {local.tzname()}), and {_OMITTED}. The Moon "
            f"moves 12-15 degrees a day, so its position may be up to ~7 degrees "
            f"off. {moon}")


def warn_on_untimed_derived_chart(kind: str, subject: charts.Subject) -> None:
    """
    Say how an approximate or unknown birth time carries into a chart derived
    from it: "solar" or "lunar" return (the instant is found from the natal
    Sun or Moon) or "progressed". `subject` is the birth subject.
    """
    status = subject.time_status
    if status == chart_const.TIME_KNOWN:
        return
    omitted = "the return chart's houses and angles are omitted"
    if kind == "progressed":
        add_warning(
            "Progressed chart from an untimed birth: the progressed angles are "
            "omitted, and the progressed Moon (about 1 degree a month) carries "
            "the natal Moon's uncertainty of up to ~7 degrees, so progressed-Moon "
            "timing may be up to ~7 months out."
            if status == chart_const.TIME_UNKNOWN else
            "Progressed chart from an approximate birth time: the progressed "
            "angles are omitted.")
        return
    name = {"solar": "Solar", "lunar": "Lunar"}[kind]
    if status == chart_const.TIME_APPROXIMATE:
        add_warning(
            f"{name} return from an approximate birth time: the return instant "
            f"shifts by about as much as the birth time is off, so {omitted}.")
    elif kind == "solar":
        add_warning(
            "Solar return from an untimed birth: the natal Sun is the noon Sun, "
            "up to ~0.5 degrees from the real one, so the return instant may be "
            f"off by up to ~12 hours either way; {omitted}.")
    else:
        span = moon_range(subject)
        start, end = span["start"], span["end"]
        add_warning(
            f"Lunar return from an untimed birth: the natal Moon is the noon Moon, "
            f"and the real one lies between {start['sign']} {start['sign_longitude']} "
            f"(00:00) and {end['sign']} {end['sign_longitude']} (23:59), so the "
            f"return instant may be off by up to ~12 hours either way; {omitted}.")


def create_subject(date_time: str, latitude: float, longitude: float, timezone: str = None,
                   time_status: int = chart_const.TIME_KNOWN, who: str = None) -> charts.Subject:
    """
    Create an Immanuel Subject with optional timezone.

    Args:
        date_time: Date and time string in ISO format. A UTC offset in it
            (Z, +00:00) chooses between the two readings of a clock-change
            time; one the location's zone never has at that time is an error.
        latitude: Parsed latitude as float
        longitude: Parsed longitude as float
        timezone: Optional IANA timezone name
        time_status: chart_const.TIME_KNOWN (default), TIME_APPROXIMATE or
            TIME_UNKNOWN (see validate_time_status). Anything but known adds
            a warning naming what the chart leaves out.
        who: Names the person in that warning ("Native", "Partner") when a
            call takes two birth charts.

    Returns:
        Configured Subject instance
    """
    subject_kwargs = {
        'date_time': date_time,
        'latitude': latitude,
        'longitude': longitude
    }
    if timezone:
        subject_kwargs['timezone'] = timezone
    if time_status != chart_const.TIME_KNOWN:
        subject_kwargs['time_status'] = time_status
    subject = charts.Subject(**subject_kwargs)
    if time_status != chart_const.TIME_UNKNOWN:
        # An unknown time is replaced by noon, so the given clock time is moot.
        offset = _explicit_offset(date_time)
        if offset is not None:
            subject = _honour_offset(subject, subject_kwargs, offset, date_time, who)
        _warn_on_clock_change(subject, offset_given=offset is not None)
    _warn_on_time_status(subject, who)
    return subject


def effective_timezone(subject: charts.Subject) -> str:
    """
    The IANA timezone a Subject actually resolved to.

    ``Subject.timezone`` only holds what the caller passed, so it stays None
    whenever the timezone was omitted - even though immanuel has already
    inferred one from the coordinates and used it for the chart. The resolved
    zone lives on the parsed datetime's tzinfo, which is what this reads, so
    responses can echo the zone the chart was actually built in rather than
    reporting null for an inferred one.

    Args:
        subject: A Subject built by create_subject

    Returns:
        IANA timezone name (e.g. 'America/Los_Angeles')
    """
    return str(subject.date_time.tzinfo)

"""create_subject helper function"""

from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from immanuel import charts

from .call_context import add_warning


def _utc_offset(local: datetime) -> str:
    minutes = int(local.utcoffset().total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    hours, rest = divmod(abs(minutes), 60)
    return f"UTC{sign}{hours}" + (f":{rest:02d}" if rest else "")


def _warn_on_clock_change(subject: charts.Subject) -> None:
    """
    Say which reading was used when a local time falls in a clock change.

    A time inside a spring-forward gap never happened, and one inside a
    fall-back overlap happened twice. immanuel accepts both silently and
    flags them only as `date_time_ambiguous`; the offset it actually used is
    on the resolved datetime, which is what this reports.
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
        add_warning(
            f"{clock} occurred twice on {day} in {zone.key} (the clocks went "
            f"back); using {used}, the {'first' if local.fold == 0 else 'second'} "
            f"of the two")


def create_subject(date_time: str, latitude: float, longitude: float, timezone: str = None) -> charts.Subject:
    """
    Create an Immanuel Subject with optional timezone.

    Args:
        date_time: Date and time string in ISO format
        latitude: Parsed latitude as float
        longitude: Parsed longitude as float
        timezone: Optional IANA timezone name

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
    subject = charts.Subject(**subject_kwargs)
    _warn_on_clock_change(subject)
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

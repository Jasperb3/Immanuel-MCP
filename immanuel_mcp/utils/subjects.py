"""create_subject helper function"""

from immanuel import charts


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
    return charts.Subject(**subject_kwargs)


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

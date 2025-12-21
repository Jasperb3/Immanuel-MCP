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

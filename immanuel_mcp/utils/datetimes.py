"""Datetime string parsing shared across chart endpoints."""

import re
from datetime import datetime
from typing import Union


def iso_timestamp(moment: datetime) -> str:
    """
    A computed moment (a return, a lunation, an ingress) as the one
    timestamp format the tools emit: ISO 8601, whole seconds, explicit
    offset, e.g. '2026-07-01T13:51:43+01:00'.

    Seconds are truncated, not rounded: a displayed time is never later than
    the moment, so a return at 23:59:59.8 on the last day of a month still
    reads as that day. Month membership is decided from the Julian date
    before formatting, never from this string.
    """
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"iso_timestamp needs an aware datetime, got {moment!r}")
    return moment.replace(microsecond=0).isoformat()


def parse_datetime_value(value: Union[str, datetime]) -> datetime:
    """Parse various datetime formats used throughout the API."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Unsupported datetime input: {value!r}")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Empty datetime string")

    # Remove a trailing timezone name: an IANA zone (Europe/London) or a
    # short alphabetic abbreviation (UTC, GMT, BST). The token must contain
    # no digits - a previous heuristic based on "uppercase and short" also
    # matched times like "1:00" and silently dropped them.
    parts = cleaned.split()
    if len(parts) > 1 and ('/' in parts[-1] or (parts[-1].isalpha() and len(parts[-1]) <= 4)):
        cleaned = ' '.join(parts[:-1])

    # Strip trailing timezone offsets or Z markers
    cleaned = re.sub(r'(Z|[+-]\d{2}:?\d{2})$', '', cleaned)

    iso_candidate = cleaned
    if 'T' not in iso_candidate and ' ' in iso_candidate:
        first_space = iso_candidate.find(' ')
        if first_space != -1:
            iso_candidate = iso_candidate[:first_space] + 'T' + iso_candidate[first_space + 1:]
    try:
        return datetime.fromisoformat(iso_candidate)
    except ValueError:
        pass

    fallback_formats = (
        '%a %b %d %Y %H:%M:%S',
        '%a %b %d %Y %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d'
    )
    for fmt in fallback_formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse datetime string: {value}")

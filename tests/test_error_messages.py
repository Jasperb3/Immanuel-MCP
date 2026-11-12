"""Input errors say what is wrong and report every bad field at once."""

import pytest

from immanuel_server import generate_compact_natal_chart, generate_composite_chart


def test_impossible_date_is_not_called_a_format_error():
    result = generate_compact_natal_chart("1990-02-30 12:00:00", "51.5", "-0.13")
    assert result["status"] == "error"
    assert "day is out of range for month" in result["message"]
    assert "format" not in result["message"]
    assert "February" in result["suggestion"]


def test_bad_format_keeps_the_format_hint():
    result = generate_compact_natal_chart("1990/02/03 12:00", "51.5", "-0.13")
    assert "Invalid datetime format" in result["message"]
    assert "ISO format" in result["suggestion"]


def test_every_bad_field_is_reported_together():
    result = generate_compact_natal_chart("1990-01-15 12:00:00", "51.5", "200", timezone="Mars/Base")
    assert result["status"] == "error"
    assert "Longitude" in result["message"]
    assert "Mars/Base" in result["message"]
    assert "51n23" in result["suggestion"]
    assert "IANA" in result["suggestion"]


def test_bad_timezone_alone_is_unchanged():
    result = generate_compact_natal_chart("1990-01-15 12:00:00", "51.5", "-0.13", timezone="Mars/Base")
    assert result["type"] == "ZoneInfoNotFoundError"
    assert result["message"] == "Unknown IANA timezone 'Mars/Base'."


def test_out_of_range_coordinate_suggests_formats():
    result = generate_compact_natal_chart("1990-01-15 12:00:00", "51.5", "200")
    assert "51n23" in result["suggestion"]
    assert "Immanuel documentation" not in result["suggestion"]


def test_partner_timezone_checked_up_front():
    result = generate_composite_chart(
        "1990-01-15 12:00:00", "51.5", "-0.13", "1990-01-15 12:00:00", "95", "0",
        partner_timezone="Nowhere/Land")
    assert "Nowhere/Land" in result["message"] and "Latitude" in result["message"]

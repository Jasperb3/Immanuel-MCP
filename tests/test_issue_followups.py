#!/usr/bin/env python3
"""
Regression tests for the four reported tool defects.

Each test pins one fixed defect so it cannot silently return:
- #1: compact charts emitted the houses block in full, unflattened form
- #2: transit_to_natal DMS wrote seconds with a minutes mark (12°21'42')
- #3: reset_immanuel_settings restored library defaults with no diff reported
- #4: list_available_settings displayed numeric house codes that configure
      rejected on input

Run from the repo root: python -m pytest tests/test_issue_followups.py
"""

import asyncio
import json
import pathlib
import re
import subprocess
import sys

import pytest
from immanuel import charts, setup
from immanuel.classes.serialize import ToJSON

import immanuel_server
from immanuel_mcp.app import mcp as shared_mcp
from immanuel_mcp.optimizers.positions import format_declination, format_position
from immanuel_mcp.utils.settings import (
    _house_system_constants,
    house_system_display_name,
    resolve_house_system,
)
from immanuel_mcp.utils.subjects import create_subject

BIRTH = ("1990-01-15 14:30:00", "32.71", "-117.15")
TIMEZONE = "America/Los_Angeles"
TRANSIT_DATE = "2026-07-04 12:00:00"

# Degrees, two-digit minutes, two-digit seconds, seconds marked with ".
DMS = re.compile(r"^-?\d+°\d{2}'\d{2}\"$")


@pytest.fixture
def restore_settings():
    """Settings are a process-global singleton; do not leak into other tests."""
    before = setup.settings.house_system
    yield
    setup.settings.house_system = before


# ---------------------------------------------------------------------------
# #1: compact charts must actually compact the houses block
# ---------------------------------------------------------------------------

def test_compact_houses_are_flattened():
    chart = immanuel_server.generate_compact_natal_chart(*BIRTH, TIMEZONE)
    houses = chart["houses"]

    assert len(houses) == 12
    for house in houses.values():
        assert set(house) == {"number", "sign", "sign_longitude", "longitude"}
        # The nested wrappers that used to survive verbatim.
        assert isinstance(house["sign"], str)
        assert isinstance(house["longitude"], float)
        assert DMS.match(house["sign_longitude"])


def test_compact_houses_are_smaller_than_full_houses():
    subject = create_subject(*BIRTH, TIMEZONE)
    full = json.loads(json.dumps(charts.Natal(subject), cls=ToJSON))
    compact = immanuel_server.generate_compact_natal_chart(*BIRTH, TIMEZONE)

    full_size = len(json.dumps(full["houses"]))
    compact_size = len(json.dumps(compact["houses"]))
    # It was byte-identical before the fix; anything near parity is a regression.
    assert compact_size < full_size / 2


# ---------------------------------------------------------------------------
# #2: seconds carry the arcsecond mark, not a second apostrophe
# ---------------------------------------------------------------------------

def test_format_helpers_preserve_the_seconds_mark():
    assert format_position({"formatted": "12°21'42\""}, "Scorpio") == "12°21'42\" Scorpio"
    assert format_declination({"formatted": "-23°26'19\""}) == "-23°26'19\""


def test_format_helpers_tolerate_missing_data():
    assert format_position({}, "Aries") == " Aries"
    assert format_declination({}) == ""


def test_transit_to_natal_positions_use_arcsecond_marks():
    result = immanuel_server.generate_transit_to_natal(*BIRTH, TRANSIT_DATE)
    positions = result["transit_positions"]

    assert positions
    for name, data in positions.items():
        position = data["position"]
        sign_longitude, _, sign = position.rpartition(" ")
        assert DMS.match(sign_longitude), f"{name}: {position!r}"
        assert sign
        # The exact corruption reported: seconds digits closed by an apostrophe.
        assert not re.search(r"'\d{2}'", position), f"{name}: {position!r}"
        assert DMS.match(data["declination"]), f"{name}: {data['declination']!r}"


# ---------------------------------------------------------------------------
# #3: reset reports what it changed instead of changing it silently
# ---------------------------------------------------------------------------

def test_reset_reports_the_diff(restore_settings):
    startup = setup.settings.house_system
    other = "WHOLE_SIGN" if startup != resolve_house_system("WHOLE_SIGN") else "PLACIDUS"
    immanuel_server.configure_immanuel_settings("house_system", other)

    result = immanuel_server.reset_immanuel_settings()

    assert result["status"] == "success"
    assert result["changed"] == ["house_system"]
    assert result["previous_settings"]["house_system"] == house_system_display_name(
        resolve_house_system(other))
    assert result["restored_settings"]["house_system"] == house_system_display_name(startup)
    assert setup.settings.house_system == startup
    # Retained alias for callers still reading the old key.
    assert result["restored_defaults"] == result["restored_settings"]


def test_reset_is_a_no_op_when_nothing_changed(restore_settings):
    immanuel_server.reset_immanuel_settings()
    assert immanuel_server.reset_immanuel_settings()["changed"] == []


# ---------------------------------------------------------------------------
# #4: displayed house-system values are accepted as input
# ---------------------------------------------------------------------------

def test_numeric_codes_and_names_resolve_alike():
    placidus = resolve_house_system("Placidus")
    assert resolve_house_system(placidus) == placidus
    assert resolve_house_system(str(placidus)) == placidus
    assert resolve_house_system("PLACIDUS") == placidus


def test_every_advertised_value_round_trips():
    systems = immanuel_server.list_available_settings()["settings"]["house_system"]
    assert systems["available_systems"]

    for entry in systems["available_systems"]:
        for accepted in entry["accepts"]:
            assert resolve_house_system(accepted) == entry["code"]


@pytest.mark.parametrize("bad", [999, "999", "Not A House System", True])
def test_unknown_house_systems_still_raise(bad):
    with pytest.raises(ValueError, match="Unknown house system"):
        resolve_house_system(bad)


def test_configure_reports_one_vocabulary(restore_settings):
    code = resolve_house_system("WHOLE_SIGN")
    result = immanuel_server.configure_immanuel_settings("house_system", code)

    assert result["status"] == "success"
    assert result["new_value"] == "Whole Sign"
    # old_value used to be the raw numeric code while new_value was a name.
    assert not result["old_value"].isdigit()
    assert setup.settings.house_system == code


def test_current_house_system_code_is_accepted_back(restore_settings):
    current = immanuel_server.list_available_settings()["settings"]["house_system"]["current"]
    result = immanuel_server.configure_immanuel_settings("house_system", current)
    assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Release stamps. The version is single-sourced from pyproject.toml
# (immanuel_mcp.__version__ reads package metadata, falling back to
# pyproject), so the first test guards the remaining gap: an installed
# distribution whose metadata has gone stale against the source - exactly
# what a `git pull` without `uv sync` produces on the Windows production
# checkout. The banner is still a hand-written literal, and both it and the
# counts have drifted before, so they are checked against reality.
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    assert match, "no version in pyproject.toml"
    return match.group(1)


def _readme_banner() -> re.Match:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    match = re.search(r"\*\*v(\S+) · (\d+) tools · (\d+) tests passing", text)
    assert match, "README banner line not found or reshaped"
    return match


def test_package_version_matches_pyproject():
    from immanuel_mcp import __version__
    assert __version__ == _pyproject_version()


def test_readme_banner_version_matches_pyproject():
    assert _readme_banner().group(1) == _pyproject_version()


def test_readme_banner_counts_match_reality():
    banner = _readme_banner()
    tools = asyncio.run(shared_mcp.list_tools())
    assert int(banner.group(2)) == len(tools)

    # sys.executable, not a bare "python": on Windows the latter resolves to
    # whatever is first on PATH rather than this venv, which collected a
    # different (much smaller) set of tests and failed the assertion.
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q",
         "-p", "no:cacheprovider"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert collected.returncode == 0, collected.stdout[-800:]
    count = re.search(r"^(\d+) tests? collected", collected.stdout, re.MULTILINE)
    assert count, collected.stdout[-800:]
    assert int(banner.group(3)) == int(count.group(1))

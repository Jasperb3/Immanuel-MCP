"""Session and per-call chart configuration.

Immanuel 1.6 has no global settings singleton: every chart takes a
``charts.Config`` via ``config=`` and freezes a snapshot of it at
construction. This module owns the one mutable session-level Config that
``configure_immanuel_settings`` edits and ``reset_immanuel_settings``
replaces.

Always reach it through ``get_session_config()``. Reset rebinds the
module-level name to a fresh copy, so a ``from ... import _session_config``
elsewhere would keep the stale object and silently ignore every reset.
"""

import os
import re

import immanuel
from immanuel import charts
from immanuel.const import calc as calc_const
from immanuel.const import chart as chart_const
from immanuel.const import names as names_const
from immanuel.tools import sweph

from .call_context import add_warning, polar_fell_back
from .subjects import TIME_STATUS_NAMES


_session_config = charts.Config()

# Captured once, at import, before any configure_immanuel_settings call can
# run. reset_immanuel_settings restores this rather than a fresh Config, so if
# the server is ever configured at launch that launch configuration is what
# "reset" goes back to. Config.copy() is a deep copy, so in-place edits to the
# session's `objects` list or orb maps never reach the snapshot.
_STARTUP_CONFIG = _session_config.copy()


def get_session_config() -> charts.Config:
    """The mutable session-level Config that configure_immanuel_settings edits."""
    return _session_config


def _house_system_constants() -> dict:
    """Map chart-const attribute names (e.g. 'WHOLE_SIGN') to their constants."""
    display_names = dict(names_const.HOUSE_SYSTEMS)
    return {
        attr: getattr(chart_const, attr)
        for attr in dir(chart_const)
        if attr.isupper() and getattr(chart_const, attr) in display_names
    }


def house_system_display_name(constant) -> str:
    """Human-readable name for a house-system constant (e.g. 113 -> 'Whole Sign')."""
    return dict(names_const.HOUSE_SYSTEMS).get(constant, str(constant))


def _normalize_house_system(value: str) -> str:
    """Case/spacing-insensitive key for house-system name lookups."""
    return value.strip().upper().replace(" ", "_").replace("-", "_")


def _house_system_error(value) -> ValueError:
    """Build the shared "unknown house system" error listing every valid value."""
    valid = ", ".join(
        f"{code} — {attr} — {house_system_display_name(code)}"
        for attr, code in sorted(_house_system_constants().items(), key=lambda item: item[1])
    )
    return ValueError(f"Unknown house system '{value}'. Valid values: {valid}")


def resolve_house_system(name) -> int:
    """
    Resolve a house system to its immanuel constant, with validation.

    Accepts either the numeric code that list_available_settings displays
    (108 or "108"), or the constant name in any case, with spaces or hyphens
    in place of underscores ('WHOLE_SIGN', 'whole sign', 'Campanus').

    Raises:
        ValueError: If the value is unknown; the message lists every valid
                    value as "CODE — CONSTANT_NAME — Display Name".
    """
    constants = _house_system_constants()

    # Numeric codes: the form list_available_settings reports as `current`,
    # which used to be rejected on input.
    if isinstance(name, bool):
        raise _house_system_error(name)
    if isinstance(name, int):
        if name not in constants.values():
            raise _house_system_error(name)
        return name
    if isinstance(name, str) and name.strip().isdigit():
        code = int(name.strip())
        if code not in constants.values():
            raise _house_system_error(name)
        return code

    # Constant names and display names both, normalized the same way. They
    # are not interchangeable - EQUAL is displayed as "Equal House" and
    # VEHLOW_EQUAL as "Vehlow Equal House" - so accepting only the constant
    # names rejected the very names list_available_settings advertises.
    lookup = {_normalize_house_system(attr): code for attr, code in constants.items()}
    lookup.update({
        _normalize_house_system(display): code
        for code, display in names_const.HOUSE_SYSTEMS.items()
    })

    key = _normalize_house_system(str(name))
    if key not in lookup:
        raise _house_system_error(name)
    return lookup[key]


def build_call_config(house_system: str = None) -> charts.Config:
    """
    Build the Config for a single chart call.

    Returns the session Config when no overrides are given (preserving
    configure_immanuel_settings behaviour). Sharing it is safe: each chart
    freezes its own snapshot at construction. With an override, returns a
    fresh Config with only the override applied.

    Note: a fresh Config starts from library defaults, so a per-call override
    deliberately ignores any session-level changes made via
    configure_immanuel_settings — the two mechanisms do not mix.
    """
    if house_system is None:
        return get_session_config()
    # TODO: 1.6 makes "session config + override" trivial
    # (get_session_config().copy() then set house_system) if that semantic is
    # ever wanted; the documented contract today is "override ignores session".
    call_config = charts.Config()
    call_config.house_system = resolve_house_system(house_system)
    return call_config


# Retained for one release for callers of the pre-1.6 name.
build_call_settings = build_call_config


PROGRESSION_METHOD_CONSTANTS = {
    "NAIBOD": calc_const.NAIBOD,
    "SOLAR_ARC": calc_const.SOLAR_ARC,
    "DAILY_HOUSES": calc_const.DAILY_HOUSES,
}

ORB_CALCULATION_CONSTANTS = {
    "MEAN": calc_const.MEAN,
    "MAX": calc_const.MAX,
}


def _resolve_named_constant(name: str, constants: dict, display_names: dict, setting: str) -> int:
    """Resolve a constant name against an allowlist, or raise a ValueError
    listing every valid value as "CONSTANT_NAME — Display Name"."""
    key = name.strip().upper().replace(" ", "_").replace("-", "_")
    if key not in constants:
        valid = ", ".join(
            f"{attr} — {display_names.get(value, attr.title())}"
            for attr, value in constants.items()
        )
        raise ValueError(f"Unknown {setting} '{name}'. Valid values: {valid}")
    return constants[key]


def resolve_progression_method(name: str) -> int:
    """Resolve an MC progression method name (e.g. 'DAILY_HOUSES'), with validation."""
    return _resolve_named_constant(
        name, PROGRESSION_METHOD_CONSTANTS,
        dict(names_const.PROGRESSION_METHODS), "MC progression method")


def resolve_orb_calculation(name: str) -> int:
    """Resolve an orb calculation method name ('MEAN' or 'MAX'), with validation."""
    return _resolve_named_constant(
        name, ORB_CALCULATION_CONSTANTS, {}, "orb calculation method")


def _aspect_constants() -> dict:
    """Map calc-const aspect names (e.g. 'TRINE') to their angles."""
    known_angles = dict(names_const.ASPECTS)
    return {
        attr: getattr(calc_const, attr)
        for attr in dir(calc_const)
        if attr.isupper() and isinstance(getattr(calc_const, attr), float)
        and getattr(calc_const, attr) in known_angles
    }


def _aspect_key(name: str) -> str:
    """Spelling-insensitive key: 'Semi-sextile', 'semi sextile' and
    'SEMISEXTILE' all match immanuel's SEMISEXTILE / 'Semisextile'."""
    return re.sub(r"[\s_-]", "", name).upper()


def resolve_aspects(value: str) -> list:
    """
    Resolve a comma-separated aspect list to immanuel's aspect angles.

    Each item is an aspect name ('TRINE', 'Semi-sextile': constant or display
    name, any case, hyphens and spaces ignored) or a numeric angle in [0, 180]
    ('120', '54.3'). Raises ValueError listing the valid names on anything else.
    """
    constants = _aspect_constants()
    lookup = {_aspect_key(attr): angle for attr, angle in constants.items()}
    lookup.update({_aspect_key(display): angle
                   for angle, display in names_const.ASPECTS.items()})
    angles = []
    for raw in value.split(","):
        item = raw.strip()
        key = _aspect_key(item)
        if key in lookup:
            angles.append(lookup[key])
            continue
        try:
            angle = float(item)
        except ValueError:
            angle = None
        if angle is None or not 0 <= angle <= 180:
            valid = ", ".join(
                f"{attr} ({angle:g}°)"
                for attr, angle in sorted(constants.items(), key=lambda kv: kv[1]))
            raise ValueError(
                f"Unknown aspect '{item}'. Use a name or an angle from 0 to 180. "
                f"Valid names: {valid}")
        angles.append(angle)
    return angles


def _object_constants() -> dict:
    """Map chart-const object names (e.g. 'TRUE_NORTH_NODE') to their indices."""
    indices = {}
    for table in (names_const.ANGLES, names_const.PLANETS, names_const.ASTEROIDS,
                  names_const.POINTS, names_const.ECLIPSES):
        indices.update(table)
    return {
        attr: getattr(chart_const, attr)
        for attr in dir(chart_const)
        if attr.isupper() and isinstance(getattr(chart_const, attr), int)
        and getattr(chart_const, attr) in indices
    }


def _ephemeris_rejects(index) -> str:
    """Return '' if immanuel's ephemeris resolves `index` (a fixed-star name,
    or an object code such as an asteroid's official number), else the reason
    it does not. Uses immanuel's own lookup, so the ephemeris path a chart
    would search is the one checked."""
    from immanuel.tools import ephemeris
    try:
        # J2000; any date resolves the name. lat/lon are needed only by
        # location-dependent points, which are all named constants anyway.
        ephemeris.get(index, 2451545.0, lat=0.0, lon=0.0)
    except Exception as e:  # swisseph.Error for unknown names and missing files, KeyError/ValueError for bad codes
        return f"{type(e).__name__}: {e}"
    return ""


def resolve_objects(value: str) -> list:
    """
    Resolve a comma-separated object list to immanuel object indices.

    Each item is a chart-const name ('SUN', 'TRUE_NORTH_NODE', any case), a
    numeric object code ('4000001'), or something immanuel's ephemeris can
    actually resolve: an asteroid's official number whose ephemeris file is
    installed ('433'), or a fixed-star name. Anything else raises ValueError:
    storing an unresolvable index makes every later chart fail with
    'Invalid object index'.
    """
    constants = _object_constants()
    valid_codes = set(constants.values())
    objects = []
    for raw in value.split(","):
        item = raw.strip()
        if item.isdigit() and int(item) in valid_codes:
            objects.append(int(item))
            continue
        key = _normalize_house_system(item)
        if key in constants:
            objects.append(constants[key])
            continue
        candidate = int(item) if item.isdigit() else item
        reason = _ephemeris_rejects(candidate)
        if reason:
            valid = ", ".join(sorted(constants))
            raise ValueError(
                f"Unknown object '{item}': not an object name or code, and not an "
                f"asteroid number or fixed star the Swiss Ephemeris can resolve "
                f"({reason}). Fixed stars cannot resolve at all: they need the "
                f"star catalogue sefstars.txt, which is not shipped with the "
                f"ephemeris files. Valid names: {valid}")
        objects.append(candidate)
    return objects


def available_locales() -> list:
    """The locales immanuel ships translations for, plus 'en_US' (English,
    the untranslated default)."""
    locales_dir = os.path.join(os.path.dirname(immanuel.__file__), "locales")
    shipped = sorted(
        entry for entry in os.listdir(locales_dir)
        if os.path.isdir(os.path.join(locales_dir, entry)) and not entry.startswith("_"))
    return ["en_US", *shipped]


def resolve_locale(value: str):
    """
    Resolve a locale to the value stored on the Config: one of immanuel's
    shipped locales, or None for 'en_US' (English is the untranslated
    default). Raises ValueError listing the valid locales on anything else -
    immanuel 1.6 silently falls back to English for an unknown locale, so
    without this a typo would report success and change nothing.
    """
    valid = available_locales()
    if value.strip() not in valid:
        raise ValueError(f"Unknown locale '{value}'. Valid values: {', '.join(valid)}")
    return None if value.strip() == "en_US" else value.strip()


# Numeric orb settings that exist on charts.Config.
ORB_SETTINGS = ("default_orb", "exact_orb", "chart_shape_orb")


def _settings_summary() -> dict:
    """Human-readable snapshot of every setting configure_immanuel_settings
    can change. objects and aspects are shown as counts."""
    config = get_session_config()
    orb_calculation_names = {v: k for k, v in ORB_CALCULATION_CONSTANTS.items()}
    return {
        "house_system": house_system_display_name(config.house_system),
        "locale": config.locale,
        "mc_progression_method": dict(names_const.PROGRESSION_METHODS).get(
            config.mc_progression_method),
        "orb_calculation": orb_calculation_names.get(config.orb_calculation),
        **{key: getattr(config, key) for key in ORB_SETTINGS},
        "objects": len(config.objects),
        "aspects": len(config.aspects),
    }


def _settings_state() -> dict:
    """The summary with objects and aspects in full, so a change of members
    that keeps the same count still shows up in reset's `changed` list."""
    config = get_session_config()
    return {**_settings_summary(),
            "objects": list(config.objects), "aspects": list(config.aspects)}


def reset_global_settings() -> dict:
    """
    Restore the session Config to the server's startup configuration and
    report exactly what changed.

    The startup configuration is captured in ``_STARTUP_CONFIG`` when this
    module is first imported, so it is immanuel's library defaults unless the
    server was configured at launch. It is NOT the set of values that were in
    effect immediately before the caller's changes - restoring those would
    require a per-change undo history, which this server does not keep. The
    returned diff exists so that distinction is visible rather than silent.

    Locale needs no special handling: in 1.6 translations are resolved per
    chart from its Config, so restoring the Config restores the language.
    """
    global _session_config
    previous, previous_state = _settings_summary(), _settings_state()

    _session_config = _STARTUP_CONFIG.copy()

    restored, restored_state = _settings_summary(), _settings_state()
    changed = sorted(k for k in restored_state
                     if previous_state.get(k) != restored_state.get(k))

    return {
        "previous_settings": previous,
        "restored_settings": restored,
        "changed": changed,
    }


def build_applied_settings(house_system: str = None,
                           time_status: int = chart_const.TIME_KNOWN) -> dict:
    """
    Build the applied_settings echo for a chart response, so the consuming
    LLM can verify which settings produced the chart instead of assuming.

    A chart without a known birth time casts no houses, so house_system is
    None and time_status names the status ("approximate" or "unknown"). The
    key is absent for a known time, so ordinary responses are unchanged.
    """
    if house_system is None:
        system, source = get_session_config().house_system, "session-global"
    else:
        system, source = resolve_house_system(house_system), "per-call"
    if time_status != chart_const.TIME_KNOWN:
        return {"house_system": None, "source": source,
                "time_status": TIME_STATUS_NAMES[time_status]}
    name = house_system_display_name(system)
    if polar_fell_back(sweph._SWE.get(system)):
        add_warning(
            f"A chart in this response lies inside a polar circle, where {name} "
            f"houses are undefined, so the Swiss Ephemeris used Porphyry cusps "
            f"instead. The Ascendant and MC are unaffected. Pass "
            f"house_system='WHOLE_SIGN' (or another non-polar system) to avoid "
            f"the fallback.")
        name = f"Porphyry (polar fallback from {name})"
    return {"house_system": name, "source": source}

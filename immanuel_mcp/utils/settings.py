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

from immanuel import charts
from immanuel.const import calc as calc_const
from immanuel.const import chart as chart_const
from immanuel.const import names as names_const


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


def _settings_summary() -> dict:
    """Human-readable snapshot of the settings a caller is likely to care about."""
    config = get_session_config()
    return {
        "house_system": house_system_display_name(config.house_system),
        "locale": config.locale,
        "mc_progression_method": dict(names_const.PROGRESSION_METHODS).get(
            config.mc_progression_method),
        "objects": len(config.objects),
        "aspects": len(config.aspects),
    }


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
    previous = _settings_summary()

    _session_config = _STARTUP_CONFIG.copy()

    restored = _settings_summary()
    changed = sorted(k for k in restored if previous.get(k) != restored.get(k))

    return {
        "previous_settings": previous,
        "restored_settings": restored,
        "changed": changed,
    }


def build_applied_settings(house_system: str = None) -> dict:
    """
    Build the applied_settings echo for a chart response, so the consuming
    LLM can verify which settings produced the chart instead of assuming.
    """
    if house_system is None:
        return {
            "house_system": house_system_display_name(get_session_config().house_system),
            "source": "session-global",
        }
    return {
        "house_system": house_system_display_name(resolve_house_system(house_system)),
        "source": "per-call",
    }

"""Per-call settings helpers.

Immanuel 1.5.4+ chart classes accept a per-call ``settings`` object,
which lets a single tool call use e.g. a different house system without
mutating the global singleton that ``configure_immanuel_settings``
manages for the rest of the session.
"""

import copy
import locale

from immanuel import setup
from immanuel.classes.cache import FunctionCache
from immanuel.classes.localize import MAPPINGS, Localize
from immanuel.const import calc as calc_const
from immanuel.const import chart as chart_const
from immanuel.const import names as names_const
from immanuel.setup import ImmanuelSettings


# Captured once, at import, before any configure_immanuel_settings call can
# run. reset_immanuel_settings restores this rather than a fresh
# ImmanuelSettings, so if the server is ever configured at launch that launch
# configuration is what "reset" goes back to. Deep-copied because `objects`,
# `aspects` and the orb dicts are mutable and callers can change them in place.
_STARTUP_SNAPSHOT = {
    key: copy.deepcopy(getattr(setup.settings, key))
    for key in vars(ImmanuelSettings())
}


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


def build_call_settings(house_system: str = None):
    """
    Build the settings object for a single chart call.

    Returns the global settings singleton when no overrides are given
    (preserving configure_immanuel_settings behaviour), else a fresh
    ImmanuelSettings with the override applied.

    Note: a fresh ImmanuelSettings starts from library defaults, so a
    per-call override deliberately ignores any session-level changes made
    via configure_immanuel_settings — the two mechanisms do not mix.
    """
    if house_system is None:
        return setup.settings
    call_settings = ImmanuelSettings()
    call_settings.house_system = resolve_house_system(house_system)
    return call_settings


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
    return {
        "house_system": house_system_display_name(setup.settings.house_system),
        "locale": setup.settings.locale,
        "mc_progression_method": dict(names_const.PROGRESSION_METHODS).get(
            setup.settings.mc_progression_method),
        "objects": len(setup.settings.objects),
        "aspects": len(setup.settings.aspects),
    }


def _reset_localization() -> None:
    """
    Clear immanuel's translation state to match a restored locale.

    Assigning the ``_locale`` backing attribute bypasses the ``locale``
    property setter, so ``Localize`` would otherwise keep serving the
    previous language while ``settings.locale`` reported the restored value.
    This mirrors ``Localize.reset()`` but guards its ``setlocale`` call, which
    is the reason we do not call immanuel's own ``settings.reset()``: it
    hard-codes ``en_US``, which raises on systems without that locale.
    """
    FunctionCache.clear_all()
    Localize.lcid = None
    Localize.translation = None
    MAPPINGS.clear()
    try:
        locale.setlocale(locale.LC_TIME, "en_US")
    except locale.Error:
        locale.setlocale(locale.LC_TIME, "C")


def reset_global_settings() -> dict:
    """
    Restore the global settings singleton to the server's startup
    configuration and report exactly what changed.

    The startup configuration is captured in ``_STARTUP_SNAPSHOT`` when this
    module is first imported, so it is immanuel's library defaults unless the
    server was configured at launch. It is NOT the set of values that were in
    effect immediately before the caller's changes - restoring those would
    require a per-change undo history, which this server does not keep. The
    returned diff exists so that distinction is visible rather than silent.

    Values are assigned to the backing attributes directly (including property
    backings such as ``_locale``), so no property side effects fire; the
    localization state those side effects would have managed is reset
    separately by ``_reset_localization``.
    """
    previous = _settings_summary()

    for key, value in _STARTUP_SNAPSHOT.items():
        setattr(setup.settings, key, copy.deepcopy(value))
    _reset_localization()
    if setup.settings.locale is not None:
        try:
            Localize.set_locale(setup.settings.locale)
        except locale.Error:
            # Same upstream hazard as above: an unavailable locale must not
            # turn a reset into a failed call. The settings value is restored
            # either way; only the translation layer is left untouched.
            pass

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
            "house_system": house_system_display_name(setup.settings.house_system),
            "source": "session-global",
        }
    return {
        "house_system": house_system_display_name(resolve_house_system(house_system)),
        "source": "per-call",
    }

"""Per-call settings helpers.

Immanuel 1.5.4+ chart classes accept a per-call ``settings`` object,
which lets a single tool call use e.g. a different house system without
mutating the global singleton that ``configure_immanuel_settings``
manages for the rest of the session.
"""

from immanuel import setup
from immanuel.const import chart as chart_const
from immanuel.const import names as names_const
from immanuel.setup import ImmanuelSettings


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


def resolve_house_system(name: str) -> int:
    """
    Resolve a house-system name to its immanuel constant, with validation.

    Accepts the constant name in any case, with spaces or hyphens in place
    of underscores (e.g. 'WHOLE_SIGN', 'whole sign', 'Campanus').

    Raises:
        ValueError: If the name is unknown; the message lists every valid
                    value as "CONSTANT_NAME — Display Name".
    """
    constants = _house_system_constants()
    key = name.strip().upper().replace(" ", "_").replace("-", "_")
    if key not in constants:
        valid = ", ".join(
            f"{attr} — {house_system_display_name(value)}"
            for attr, value in sorted(constants.items(), key=lambda item: item[1])
        )
        raise ValueError(
            f"Unknown house system '{name}'. Valid values: {valid}"
        )
    return constants[key]


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

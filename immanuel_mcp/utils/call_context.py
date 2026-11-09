"""
Per-call state shared by the helpers one tool call goes through.

A tool decorated with @reports_warnings gets a fresh CallState for the
duration of the call. Helpers deep inside it (subject creation, the polar
house shim) record into it, and the decorator attaches the collected
`warnings` to the response. A response with nothing to report carries no
`warnings` key, so ordinary responses are unchanged.

A ContextVar keeps calls apart: FastMCP runs each sync tool call in a
worker thread with a copy of the context.
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from typing import List, Optional, Set


@dataclass
class CallState:
    warnings: List[str] = field(default_factory=list)
    # Swiss Ephemeris house-system codes (b'P', b'K', ...) that fell back to
    # Porphyry because the chart lies inside a polar circle.
    polar_fallbacks: Set[bytes] = field(default_factory=set)


_STATE: ContextVar[Optional[CallState]] = ContextVar("immanuel_mcp_call_state", default=None)


def add_warning(message: str) -> None:
    state = _STATE.get()
    if state is not None and message not in state.warnings:
        state.warnings.append(message)


def note_polar_fallback(system_code: bytes) -> None:
    state = _STATE.get()
    if state is not None:
        state.polar_fallbacks.add(system_code)


def polar_fell_back(system_code: bytes) -> bool:
    state = _STATE.get()
    return state is not None and system_code in state.polar_fallbacks


def reports_warnings(fn):
    """Give each call of `fn` its own CallState and attach its warnings."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        state = CallState()
        token = _STATE.set(state)
        try:
            result = fn(*args, **kwargs)
        finally:
            _STATE.reset(token)
        if state.warnings and isinstance(result, dict):
            result["warnings"] = list(state.warnings)
        return result
    return wrapper

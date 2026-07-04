"""Attach lifecycle event data to a chart response dictionary."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..utils.datetimes import parse_datetime_value
from .lifecycle import detect_lifecycle_events, format_lifecycle_event_feed

logger = logging.getLogger(__name__)


def attach_lifecycle_section(
    result: Dict[str, Any],
    natal_chart,
    comparison_chart,
    birth_datetime: Union[str, datetime],
    comparison_datetime: Union[str, datetime],
    include_future: bool = True,
    future_years: int = 20,
    max_future_events: int = 10,
    additional_events: Optional[List[Dict[str, Any]]] = None
) -> None:
    """Populate lifecycle fields on the result dictionary."""
    try:
        birth_dt = parse_datetime_value(birth_datetime)
        comparison_dt = parse_datetime_value(comparison_datetime)

        lifecycle_data = detect_lifecycle_events(
            natal_chart=natal_chart,
            transit_chart=comparison_chart,
            birth_datetime=birth_dt,
            transit_datetime=comparison_dt,
            include_future=include_future,
            future_years=future_years,
            max_future_events=max_future_events
        )

        payload = format_lifecycle_event_feed(
            lifecycle_data,
            comparison_dt,
            additional_events=additional_events
        )

        result["lifecycle_events"] = payload["events"]
        result["lifecycle_summary"] = payload["summary"]

    except Exception as exc:
        logger.warning("Lifecycle events detection failed: %s", exc, exc_info=True)
        result["lifecycle_events"] = None
        result["lifecycle_summary"] = None

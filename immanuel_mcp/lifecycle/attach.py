"""Attach lifecycle event data to a chart response dictionary."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from immanuel import charts

from ..constants import PLANET_CONSTANTS
from ..utils.datetimes import parse_datetime_value
from ..utils.settings import new_config
from .lifecycle import detect_lifecycle_events, format_lifecycle_event_feed

logger = logging.getLogger(__name__)

# Every body the lifecycle detector reads from the charts it is given.
LIFECYCLE_OBJECTS = list(PLANET_CONSTANTS.values())


def _with_lifecycle_objects(chart):
    """The chart itself, or, if its config's object list leaves out a body
    lifecycle needs (configure_immanuel_settings objects=[...]), the same
    chart rebuilt with those bodies added. Without this, events for the
    missing bodies vanished and the timeline fell back to estimated dates."""
    missing = [index for index in LIFECYCLE_OBJECTS if chart.objects.get(index) is None]
    if not missing or not isinstance(chart, charts.Natal):
        return chart
    config = new_config()
    config.house_system = chart._config.house_system
    config.objects = list(dict.fromkeys([*chart._config.objects, *missing]))
    return charts.Natal(chart._native, config=config)


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
            natal_chart=_with_lifecycle_objects(natal_chart),
            transit_chart=_with_lifecycle_objects(comparison_chart),
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

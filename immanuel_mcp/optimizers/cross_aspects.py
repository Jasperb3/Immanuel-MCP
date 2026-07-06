"""Predictive-chart-to-natal cross aspects (aspects_to extraction).

Progressed and return charts gain a natal_cross_aspects section built from
a second chart constructed with aspects_to=natal. In that serialization the
nested aspect keys carry direction: from = the predictive chart's object,
to = the natal object (the same convention v0.5.0 established for
transit-to-natal). Self-pairs (e.g. progressed Moon to natal Moon) are
kept - they are the core of progression and return technique.
"""

from typing import Any, Dict, List, Tuple

from ..interpretations.aspects import (
    get_context_aware_interpretation,
    normalize_aspects_to_list,
)
from ..pagination.helpers import (
    build_aspect_summary,
    classify_all_aspects,
    classify_aspect_priority,
    filter_aspects_by_priority,
    get_actual_orb,
)

VALID_PRIORITIES = ("tight", "moderate", "loose", "all")


def _movement_label(aspect: Dict[str, Any]) -> Any:
    movement = aspect.get("movement")
    if isinstance(movement, dict):
        return movement.get("formatted")
    return movement


def build_full_cross_aspects(
    cross_chart_data: Dict[str, Any],
    source_key: str
) -> List[Dict[str, Any]]:
    """
    Build the natal_cross_aspects list from a ToJSON-serialized aspects_to
    chart. Returns every cross aspect (all objects, all configured aspect
    types) in a compact per-aspect shape to respect MCP size limits.

    Args:
        cross_chart_data: json-decoded ToJSON serialization of the chart
                          built with aspects_to=natal
        source_key: label for the predictive side, e.g. 'progressed_object'
                    or 'return_object' (the other side is 'natal_object')
    """
    object_names = {
        obj["index"]: obj.get("name")
        for obj in cross_chart_data.get("objects", {}).values()
        if isinstance(obj, dict) and "index" in obj
    }

    entries = []
    for aspect in normalize_aspects_to_list(
        cross_chart_data.get("aspects", {}), filter_self_aspects=False
    ):
        from_name = object_names.get(aspect.get("from_index"))
        to_name = object_names.get(aspect.get("to_index"))
        if not from_name or not to_name:
            continue
        entries.append({
            source_key: from_name,
            "natal_object": to_name,
            "type": aspect.get("type"),
            "orb": round(get_actual_orb(aspect), 2),
            "movement": _movement_label(aspect),
            "priority": classify_aspect_priority(aspect),
        })
    return entries


def build_compact_cross_aspects(
    cross_chart_data: Dict[str, Any],
    source_key: str,
    aspect_priority: str = "tight"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Build (natal_cross_aspects, natal_cross_aspect_summary) from a
    CompactJSONSerializer serialization of an aspects_to chart: major
    objects and major aspects only, filtered to the requested priority
    tier, with interpretation hints.

    An unknown aspect_priority falls back to 'tight' (same behaviour as
    transit-to-natal).
    """
    if aspect_priority not in VALID_PRIORITIES:
        aspect_priority = "tight"

    all_aspects = cross_chart_data.get("aspects", [])
    tight, moderate, loose = classify_all_aspects(all_aspects)
    summary = build_aspect_summary(tight, moderate, loose, aspect_priority)

    entries = []
    for aspect in filter_aspects_by_priority(all_aspects, aspect_priority):
        entry = {
            source_key: aspect.get("from_object"),
            "natal_object": aspect.get("to_object"),
            "type": aspect.get("type"),
            "orb": round(get_actual_orb(aspect), 2),
            "priority": classify_aspect_priority(aspect),
        }
        interp = get_context_aware_interpretation(
            aspect.get("object1", ""), aspect.get("object2", ""), aspect.get("type", "")
        )
        entry["keywords"] = interp.get("keywords", [])
        entry["nature"] = interp.get("nature", "variable")
        if "description" in interp:
            entry["interpretation"] = interp["description"]
        entries.append(entry)

    return entries, summary

"""Pagination helpers"""

from typing import Any, Dict, List
import json



# ============================================================================
# Aspect Pagination Helpers (for MCP size limit compliance)
# ============================================================================

def classify_aspect_priority(aspect: dict) -> str:
    """
    Classify aspect by orb into priority tiers.

    Tight aspects (0-2°): Peak influence, most noticeable effects
    Moderate aspects (2-5°): Secondary influence, still noticeable
    Loose aspects (5-8°): Background influence, subtle effects

    Args:
        aspect: Aspect dictionary with 'orb' field

    Returns:
        "tight", "moderate", or "loose"
    """
    orb = abs(aspect.get('orb', 0))

    if orb <= 2.0:
        return "tight"
    elif orb <= 5.0:
        return "moderate"
    else:
        return "loose"


def filter_aspects_by_priority(aspects: list, priority: str) -> list:
    """
    Filter aspects to only those matching the specified priority tier.

    Args:
        aspects: List of aspect dictionaries
        priority: "tight", "moderate", "loose", or "all"

    Returns:
        Filtered list of aspects
    """
    if priority == "all":
        return aspects

    return [asp for asp in aspects if classify_aspect_priority(asp) == priority]


def classify_all_aspects(aspects: list) -> tuple:
    """
    Classify all aspects into priority tiers.

    Args:
        aspects: List of aspect dictionaries

    Returns:
        Tuple of (tight_aspects, moderate_aspects, loose_aspects)
    """
    tight = []
    moderate = []
    loose = []

    for aspect in aspects:
        priority = classify_aspect_priority(aspect)
        if priority == "tight":
            tight.append(aspect)
        elif priority == "moderate":
            moderate.append(aspect)
        else:
            loose.append(aspect)

    return (tight, moderate, loose)


def build_aspect_summary(
    tight: list,
    moderate: list,
    loose: list,
    current_priority: str
) -> dict:
    """
    Build summary counts for aspect pagination.

    Args:
        tight: List of tight aspects
        moderate: List of moderate aspects
        loose: List of loose aspects
        current_priority: The priority tier being returned

    Returns:
        Summary dictionary with counts and current page info
    """
    summary = {
        "tight_aspects": len(tight),
        "moderate_aspects": len(moderate),
        "loose_aspects": len(loose),
        "total_aspects": len(tight) + len(moderate) + len(loose)
    }

    # Indicate which aspects are in this response
    if current_priority == "tight":
        summary["returned_in_this_page"] = len(tight)
    elif current_priority == "moderate":
        summary["returned_in_this_page"] = len(moderate)
    elif current_priority == "loose":
        summary["returned_in_this_page"] = len(loose)
    else:  # "all"
        summary["returned_in_this_page"] = summary["total_aspects"]

    return summary


def build_pagination_object(
    current_priority: str,
    has_tight: bool,
    has_moderate: bool,
    has_loose: bool
) -> dict:
    """
    Build pagination metadata for aspect navigation.

    Args:
        current_priority: Current priority tier ("tight", "moderate", "loose", "all")
        has_tight: Whether tight aspects exist
        has_moderate: Whether moderate aspects exist
        has_loose: Whether loose aspects exist

    Returns:
        Pagination metadata dictionary
    """
    # Define page mapping
    priority_pages = {
        "tight": 1,
        "moderate": 2,
        "loose": 3,
        "all": None
    }

    current_page = priority_pages.get(current_priority)
    total_pages = sum([has_tight, has_moderate, has_loose])

    # Determine next page
    next_page = None
    if current_priority == "tight" and has_moderate:
        next_page = "moderate"
    elif current_priority == "moderate" and has_loose:
        next_page = "loose"

    has_more = next_page is not None

    pagination = {
        "current_page": current_page,
        "total_pages": total_pages,
        "has_more_aspects": has_more
    }

    if next_page:
        pagination["next_page"] = next_page
        pagination["instructions"] = f"To get {next_page} aspects, call again with aspect_priority='{next_page}'"

    return pagination


def estimate_response_size(response: dict) -> int:
    """
    Estimate JSON response size in bytes.

    Args:
        response: Response dictionary

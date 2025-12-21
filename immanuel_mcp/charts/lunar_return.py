"""Lunar Return Chart Generation

A lunar return occurs when the Moon returns to its exact natal position,
happening approximately every 27-28 days. This is a monthly predictive
technique showing themes and energies for the coming month.

Since the Immanuel library doesn't have a built-in LunarReturn class,
this module implements custom logic to:
1. Calculate the natal Moon's position
2. Find when the transiting Moon returns to that position
3. Generate a chart for that moment
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from immanuel import charts
from immanuel.classes.serialize import ToJSON
from compact_serializer import CompactJSONSerializer

# Import from parent package
import sys
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from immanuel_mcp.utils.coordinates import parse_coordinate
from immanuel_mcp.utils.subjects import create_subject
from immanuel_mcp.utils.errors import handle_chart_error, validate_inputs
from immanuel_server import mcp  # Import the MCP server instance

logger = logging.getLogger(__name__)


def find_lunar_return_date(
    natal_moon_longitude: float,
    year: int,
    month: int,
    lat: float,
    lon: float,
    timezone: str = None
) -> datetime:
    """
    Find the date when the Moon returns to its natal position within a given month.

    Args:
        natal_moon_longitude: The natal Moon's ecliptic longitude in degrees
        year: The year to search for the lunar return
        month: The month to search for the lunar return (1-12)
        lat: Latitude for the chart
        lon: Longitude for the chart
        timezone: Optional IANA timezone

    Returns:
        datetime object for the lunar return moment

    Raises:
        ValueError: If no lunar return is found in the specified month
    """
    # Start at the beginning of the month
    start_date = datetime(year, month, 1, 0, 0, 0)

    # End at the last day of the month
    if month == 12:
        end_date = datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end_date = datetime(year, month + 1, 1, 0, 0, 0)

    # Check every 6 hours for Moon's position
    # Moon moves ~13 degrees per day, so 6-hour intervals give us ~3.25 degrees resolution
    current_date = start_date
    prev_moon_lon = None

    while current_date < end_date:
        # Create a subject for this moment
        subject = create_subject(
            current_date.isoformat(),
            lat,
            lon,
            timezone
        )

        # Get Moon's current position
        transit_chart = charts.Natal(subject)
        moon = transit_chart.objects.get(4000002)  # Moon's index

        if moon is None:
            current_date += timedelta(hours=6)
            continue

        current_moon_lon = moon.longitude.raw

        # Check if we've crossed the natal position
        if prev_moon_lon is not None:
            # Handle 360-degree wrap-around
            natal_normalized = natal_moon_longitude % 360

            # Check if we crossed the natal position
            crossed = False
            if prev_moon_lon < natal_normalized <= current_moon_lon:
                crossed = True
            elif prev_moon_lon > current_moon_lon:  # Wrapped around 360 degrees
                if prev_moon_lon < natal_normalized or natal_normalized <= current_moon_lon:
                    crossed = True

            if crossed:
                # Found the approximate time - refine to within 1 hour
                return refine_lunar_return_time(
                    natal_moon_longitude,
                    current_date - timedelta(hours=6),
                    current_date,
                    lat,
                    lon,
                    timezone
                )

        prev_moon_lon = current_moon_lon
        current_date += timedelta(hours=6)

    raise ValueError(f"No lunar return found in {year}-{month:02d}")


def refine_lunar_return_time(
    natal_moon_longitude: float,
    start: datetime,
    end: datetime,
    lat: float,
    lon: float,
    timezone: str = None,
    tolerance: float = 0.1
) -> datetime:
    """
    Refine the lunar return time to within a small tolerance.

    Uses binary search to find the exact moment the Moon returns.

    Args:
        natal_moon_longitude: The natal Moon's ecliptic longitude
        start: Start of time range
        end: End of time range
        lat: Latitude
        lon: Longitude
        timezone: Optional IANA timezone
        tolerance: Acceptable difference in degrees (default 0.1)

    Returns:
        datetime object for the refined lunar return moment
    """
    while (end - start).total_seconds() > 60:  # Refine to within 1 minute
        mid = start + (end - start) / 2

        subject = create_subject(
            mid.isoformat(),
            lat,
            lon,
            timezone
        )

        transit_chart = charts.Natal(subject)
        moon = transit_chart.objects.get(4000002)

        if moon is None:
            return mid  # Best we can do

        moon_lon = moon.longitude.raw
        natal_normalized = natal_moon_longitude % 360

        diff = abs(moon_lon - natal_normalized)
        if diff > 180:
            diff = 360 - diff

        if diff < tolerance:
            return mid

        # Determine which half to search
        # Check if we need to go forward or backward in time
        future_subject = create_subject(
            (mid + timedelta(hours=1)).isoformat(),
            lat,
            lon,
            timezone
        )
        future_chart = charts.Natal(future_subject)
        future_moon = future_chart.objects.get(4000002)

        if future_moon:
            future_diff = abs(future_moon.longitude.raw - natal_normalized)
            if future_diff > 180:
                future_diff = 360 - future_diff

            if future_diff < diff:
                start = mid
            else:
                end = mid
        else:
            return mid

    return start + (end - start) / 2


@mcp.tool()
def generate_lunar_return_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    return_year: int,
    return_month: int,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Calculate lunar return chart for specified month/year.

    A lunar return occurs when the Moon returns to its natal position,
    happening approximately every 27-28 days. This is a monthly predictive
    technique showing themes and energies for the coming month.

    Args:
        date_time: Birth date and time in ISO format (e.g., '1990-01-15 14:30:00')
        latitude: Birth location latitude (e.g., '32n43' or '32.71')
        longitude: Birth location longitude (e.g., '117w09' or '-117.15')
        return_year: Year for the lunar return (e.g., 2025)
        return_month: Month for the lunar return (1-12)
        timezone: Optional IANA timezone name (e.g., 'America/New_York')

    Returns:
        Full lunar return chart with all positions and aspects
    """
    try:
        logger.info(f"Generating lunar return chart for {date_time} at {latitude}, {longitude} for {return_year}-{return_month:02d}")

        # Validate inputs
        validate_inputs(date_time, latitude, longitude)

        if not 1 <= return_month <= 12:
            raise ValueError(f"Return month must be between 1 and 12. Got: {return_month}")
        if not 1900 <= return_year <= 2100:
            raise ValueError(f"Return year must be between 1900 and 2100. Got: {return_year}")

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        # Get natal Moon's position
        natal_subject = create_subject(date_time, lat, lon, timezone)
        natal_chart = charts.Natal(natal_subject)
        natal_moon = natal_chart.objects.get(4000002)  # Moon's index

        if natal_moon is None:
            raise ValueError("Could not calculate natal Moon position")

        natal_moon_longitude = natal_moon.longitude.raw

        # Find the lunar return date
        lunar_return_dt = find_lunar_return_date(
            natal_moon_longitude,
            return_year,
            return_month,
            lat,
            lon,
            timezone
        )

        # Generate chart for lunar return moment
        return_subject = create_subject(
            lunar_return_dt.isoformat(),
            lat,
            lon,
            timezone
        )
        lunar_return_chart = charts.Natal(return_subject)

        # Serialize to JSON
        result = json.loads(json.dumps(lunar_return_chart, cls=ToJSON))

        # Add metadata about the lunar return
        result['lunar_return_info'] = {
            'return_date': lunar_return_dt.isoformat(),
            'natal_moon_longitude': natal_moon_longitude,
            'return_year': return_year,
            'return_month': return_month
        }

        logger.info(f"Lunar return chart generated successfully for {lunar_return_dt.isoformat()}")
        return result

    except Exception as e:
        logger.error(f"Error generating lunar return chart: {str(e)}")
        return handle_chart_error(e)


@mcp.tool()
def generate_compact_lunar_return_chart(
    date_time: str,
    latitude: str,
    longitude: str,
    return_year: int,
    return_month: int,
    timezone: str = None
) -> Dict[str, Any]:
    """
    Calculate compact lunar return chart with optimized response.

    Same as generate_lunar_return_chart but with streamlined output:
    - Major objects only (Sun through Pluto, angles)
    - Major aspects only (conjunction, opposition, square, trine, sextile)
    - Optimized position format (84.9% smaller)

    Args:
        date_time: Birth date and time in ISO format (e.g., '1990-01-15 14:30:00')
        latitude: Birth location latitude (e.g., '32n43' or '32.71')
        longitude: Birth location longitude (e.g., '117w09' or '-117.15')
        return_year: Year for the lunar return (e.g., 2025)
        return_month: Month for the lunar return (1-12)
        timezone: Optional IANA timezone name (e.g., 'America/New_York')

    Returns:
        Compact lunar return chart optimized for LLM processing
    """
    try:
        logger.info(f"Generating compact lunar return chart for {date_time} at {latitude}, {longitude} for {return_year}-{return_month:02d}")

        # Validate inputs
        validate_inputs(date_time, latitude, longitude)

        if not 1 <= return_month <= 12:
            raise ValueError(f"Return month must be between 1 and 12. Got: {return_month}")
        if not 1900 <= return_year <= 2100:
            raise ValueError(f"Return year must be between 1900 and 2100. Got: {return_year}")

        # Parse coordinates
        lat = parse_coordinate(latitude, is_latitude=True)
        lon = parse_coordinate(longitude, is_latitude=False)

        # Get natal Moon's position
        natal_subject = create_subject(date_time, lat, lon, timezone)
        natal_chart = charts.Natal(natal_subject)
        natal_moon = natal_chart.objects.get(4000002)  # Moon's index

        if natal_moon is None:
            raise ValueError("Could not calculate natal Moon position")

        natal_moon_longitude = natal_moon.longitude.raw

        # Find the lunar return date
        lunar_return_dt = find_lunar_return_date(
            natal_moon_longitude,
            return_year,
            return_month,
            lat,
            lon,
            timezone
        )

        # Generate chart for lunar return moment
        return_subject = create_subject(
            lunar_return_dt.isoformat(),
            lat,
            lon,
            timezone
        )
        lunar_return_chart = charts.Natal(return_subject)

        # Serialize to JSON using compact serializer
        result = json.loads(json.dumps(lunar_return_chart, cls=CompactJSONSerializer))

        # Add metadata about the lunar return
        result['lunar_return_info'] = {
            'return_date': lunar_return_dt.isoformat(),
            'natal_moon_longitude': natal_moon_longitude,
            'return_year': return_year,
            'return_month': return_month
        }

        logger.info(f"Compact lunar return chart generated successfully for {lunar_return_dt.isoformat()}")
        return result

    except Exception as e:
        logger.error(f"Error generating compact lunar return chart: {str(e)}")
        return handle_chart_error(e)

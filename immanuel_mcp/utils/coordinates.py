"""parse_coordinate function"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_coordinate(coord: str, is_latitude: bool = True) -> float:
    """
    Parse coordinate strings in various formats.
    
    Args:
        coord: Coordinate string in various formats
        is_latitude: Whether this is a latitude (for validation)
    
    Returns:
        Decimal coordinate value
        
    Raises:
        ValueError: If coordinate format is invalid or out of range
        
    Examples:
        >>> parse_coordinate("32n43")
        32.71666666666667
        >>> parse_coordinate("-117.15")
        -117.15
        >>> parse_coordinate("51°23'30\"N")
        51.39166666666667
    """
    coord_type = "latitude" if is_latitude else "longitude"
    original_coord = coord  # Keep original for logging
    coord = coord.strip().replace('°', ' ').replace("'", ' ').replace('"', ' ')

    logger.debug(f"Parsing {coord_type}: original='{original_coord}', cleaned='{coord}'")

    # Check for DMS pattern FIRST (before float conversion) to avoid scientific notation issues.
    # Matches formats like: 32n43, 32N43, 32n43'30 and 117w09, 117w09'30 (the
    # delimiters were normalized to spaces above). Minutes and seconds are
    # limited to two digits each and seconds must be delimiter-separated:
    # matching on a digit-fused string let the minutes group swallow the
    # seconds (117w09'30 parsed as 117 deg 930 min = -132.5 instead of -117.158).
    pattern = r'^(\d{1,3})\s*([nsewNSEW])\s*(\d{1,2})(?:\s+(\d{1,2}(?:\.\d+)?))?\s*$'
    match = re.match(pattern, coord)

    if match:
        degrees = int(match.group(1))
        direction = match.group(2).lower()
        minutes = int(match.group(3)) if match.group(3) else 0
        seconds = float(match.group(4)) if match.group(4) else 0

        if minutes >= 60 or seconds >= 60:
            raise ValueError(
                f"Invalid {coord_type}: '{original_coord}' has minutes or seconds >= 60"
            )

        logger.debug(f"Matched DMS pattern: {degrees}° {minutes}' {seconds}\" {direction.upper()}")

        decimal = degrees + (minutes / 60) + (seconds / 3600)

        # Apply sign based on direction
        if direction in ['s', 'w']:
            decimal = -decimal

        logger.debug(f"Converted to decimal: {decimal}")

        # Validate range
        if is_latitude and not -90 <= decimal <= 90:
            error_msg = f"Latitude must be between -90 and 90 degrees. Got: {decimal}"
            logger.error(f"DMS range validation failed: {error_msg}")
            raise ValueError(error_msg)
        elif not is_latitude and not -180 <= decimal <= 180:
            error_msg = f"Longitude must be between -180 and 180 degrees. Got: {decimal}"
            logger.error(f"DMS range validation failed: {error_msg}")
            raise ValueError(error_msg)

        logger.debug(f"Successfully parsed and validated {coord_type}: {decimal}")
        return decimal
    
    # Try space-separated format: "32 43 30 N" or "32 43 N"
    logger.debug(f"DMS pattern failed, trying space-separated format")
    parts = coord.upper().split()
    if len(parts) >= 3 and parts[-1] in ['N', 'S', 'E', 'W']:
        try:
            degrees = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 2 else 0
            seconds = int(parts[2]) if len(parts) > 3 else 0
            direction = parts[-1].lower()

            if minutes >= 60 or seconds >= 60:
                raise ValueError(
                    f"Invalid {coord_type}: '{original_coord}' has minutes or seconds >= 60"
                )

            logger.debug(f"Matched space-separated: {degrees}° {minutes}' {seconds}\" {direction.upper()}")

            decimal = degrees + (minutes / 60) + (seconds / 3600)
            if direction in ['s', 'w']:
                decimal = -decimal

            logger.debug(f"Converted to decimal: {decimal}")

            # Validate range
            if is_latitude and not -90 <= decimal <= 90:
                error_msg = f"Latitude must be between -90 and 90 degrees. Got: {decimal}"
                logger.error(f"Space-separated range validation failed: {error_msg}")
                raise ValueError(error_msg)
            elif not is_latitude and not -180 <= decimal <= 180:
                error_msg = f"Longitude must be between -180 and 180 degrees. Got: {decimal}"
                logger.error(f"Space-separated range validation failed: {error_msg}")
                raise ValueError(error_msg)

            logger.debug(f"Successfully parsed and validated {coord_type}: {decimal}")
            return decimal
        except (ValueError, IndexError) as e:
            logger.debug(f"Space-separated parsing failed: {e}")
            pass

    # Finally, try parsing as decimal (after DMS to avoid scientific notation confusion)
    logger.debug(f"Space-separated format failed, trying decimal format")
    try:
        result = float(coord)
        logger.debug(f"Successfully parsed as decimal: {result}")

        # Validate range
        if is_latitude and not -90 <= result <= 90:
            error_msg = f"Latitude must be between -90 and 90 degrees. Got: {result}"
            logger.error(f"Decimal range validation failed: {error_msg}")
            raise ValueError(error_msg)
        elif not is_latitude and not -180 <= result <= 180:
            error_msg = f"Longitude must be between -180 and 180 degrees. Got: {result}"
            logger.error(f"Decimal range validation failed: {error_msg}")
            raise ValueError(error_msg)

        logger.debug(f"Successfully validated {coord_type}: {result}")
        return result
    except ValueError as e:
        if "must be between" in str(e):
            raise  # Re-raise range validation errors
        logger.debug(f"Decimal parsing failed: {e}")

    error_msg = (f"Invalid {coord_type} format: '{original_coord}'. "
                f"Supported formats: decimal (32.71 or -117.15), "
                f"DMS with direction (32n43 or 117w09), "
                f"or space-separated (32 43 30 N)")
    logger.error(error_msg)
    raise ValueError(error_msg)

"""
utils/haversine.py — Haversine distance & speed calculations.

Used in stream processor to compute:
- Distance between GPS points
- Speed (km/h)
- Heading (direction in degrees)
"""

import math
from typing import Tuple


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS points using Haversine formula.

    Args:
        lat1, lon1: Starting point (latitude, longitude)
        lat2, lon2: Ending point (latitude, longitude)

    Returns:
        Distance in kilometers
    """
    R = 6371.0  # Earth radius in km

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def compute_speed(
    lat1: float,
    lon1: float,
    timestamp1: float,
    lat2: float,
    lon2: float,
    timestamp2: float,
) -> float:
    """
    Calculate speed between two GPS points.

    Args:
        lat1, lon1: Previous location
        timestamp1: Previous timestamp (unix seconds)
        lat2, lon2: Current location
        timestamp2: Current timestamp (unix seconds)

    Returns:
        Speed in km/h
    """
    if timestamp2 <= timestamp1:
        return 0.0

    distance_km = haversine_km(lat1, lon1, lat2, lon2)
    time_hours = (timestamp2 - timestamp1) / 3600.0

    if time_hours <= 0:
        return 0.0

    return distance_km / time_hours


def compute_heading(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing (heading) between two points.

    Returns:
        Heading in degrees (0-360), where:
        - 0 = North
        - 90 = East
        - 180 = South
        - 270 = West
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad

    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)

    bearing = math.atan2(y, x)
    bearing_degrees = math.degrees(bearing)

    # Normalize to 0-360
    return (bearing_degrees + 360) % 360


def distance_to_destination(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance to destination (same as haversine_km).

    Args:
        lat1, lon1: Current position
        lat2, lon2: Destination

    Returns:
        Distance in kilometers
    """
    return haversine_km(lat1, lon1, lat2, lon2)

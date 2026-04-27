"""
utils/interpolation.py — GPS data interpolation & ETA calculation.

Used in stream processor to:
- Smooth GPS coordinates (linear interpolation between points)
- Calculate ETA to destination
"""

import math
from typing import Tuple

from app.utils.haversine import distance_to_destination


def interpolate(lat1: float, lon1: float, lat2: float, lon2: float, t: float = 0.5) -> Tuple[float, float]:
    """
    Linear interpolation between two GPS points.

    This creates a smooth path between two GPS readings, reducing jitter.

    Args:
        lat1, lon1: Starting point
        lat2, lon2: Ending point
        t: Interpolation factor (0.0 = start, 0.5 = midpoint, 1.0 = end)

    Returns:
        Interpolated (lat, lon)
    """
    smooth_lat = lat1 + (lat2 - lat1) * t
    smooth_lon = lon1 + (lon2 - lon1) * t

    return smooth_lat, smooth_lon


def compute_eta_minutes(
    current_lat: float,
    current_lon: float,
    dest_lat: float,
    dest_lon: float,
    speed_kmh: float,
) -> int:
    """
    Compute estimated time to destination (ETA).

    🔴 Called on every GPS update, live ETA.

    Args:
        current_lat, current_lon: Current position
        dest_lat, dest_lon: Destination
        speed_kmh: Current speed in km/h

    Returns:
        ETA in minutes (integer), minimum 1 minute
    """
    if speed_kmh < 0.5:
        # Stationary or very slow — estimate high ETA
        return 999

    distance_km = distance_to_destination(current_lat, current_lon, dest_lat, dest_lon)

    # time_hours = distance / speed
    # time_minutes = time_hours * 60
    eta_minutes = (distance_km / speed_kmh) * 60

    # Minimum 1 minute
    return max(1, int(round(eta_minutes)))


def estimate_delivery_delay(
    eta_minutes: int,
    promised_delivery_at,  # datetime
    current_time,  # datetime
) -> int:
    """
    Estimate delivery delay (minutes behind SLA).

    Args:
        eta_minutes: Estimated time to destination
        promised_delivery_at: Promised delivery datetime
        current_time: Current datetime

    Returns:
        Minutes delayed (0 if on time, positive if late)
    """
    if not promised_delivery_at:
        return 0

    # Minutes until promised delivery
    minutes_until_sla = (promised_delivery_at - current_time).total_seconds() / 60

    # Delay = ETA - minutes_until_sla
    # If ETA > minutes_until_sla, we're behind
    delay = max(0, int(eta_minutes - minutes_until_sla))

    return delay


def calculate_waypoints(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    steps: int = 10,
) -> list:
    """
    Generate intermediate waypoints between two GPS points.

    Useful for smooth map animations.

    Args:
        lat1, lon1: Start
        lat2, lon2: End
        steps: Number of waypoints to generate

    Returns:
        List of (lat, lon) tuples
    """
    waypoints = []
    for i in range(steps + 1):
        t = i / steps
        lat, lon = interpolate(lat1, lon1, lat2, lon2, t)
        waypoints.append((lat, lon))
    return waypoints

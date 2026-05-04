"""
Core realtime simulation loop.
"""

import asyncio
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.application.services.routing_engine import routing_graph
from app.db import get_database
from app.infrastructure.repositories import ShipperRepository, TrackingEventRepository

logger = logging.getLogger(__name__)

WAREHOUSE_LAT = 10.8051
WAREHOUSE_LON = 106.7144
WAREHOUSE_ID = "WH-BINHthanh"

LAT_MIN, LAT_MAX = 10.65, 10.90
LON_MIN, LON_MAX = 106.55, 106.85

SHIPPER_COUNT = 30
GPS_INTERVAL = 1.0


# ── Incident default configs theo TONGQUAN.md mục 19.4 ──
INCIDENT_DEFAULTS = {
    "TRAFFIC_JAM": {"severity": "MEDIUM", "estimated_delay": 15, "action": "Đang tìm đường thay thế..."},
    "HEAVY_RAIN": {"severity": "HIGH", "estimated_delay": 30, "action": "Đánh giá mức mưa, có thể dừng giao"},
    "CUSTOMER_ABSENT": {"severity": "LOW", "estimated_delay": 10, "action": "Bỏ qua, giao đơn tiếp theo, thử lại sau"},
    "VEHICLE_BREAKDOWN": {"severity": "HIGH", "estimated_delay": 45, "action": "Chờ sửa xe. Timeout 60p sẽ reassign"},
    "LOST_CONNECTION": {"severity": "MEDIUM", "estimated_delay": 20, "action": "Hệ thống đang ping lại GPS mỗi 30s"},
}

# ── Auto-detection thresholds (Section 22) ──
SLOW_SPEED_THRESHOLD = 5.0       # km/h
SLOW_SPEED_DURATION = 180        # 3 minutes in seconds (ticks)
SPEED_DROP_PERCENT = 0.40        # 40% sudden drop → suspect rain
GPS_LOST_TIMEOUT = 120           # 2 minutes no ping
STOP_AT_DELIVERY_TIMEOUT = 600   # 10 minutes stopped at delivery → customer absent
STOP_NOT_DELIVERY_TIMEOUT = 900  # 15 minutes stopped not at delivery → vehicle breakdown
INCIDENT_REASSIGN_TIMEOUT = 3600 # 60 minutes → reassign (Fix #4)
CUSTOMER_ABSENT_MAX_RETRIES = 2  # Max 2 retries (Fix #3)

# ── Graph routing configuration ──
ROAD_GRAPH_NODE_IDS = list(routing_graph.nodes.keys())

# ── Rain severity levels (Fix #6) ──
RAIN_LEVELS = {
    "LIGHT":  {"factor": 1.2, "severity": "LOW",    "action": "Mưa nhẹ, giảm tốc nhẹ"},
    "MEDIUM": {"factor": 1.4, "severity": "MEDIUM", "action": "Mưa vừa, giảm tốc đáng kể"},
    "HEAVY":  {"factor": 2.0, "severity": "HIGH",   "action": "Mưa nặng, có thể dừng giao"},
}


@dataclass
class VirtualShipper:
    shipper_id: str
    lat: float
    lon: float
    speed_kmh: float = 35.0
    heading: float = 0.0
    status: str = "IDLE"
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    order_id: Optional[str] = None
    # ETA tracking
    eta_minutes: Optional[float] = None
    # Auto-detection counters
    slow_ticks: int = 0         # consecutive ticks with speed < 5 km/h
    no_gps_ticks: int = 0       # consecutive ticks without GPS
    stop_ticks: int = 0         # consecutive ticks with speed = 0
    incident_ticks: int = 0     # ticks since incident started
    prev_speed_kmh: float = 35.0  # previous tick speed for sudden drop
    has_incident: bool = False
    incident_type: Optional[str] = None
    rain_level: Optional[str] = None      # LIGHT, MEDIUM, HEAVY
    customer_absent_retries: int = 0      # Fix #3: max 2 retries
    # Graph route waypoints: list of (lat, lon) tuples along road graph
    route_waypoints: List[Tuple[float, float]] = field(default_factory=list)
    route_index: int = 0                  # current waypoint index
    route_polyline: List[List[float]] = field(default_factory=list)  # [[lat,lon],...] for frontend
    # Pending orders queue: [(order_id, dest_lat, dest_lon), ...] cho khách vắng retry
    pending_orders: List[dict] = field(default_factory=list)  # [{"order_id": "...", "dest_lat": ..., "dest_lon": ..., "attempt": 1}, ...]

    def distance_to(self, lat: float, lon: float) -> float:
        """Haversine distance in km."""
        radius_km = 6371.0
        dlat = math.radians(lat - self.lat)
        dlon = math.radians(lon - self.lon)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(self.lat))
            * math.cos(math.radians(lat))
            * math.sin(dlon / 2) ** 2
        )
        return radius_km * 2 * math.asin(math.sqrt(a))

    def has_arrived(self) -> bool:
        if self.target_lat is None or self.target_lon is None:
            return False
        return self.distance_to(self.target_lat, self.target_lon) < 0.3

    def set_route(self, waypoints: List[Tuple[float, float]]) -> None:
        """Set graph route waypoints for road-following movement.

        The route is produced by RoutingGraph/A* and already snapped to graph
        nodes. Snap the marker to the first node and continue edge-by-edge.
        """
        if not waypoints:
            self.route_waypoints = []
            self.route_index = 0
            self.route_polyline = []
            return

        first_lat, first_lon = waypoints[0]
        self.lat = first_lat
        self.lon = first_lon
        self.route_waypoints = waypoints
        self.route_index = 1 if len(waypoints) > 1 else 0
        self.route_polyline = [[lat, lon] for lat, lon in waypoints]
        logger.info("[Route] %s snapped to graph node and received %d waypoints", self.shipper_id, len(waypoints))

    def move(self, dt: float = 1.0) -> None:
        """Move shipper along graph route waypoints (follows road edges)."""
        # If has route waypoints → follow them along the road
        if self.route_waypoints and self.route_index < len(self.route_waypoints):
            self.speed_kmh = 40.0
            speed_ms = self.speed_kmh / 3.6
            remaining_dist_m = speed_ms * dt

            while remaining_dist_m > 0 and self.route_index < len(self.route_waypoints):
                wp_lat, wp_lon = self.route_waypoints[self.route_index]
                dy = wp_lat - self.lat
                dx = wp_lon - self.lon
                dist_to_wp_deg = math.sqrt(dx**2 + dy**2)
                dist_to_wp_m = dist_to_wp_deg * 111_320

                # Calculate heading toward current waypoint
                if dist_to_wp_deg > 0.000001:
                    target_heading = math.degrees(math.atan2(dx, dy)) % 360
                    # Normalize angle delta to [-180, 180] to avoid sudden flips/jumps
                    delta = (target_heading - self.heading + 180) % 360 - 180
                    self.heading = (self.heading + delta * 0.35) % 360

                if dist_to_wp_m <= remaining_dist_m:
                    # Arrive at this waypoint, move to next
                    self.lat = wp_lat
                    self.lon = wp_lon
                    remaining_dist_m -= dist_to_wp_m
                    self.route_index += 1
                else:
                    # Move partially toward waypoint
                    fraction = remaining_dist_m / dist_to_wp_m if dist_to_wp_m > 0 else 0
                    self.lat += dy * fraction
                    self.lon += dx * fraction
                    remaining_dist_m = 0

            # If all waypoints consumed, clear route
            if self.route_index >= len(self.route_waypoints):
                self.route_waypoints = []
                self.route_index = 0
            return

        # No road route available: do not use straight-line fallback.
        #
        # A straight-line fallback makes markers cut through buildings/blocks
        # whenever OSRM is unavailable or a route has not finished loading.
        # Keep the shipper still until a valid road-following route is assigned.
        if self.target_lat is not None and self.target_lon is not None:
            self.speed_kmh = 0.0
            return

        # No target: keep IDLE shippers stationary.
        #
        # The previous random-walk logic moved markers in arbitrary straight
        # lines, so they visibly crossed buildings/blocks on the map. A shipper
        # should only move after receiving an OSRM route from dispatch/delivery.
        self.speed_kmh = 0.0
        return

    def calculate_eta(self) -> Optional[float]:
        """Calculate ETA in minutes to target."""
        if self.target_lat is None or self.target_lon is None:
            return None
        dist_km = self.distance_to(self.target_lat, self.target_lon)
        if self.speed_kmh > 0:
            return round((dist_km / self.speed_kmh) * 60, 1)
        return None

    def to_ws_payload(self) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()
        self.eta_minutes = self.calculate_eta()
        return {
            "type": "gps_update",
            "shipper_id": self.shipper_id,
            "name": self.shipper_id,
            "phone_number": "N/A",
            "vehicle_type": "motorcycle",
            "vehicle_plate": f"SIM-{self.shipper_id[-3:]}",
            "lat": round(self.lat, 6),
            "lon": round(self.lon, 6),
            "speed_kmh": round(self.speed_kmh, 1),
            "heading": round(self.heading, 1),
            "status": self.status,
            "signal_status": "OFFLINE" if self.status in ("LOST_CONNECTION", "OFFLINE") else "ONLINE",
            "order_id": self.order_id,
            "eta_minutes": self.eta_minutes,
            "has_incident": self.has_incident,
            "incident_type": self.incident_type,
            "customer_absent_retries": self.customer_absent_retries,
            "timestamp": timestamp,
            "route_polyline": self.route_polyline if self.route_polyline else None,
        }


class SimulationEngine:
    """Singleton simulation engine initialized at FastAPI startup."""

    def __init__(self):
        self.shippers: Dict[str, VirtualShipper] = {}
        self.phase: str = "IDLE"
        self.dispatched_ids: List[str] = []
        self.running = False
        self.ws_manager = None
        self._tick = 0
        self._arrived_at_warehouse: List[str] = []
        self._delivery_targets: Dict[str, dict] = {}
        # Orders tracking for customer absent logic
        self._orders: Dict[str, dict] = {}  # order_id -> {shipper_id, dest_lat, dest_lon, status, attempt}
        self._init_shippers()

    def _init_shippers(self) -> None:
        """Create virtual shippers on road-graph nodes around HCMC."""
        self.shippers = {}
        spawn_node_ids = [node_id for node_id in ROAD_GRAPH_NODE_IDS if node_id != "WH"]
        for i in range(1, SHIPPER_COUNT + 1):
            shipper_id = f"SHP-{i:03d}"
            node_id = random.choice(spawn_node_ids)
            lat, lon = routing_graph.get_node_coordinate(node_id)
            self.shippers[shipper_id] = VirtualShipper(
                shipper_id=shipper_id,
                lat=lat,
                lon=lon,
                speed_kmh=random.uniform(20, 45),
                heading=random.uniform(0, 360),
            )
        logger.info("[SimEngine] Initialized %s shippers on graph nodes", SHIPPER_COUNT)

    def get_all_shippers_state(self) -> List[dict]:
        """Return current in-memory snapshot in frontend format."""
        return [shipper.to_ws_payload() for shipper in self.shippers.values()]

    def get_nearest_to_warehouse(self, top_n: int = 3) -> List[dict]:
        """Return top idle shippers nearest to the warehouse."""
        candidates = [
            (shipper.distance_to(WAREHOUSE_LAT, WAREHOUSE_LON), shipper)
            for shipper in self.shippers.values()
            if shipper.status == "IDLE"
        ]
        candidates.sort(key=lambda item: item[0])
        return [
            {
                "shipper_id": shipper.shipper_id,
                "lat": round(shipper.lat, 6),
                "lon": round(shipper.lon, 6),
                "distance_km": round(distance_km, 2),
            }
            for distance_km, shipper in candidates[:top_n]
        ]

    @staticmethod
    async def _fetch_graph_route(
        from_lat: float, from_lon: float, to_lat: float, to_lon: float
    ) -> List[Tuple[float, float]]:
        """Fetch road-following route from in-memory RoutingGraph/A*."""
        waypoints = routing_graph.find_route_waypoints(from_lat, from_lon, to_lat, to_lon)
        if not waypoints:
            logger.warning(
                "[GraphRoute] No route found from (%.4f,%.4f) to (%.4f,%.4f)",
                from_lat,
                from_lon,
                to_lat,
                to_lon,
            )
            return []

        logger.info("[GraphRoute] Route fetched: %d waypoints", len(waypoints))
        return waypoints

    def find_nearby_orders(self, shipper_id: str, exclude_order_id: str = None, radius_km: float = 3.0) -> List[dict]:
        """Tìm các đơn hàng khác gần shipper hiện tại (đối với khách vắng).

        According to TONGQUAN.md mục 19.4:
        - Nếu có đơn gần 3km → giao đơn gần trước
        - Nếu không → để đơn failed cuối
        """
        shipper = self.shippers.get(shipper_id)
        if not shipper:
            return []

        nearby = []
        for order_id, order_info in self._orders.items():
            # Skip nếu đây là order đang failed (exclude_order_id)
            if exclude_order_id and order_id == exclude_order_id:
                continue
            # Skip nếu order này đang được giao bởi shipper khác
            if order_info.get("shipper_id") and order_info["shipper_id"] != shipper_id:
                continue
            # Skip nếu order đã hoàn thành
            if order_info.get("status") in ("DELIVERED", "FAILED"):
                continue

            dest_lat = order_info.get("dest_lat")
            dest_lon = order_info.get("dest_lon")
            if dest_lat is None or dest_lon is None:
                continue

            dist_km = shipper.distance_to(dest_lat, dest_lon)
            if dist_km <= radius_km:
                nearby.append({
                    "order_id": order_id,
                    "dest_lat": dest_lat,
                    "dest_lon": dest_lon,
                    "distance_km": dist_km,
                    "status": order_info.get("status"),
                })

        # Sort by distance
        nearby.sort(key=lambda x: x["distance_km"])
        return nearby

    async def dispatch_to_warehouse(self, shipper_ids: List[str]) -> None:
        """Command shippers to head to the warehouse with graph road routes."""
        self.dispatched_ids = shipper_ids
        self._arrived_at_warehouse = []
        self.phase = "DISPATCHING"

        for shipper_id in shipper_ids:
            shipper = self.shippers.get(shipper_id)
            if shipper:
                shipper.status = "HEADING_TO_WAREHOUSE"
                shipper.target_lat = WAREHOUSE_LAT
                shipper.target_lon = WAREHOUSE_LON
                waypoints = await self._fetch_graph_route(
                    shipper.lat, shipper.lon, WAREHOUSE_LAT, WAREHOUSE_LON
                )
                if waypoints:
                    shipper.set_route(waypoints)

        logger.info("[SimEngine] Dispatched %s to warehouse (graph routes)", shipper_ids)

    async def set_delivery_target(self, shipper_id: str, dest_lat: float, dest_lon: float, order_id: str) -> None:
        """Command a shipper to start delivery with graph road route."""
        shipper = self.shippers.get(shipper_id)
        if shipper:
            shipper.status = "DELIVERING"
            shipper.target_lat = dest_lat
            shipper.target_lon = dest_lon
            shipper.order_id = order_id
            self._delivery_targets[shipper_id] = {
                "dest_lat": dest_lat,
                "dest_lon": dest_lon,
            }
            # Track order in memory
            self._orders[order_id] = {
                "shipper_id": shipper_id,
                "dest_lat": dest_lat,
                "dest_lon": dest_lon,
                "status": "IN_TRANSIT",
                "attempt": 1,  # Lần thứ 1 giao
            }
            self.phase = "DELIVERING"
            # Fetch graph route for road-following
            waypoints = await self._fetch_graph_route(
                shipper.lat, shipper.lon, dest_lat, dest_lon
            )
            if waypoints:
                shipper.set_route(waypoints)

    def apply_incident(self, shipper_id: str, incident_type: str, rain_level: str = "MEDIUM") -> dict:
        """Apply an incident to a shipper — theo TONGQUAN.md mục 19.4."""
        shipper = self.shippers.get(shipper_id)
        if not shipper:
            return {"error": "Shipper not found"}

        defaults = INCIDENT_DEFAULTS.get(incident_type, {"severity": "MEDIUM", "estimated_delay": 15, "action": "Đang xử lý..."})
        shipper.has_incident = True
        shipper.incident_type = incident_type
        shipper.incident_ticks = 0

        if incident_type == "VEHICLE_BREAKDOWN":
            shipper.status = "VEHICLE_BREAKDOWN"
            shipper.speed_kmh = 0
        elif incident_type == "LOST_CONNECTION":
            shipper.status = "LOST_CONNECTION"
        elif incident_type == "TRAFFIC_JAM":
            shipper.status = "DELAYED"
            shipper.speed_kmh = max(3, shipper.speed_kmh * 0.3)
        elif incident_type == "HEAVY_RAIN":
            # Fix #6: Rain 3 levels
            rain_cfg = RAIN_LEVELS.get(rain_level.upper(), RAIN_LEVELS["MEDIUM"])
            shipper.rain_level = rain_level.upper()
            shipper.status = "DELAYED"
            shipper.speed_kmh = max(2, shipper.speed_kmh / rain_cfg["factor"])
            defaults = {**defaults, "severity": rain_cfg["severity"], "action": rain_cfg["action"]}
        elif incident_type == "CUSTOMER_ABSENT":
            # Fix #3: Khách vắng - Max 2 retries theo TONGQUAN.md mục 19.4
            shipper.customer_absent_retries += 1
            current_order = shipper.order_id
            current_dest = (shipper.target_lat, shipper.target_lon)

            if shipper.customer_absent_retries >= CUSTOMER_ABSENT_MAX_RETRIES:
                # Lần 2 failed -> Đơn FAILED hoàn toàn, shipper về IDLE
                if current_order and current_order in self._orders:
                    self._orders[current_order]["status"] = "FAILED"
                shipper.status = "IDLE"
                shipper.target_lat = None
                shipper.target_lon = None
                shipper.order_id = None
                shipper.route_waypoints = []
                shipper.route_index = 0
                shipper.route_polyline = []
                shipper.pending_orders = []
                defaults = {**defaults, "action": f"Đã thử {CUSTOMER_ABSENT_MAX_RETRIES} lần. Đơn hàng FAILED, shipper về IDLE"}
                logger.info("[CustomerAbsent] %s FAILED after %d attempts, back to IDLE", current_order, shipper.customer_absent_retries)
            else:
                # Lần 1 failed -> Đơn DELIVERY_FAILED_ATTEMPT_1, tìm đơn gần 3km
                if current_order:
                    self._orders[current_order]["status"] = "DELIVERY_FAILED_ATTEMPT_1"
                    shipper.pending_orders.append({
                        "order_id": current_order,
                        "dest_lat": current_dest[0],
                        "dest_lon": current_dest[1],
                        "attempt": shipper.customer_absent_retries,
                    })

                # Tìm đơn khác gần 3km
                nearby = self.find_nearby_orders(shipper_id, exclude_order_id=current_order, radius_km=3.0)

                if nearby:
                    # Có đơn gần -> Giao đơn gần nhất
                    next_order = nearby[0]
                    order_id = next_order["order_id"]
                    dest_lat = next_order["dest_lat"]
                    dest_lon = next_order["dest_lon"]

                    shipper.status = "DELIVERING"
                    shipper.target_lat = dest_lat
                    shipper.target_lon = dest_lon
                    shipper.order_id = order_id
                    self._orders[order_id]["shipper_id"] = shipper_id
                    self._orders[order_id]["attempt"] = shipper.customer_absent_retries + 1

                    defaults = {**defaults, "action": f"Lần {shipper.customer_absent_retries} khách vắng. Tìm được đơn gần {next_order['distance_km']:.1f}km, đang giao"}
                    logger.info("[CustomerAbsent] %s -> Reroute to nearby order %s (%.2f km away)",
                               shipper_id, order_id, next_order["distance_km"])
                else:
                    # Không có đơn gần -> Shipper về IDLE, chờ assignment mới
                    shipper.status = "IDLE"
                    shipper.target_lat = None
                    shipper.target_lon = None
                    shipper.order_id = None
                    shipper.route_waypoints = []
                    shipper.route_index = 0
                    shipper.route_polyline = []

                    defaults = {**defaults, "action": f"Lần {shipper.customer_absent_retries} khách vắng. Không có đơn gần, chờ assignment mới"}
                    logger.info("[CustomerAbsent] %s -> No nearby orders found, waiting for new assignment", shipper_id)

        result = {
            "shipper_id": shipper_id,
            "incident_type": incident_type,
            "severity": defaults["severity"],
            "estimated_delay": defaults["estimated_delay"],
            "recommended_action": defaults["action"],
            "location": {"lat": shipper.lat, "lon": shipper.lon},
        }
        if incident_type == "HEAVY_RAIN":
            result["rain_level"] = shipper.rain_level
        return result

    def resolve_incident(self, shipper_id: str) -> dict:
        """Resolve an incident for a shipper."""
        shipper = self.shippers.get(shipper_id)
        if not shipper:
            return {"error": "Shipper not found"}
        shipper.has_incident = False
        shipper.incident_type = None
        shipper.incident_ticks = 0
        shipper.rain_level = None
        shipper.slow_ticks = 0
        shipper.stop_ticks = 0
        if shipper.order_id:
            shipper.status = "DELIVERING"
            shipper.speed_kmh = 35.0
        else:
            shipper.status = "IDLE"
            shipper.speed_kmh = 30.0
        return {"shipper_id": shipper_id, "status": shipper.status, "resolved": True}

    def get_fleet_stats(self) -> dict:
        """Fleet statistics — GET /stats/fleet."""
        status_counts = {}
        for s in self.shippers.values():
            status_counts[s.status] = status_counts.get(s.status, 0) + 1
        return {
            "total_shippers": len(self.shippers),
            "status_breakdown": status_counts,
            "active_incidents": sum(1 for s in self.shippers.values() if s.has_incident),
            "phase": self.phase,
        }

    def complete_simulation(self) -> None:
        """Reset all shippers to idle state."""
        self.phase = "COMPLETED"
        for shipper in self.shippers.values():
            shipper.status = "IDLE"
            shipper.target_lat = None
            shipper.target_lon = None
            shipper.order_id = None
        self.dispatched_ids = []
        self._arrived_at_warehouse = []
        self._delivery_targets = {}

    async def sync_all_to_mongo(self, clear_existing: bool = False) -> None:
        """Persist the current in-memory fleet state to MongoDB."""
        db = get_database()
        if db is None:
            return

        repo = ShipperRepository(db)
        if clear_existing:
            await db.shippers.delete_many({})

        snapshots = self.get_all_shippers_state()
        for shipper in snapshots:
            await repo.upsert_shipper_snapshot(shipper)

    async def run(self) -> None:
        """Main simulation loop running as a background task."""
        self.running = True
        logger.info("[SimEngine] Simulation loop started")

        from app.presentation.websocket.manager import ws_manager

        self.ws_manager = ws_manager
        await self.sync_all_to_mongo(clear_existing=True)

        while self.running:
            try:
                await self._tick_all()
            except Exception as exc:
                logger.exception("[SimEngine] Tick error: %s", exc)
            await asyncio.sleep(GPS_INTERVAL)

    async def _record_tracking_event(self, repo: TrackingEventRepository, shipper: dict) -> None:
        """Append a tracking event for the current GPS point."""
        timestamp = datetime.fromisoformat(shipper["timestamp"])
        await repo.append_event(
            {
                "shipper_id": shipper["shipper_id"],
                "lat": shipper["lat"],
                "lon": shipper["lon"],
                "smooth_lat": shipper["lat"],
                "smooth_lon": shipper["lon"],
                "speed_kmh": shipper["speed_kmh"],
                "heading": shipper["heading"],
                "distance_moved_km": 0.0,
                "order_id": shipper.get("order_id"),
                "eta_minutes": None,
                "delay_minutes": 0,
                "event_type": "LOCATION_UPDATE",
                "status_code": shipper["status"],
                "exception_code": None,
                "note": None,
                "timestamp": timestamp,
            }
        )

    async def _broadcast_system_alert(self, shipper: VirtualShipper, suspected: str) -> None:
        """Section 22: Broadcast system_alert when auto-detection suspects anomaly."""
        if self.ws_manager:
            await self.ws_manager.broadcast_clients({
                "type": "system_alert",
                "shipper_id": shipper.shipper_id,
                "suspected_incident": suspected,
                "message": f"Phát hiện bất thường: {suspected} cho {shipper.shipper_id}",
                "lat": round(shipper.lat, 6),
                "lon": round(shipper.lon, 6),
                "speed_kmh": round(shipper.speed_kmh, 1),
            })

    async def _broadcast_customer_notification(self, shipper: VirtualShipper, reason: str, delay_min: int) -> None:
        """Section 23: Notify customer about delay."""
        if self.ws_manager and shipper.order_id:
            eta = shipper.calculate_eta() or 0
            await self.ws_manager.broadcast_clients({
                "type": "customer_notification",
                "order_id": shipper.order_id,
                "shipper_id": shipper.shipper_id,
                "message": f"Đơn hàng của bạn bị delay ~{delay_min} phút do {reason}",
                "new_eta_minutes": round(eta + delay_min, 1),
                "reason": reason,
            })

    async def _broadcast_eta_updated(self, shipper: VirtualShipper, old_eta: float, new_eta: float) -> None:
        """Fix #10: eta_updated when ETA changes significantly (>2 min)."""
        if self.ws_manager:
            await self.ws_manager.broadcast_clients({
                "type": "eta_updated",
                "shipper_id": shipper.shipper_id,
                "old_eta_minutes": round(old_eta, 1),
                "new_eta_minutes": round(new_eta, 1),
                "delta_minutes": round(new_eta - old_eta, 1),
            })

    async def _auto_detect_incidents(self, shipper: VirtualShipper) -> None:
        """Section 22: Auto-detect anomalies each tick."""
        if shipper.has_incident:
            shipper.incident_ticks += 1
            # Fix #4: Vehicle breakdown 60-min timeout → reassign
            if shipper.incident_type == "VEHICLE_BREAKDOWN" and shipper.incident_ticks >= INCIDENT_REASSIGN_TIMEOUT:
                logger.info("[AutoDetect] %s VEHICLE_BREAKDOWN timeout 60 min → reassign", shipper.shipper_id)
                shipper.has_incident = False
                shipper.incident_type = None
                shipper.incident_ticks = 0
                shipper.status = "IDLE"
                shipper.speed_kmh = 0
                shipper.target_lat = None
                shipper.target_lon = None
                shipper.order_id = None
                if self.ws_manager:
                    await self.ws_manager.broadcast_clients({
                        "type": "incident_resolved",
                        "shipper_id": shipper.shipper_id,
                        "reason": "TIMEOUT_REASSIGN",
                        "message": f"{shipper.shipper_id} hư xe quá 60 phút, đơn cần reassign",
                    })
            return

        # 1. Speed < 5 km/h liên tục > 3 phút → suspect kẹt xe
        if shipper.speed_kmh < SLOW_SPEED_THRESHOLD and shipper.status in ("DELIVERING", "HEADING_TO_WAREHOUSE"):
            shipper.slow_ticks += 1
            if shipper.slow_ticks >= SLOW_SPEED_DURATION:
                shipper.slow_ticks = 0
                await self._broadcast_system_alert(shipper, "TRAFFIC_JAM")
        else:
            shipper.slow_ticks = 0

        # 2. Speed drops > 40% suddenly → suspect mưa lớn
        if shipper.prev_speed_kmh > 10 and shipper.speed_kmh < shipper.prev_speed_kmh * (1 - SPEED_DROP_PERCENT):
            await self._broadcast_system_alert(shipper, "HEAVY_RAIN")

        # 3. Speed = 0 liên tục > 15 phút (not at delivery point) → hư xe
        if shipper.speed_kmh < 0.5 and shipper.status not in ("AT_WAREHOUSE", "IDLE", "DELIVERED", "OFFLINE"):
            shipper.stop_ticks += 1
            at_delivery = shipper.target_lat is not None and shipper.distance_to(shipper.target_lat, shipper.target_lon) < 0.5
            if at_delivery and shipper.stop_ticks >= STOP_AT_DELIVERY_TIMEOUT:
                shipper.stop_ticks = 0
                await self._broadcast_system_alert(shipper, "CUSTOMER_ABSENT")
            elif not at_delivery and shipper.stop_ticks >= STOP_NOT_DELIVERY_TIMEOUT:
                shipper.stop_ticks = 0
                await self._broadcast_system_alert(shipper, "VEHICLE_BREAKDOWN")
        else:
            shipper.stop_ticks = 0

        shipper.prev_speed_kmh = shipper.speed_kmh

    async def _tick_all(self) -> None:
        """Process one simulation tick and persist the new state."""
        self._tick += 1
        snapshots: List[dict] = []
        db = get_database()
        shipper_repo = ShipperRepository(db) if db is not None else None
        tracking_repo = TrackingEventRepository(db) if db is not None else None

        for shipper_id, shipper in self.shippers.items():
            # Track old ETA for eta_updated event
            old_eta = shipper.calculate_eta()
            shipper.move(GPS_INTERVAL)
            # Auto-detection (Section 22)
            await self._auto_detect_incidents(shipper)
            # Check ETA change > 2 min → broadcast eta_updated
            new_eta = shipper.calculate_eta()
            if old_eta is not None and new_eta is not None and abs(new_eta - old_eta) > 2.0:
                await self._broadcast_eta_updated(shipper, old_eta, new_eta)

            if shipper.status == "HEADING_TO_WAREHOUSE" and shipper.has_arrived():
                shipper.status = "AT_WAREHOUSE"
                shipper.target_lat = None
                shipper.target_lon = None
                if shipper_id not in self._arrived_at_warehouse:
                    self._arrived_at_warehouse.append(shipper_id)
                    if self.ws_manager:
                        await self.ws_manager.broadcast_clients(
                            {
                                "type": "shipper_arrived",
                                "shipper_id": shipper_id,
                                "warehouse_id": WAREHOUSE_ID,
                                "all_dispatched": self.dispatched_ids,
                                "arrived_so_far": self._arrived_at_warehouse,
                            }
                        )
                    if set(self._arrived_at_warehouse) >= set(self.dispatched_ids):
                        self.phase = "WAITING_FOR_ORDER"
                        if self.ws_manager:
                            await self.ws_manager.broadcast_clients(
                                {
                                    "type": "all_arrived_at_warehouse",
                                    "shipper_ids": self.dispatched_ids,
                                }
                            )

            elif shipper.status == "DELIVERING" and shipper.has_arrived():
                delivery = self._delivery_targets.get(shipper_id, {})
                distance_km = math.dist(
                    [WAREHOUSE_LAT, WAREHOUSE_LON],
                    [delivery.get("dest_lat", WAREHOUSE_LAT), delivery.get("dest_lon", WAREHOUSE_LON)],
                ) * 111

                shipper.status = "DELIVERED"
                shipper.target_lat = None
                shipper.target_lon = None
                if shipper_repo:
                    await shipper_repo.increment_completed_orders(shipper_id, round(distance_km, 2))
                completed_order_id = shipper.order_id
                shipper.order_id = None

                if self.ws_manager:
                    await self.ws_manager.broadcast_clients(
                        {
                            "type": "delivery_completed",
                            "shipper_id": shipper_id,
                            "order_id": completed_order_id,
                        }
                    )

                delivering_done = all(
                    self.shippers[dispatched_id].status in ("DELIVERED", "AT_WAREHOUSE")
                    for dispatched_id in self.dispatched_ids
                    if dispatched_id in self.shippers
                )
                if delivering_done and self.phase == "DELIVERING":
                    self.phase = "COMPLETED"
                    if self.ws_manager:
                        await self.ws_manager.broadcast_clients({"type": "simulation_completed"})

            snapshot = shipper.to_ws_payload()
            snapshots.append(snapshot)

            if shipper_repo:
                await shipper_repo.upsert_shipper_snapshot(snapshot)
            if tracking_repo:
                await self._record_tracking_event(tracking_repo, snapshot)

        if self.ws_manager and snapshots:
            await self.ws_manager.broadcast_clients(
                {
                    "type": "bulk_gps_update",
                    "shippers": snapshots,
                    "phase": self.phase,
                    "tick": self._tick,
                }
            )


simulation_engine = SimulationEngine()

"""
Core realtime simulation loop.
"""

import asyncio
import logging
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

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

    def move(self, dt: float = 1.0) -> None:
        """Move shipper toward its target or in a random walk."""
        if self.target_lat is not None and self.target_lon is not None:
            dy = self.target_lat - self.lat
            dx = self.target_lon - self.lon
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0.0001:
                target_heading = math.degrees(math.atan2(dx, dy)) % 360
                self.heading = (self.heading + (target_heading - self.heading) * 0.3) % 360
                self.speed_kmh = 40.0
        else:
            self.heading = (self.heading + random.uniform(-10, 10)) % 360
            self.speed_kmh = max(15, min(50, self.speed_kmh + random.uniform(-3, 3)))

        speed_ms = self.speed_kmh / 3.6
        dist_m = speed_ms * dt
        dist_deg = dist_m / 111_320

        self.lat += dist_deg * math.cos(math.radians(self.heading))
        self.lon += dist_deg * math.sin(math.radians(self.heading))

        if self.lat < LAT_MIN or self.lat > LAT_MAX:
            self.heading = (180 - self.heading) % 360
            self.lat = max(LAT_MIN, min(LAT_MAX, self.lat))
        if self.lon < LON_MIN or self.lon > LON_MAX:
            self.heading = (360 - self.heading) % 360
            self.lon = max(LON_MIN, min(LON_MAX, self.lon))

    def to_ws_payload(self) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()
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
            "signal_status": "ONLINE",
            "order_id": self.order_id,
            "timestamp": timestamp,
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
        self._init_shippers()

    def _init_shippers(self) -> None:
        """Create virtual shippers at random positions in HCMC."""
        self.shippers = {}
        for i in range(1, SHIPPER_COUNT + 1):
            shipper_id = f"SHP-{i:03d}"
            self.shippers[shipper_id] = VirtualShipper(
                shipper_id=shipper_id,
                lat=random.uniform(LAT_MIN, LAT_MAX),
                lon=random.uniform(LON_MIN, LON_MAX),
                speed_kmh=random.uniform(20, 45),
                heading=random.uniform(0, 360),
            )
        logger.info("[SimEngine] Initialized %s shippers", SHIPPER_COUNT)

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

    def dispatch_to_warehouse(self, shipper_ids: List[str]) -> None:
        """Command shippers to head to the warehouse."""
        self.dispatched_ids = shipper_ids
        self._arrived_at_warehouse = []
        self.phase = "DISPATCHING"
        for shipper_id in shipper_ids:
            shipper = self.shippers.get(shipper_id)
            if shipper:
                shipper.status = "HEADING_TO_WAREHOUSE"
                shipper.target_lat = WAREHOUSE_LAT
                shipper.target_lon = WAREHOUSE_LON
        logger.info("[SimEngine] Dispatched %s to warehouse", shipper_ids)

    def set_delivery_target(self, shipper_id: str, dest_lat: float, dest_lon: float, order_id: str) -> None:
        """Command a shipper to start delivery."""
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
            self.phase = "DELIVERING"

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

    async def _tick_all(self) -> None:
        """Process one simulation tick and persist the new state."""
        self._tick += 1
        snapshots: List[dict] = []
        db = get_database()
        shipper_repo = ShipperRepository(db) if db is not None else None
        tracking_repo = TrackingEventRepository(db) if db is not None else None

        for shipper_id, shipper in self.shippers.items():
            shipper.move(GPS_INTERVAL)

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

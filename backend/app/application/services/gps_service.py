"""
application/services/gps_service.py — GPS ingestion & stream management.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain import Shipper, Order, TrackingEvent, GPSStreamPayload
from app.infrastructure.repositories import ShipperRepository, OrderRepository, TrackingEventRepository
from app.utils import haversine_km, compute_speed, compute_heading, interpolate, compute_eta_minutes
from app.presentation.websocket.manager import ws_manager

logger = logging.getLogger(__name__)


class GPSService:
    """
    Service for handling GPS stream ingestion and processing.

    This is where the 9-step stream processor is implemented.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.shipper_repo = ShipperRepository(db)
        self.order_repo = OrderRepository(db)
        self.event_repo = TrackingEventRepository(db)

    async def process_gps_stream(self, gps_payload: GPSStreamPayload) -> Optional[dict]:
        """
        Main entry point: process one GPS event through 9-step pipeline.

        🔴 Called for every GPS point from simulator/field (~1 sec per shipper).

        Args:
            gps_payload: {shipper_id, lat, lon, timestamp}

        Returns:
            Tracking event dict if successful, None if validation fails.
        """

        # ══════════════════════════════════════
        # STEP 1: VALIDATE GPS DATA
        # ══════════════════════════════════════
        shipper_id = gps_payload.shipper_id
        lat = gps_payload.lat
        lon = gps_payload.lon

        if not shipper_id or lat is None or lon is None:
            logger.warning(f"[GPS] Validation failed: {gps_payload}")
            return None

        now = gps_payload.timestamp or datetime.now(timezone.utc)

        # ══════════════════════════════════════
        # STEP 2: CREATE TRACKING EVENT RECORD
        # ══════════════════════════════════════
        event = {
            "event_id": self._generate_event_id(),
            "timestamp": now,
            "shipper_id": shipper_id,
            "lat": lat,
            "lon": lon,
            "smooth_lat": lat,
            "smooth_lon": lon,
            "speed_kmh": 0.0,
            "heading": 0.0,
            "distance_moved_km": 0.0,
            "eta_minutes": None,
            "delay_minutes": 0,
            "event_type": "LOCATION_UPDATE",
            "exception_code": None,
            "note": None,
        }

        # ══════════════════════════════════════
        # STEP 3: COMPUTE SPEED + HEADING
        # ══════════════════════════════════════
        prev_event = await self.event_repo.find_shipper_last_location(shipper_id)
        if prev_event:
            prev_ts = prev_event["timestamp"].timestamp()
            curr_ts = now.timestamp()

            event["speed_kmh"] = compute_speed(
                prev_event["lat"], prev_event["lon"], prev_ts,
                lat, lon, curr_ts,
            )
            event["heading"] = compute_heading(prev_event["lat"], prev_event["lon"], lat, lon)
            event["distance_moved_km"] = haversine_km(prev_event["lat"], prev_event["lon"], lat, lon)

        # ══════════════════════════════════════
        # STEP 4: LINEAR INTERPOLATION
        # ══════════════════════════════════════
        if prev_event:
            smooth_lat, smooth_lon = interpolate(
                prev_event["lat"], prev_event["lon"],
                lat, lon,
                t=0.5,
            )
            event["smooth_lat"] = smooth_lat
            event["smooth_lon"] = smooth_lon

        # ══════════════════════════════════════
        # STEP 5: FETCH ACTIVE ORDER + COMPUTE ETA
        # ══════════════════════════════════════
        active_order = await self.order_repo.find_active_order(shipper_id)
        if active_order:
            event["order_id"] = active_order.get("order_id")
            eta = compute_eta_minutes(
                event["smooth_lat"], event["smooth_lon"],
                active_order["dest_lat"], active_order["dest_lon"],
                event["speed_kmh"],
            )
            event["eta_minutes"] = eta

            # Calculate delay vs SLA
            promised_at = active_order.get("promised_delivery_at")
            if promised_at:
                minutes_left = (promised_at - now).total_seconds() / 60
                event["delay_minutes"] = max(0, int(eta - minutes_left))

        # ══════════════════════════════════════
        # STEP 6: SAVE TO MONGODB (APPEND-ONLY)
        # ══════════════════════════════════════
        await self.event_repo.append_event(event)

        # ══════════════════════════════════════
        # STEP 7: CASCADE UPDATE (shipper + order)
        # ══════════════════════════════════════
        await self._update_shipper_state(event)
        if active_order:
            await self._update_order_state(event, active_order)

        # ══════════════════════════════════════
        # STEP 8: WEBSOCKET BROADCAST
        # ══════════════════════════════════════
        await self._broadcast_realtime(event, active_order)

        # ══════════════════════════════════════
        # STEP 9: DECISION ENGINE (ALERTS)
        # ══════════════════════════════════════
        await self._evaluate_rules(event, active_order)

        return event

    async def _update_shipper_state(self, event: dict) -> None:
        """STEP 7a: Update shipper GPS state."""
        await self.shipper_repo.update_gps_state(
            shipper_id=event["shipper_id"],
            lat=event["smooth_lat"],
            lon=event["smooth_lon"],
            speed_kmh=event["speed_kmh"],
            heading=event["heading"],
            timestamp=event["timestamp"],
        )

    async def _update_order_state(self, event: dict, order: dict) -> None:
        """STEP 7b: Update order ETA + status."""
        if event.get("eta_minutes") is None:
            return

        await self.order_repo.update_eta(
            order_id=order["order_id"],
            eta_minutes=event["eta_minutes"],
        )

    async def _broadcast_realtime(self, event: dict, order: Optional[dict]) -> None:
        """STEP 8: Broadcast GPS update to all WebSocket clients."""
        payload = {
            "event_id": event["event_id"],
            "shipper_id": event["shipper_id"],
            "lat": event["smooth_lat"],
            "lon": event["smooth_lon"],
            "speed_kmh": event["speed_kmh"],
            "heading": event["heading"],
            "eta_minutes": event.get("eta_minutes"),
            "order_id": event.get("order_id"),
            "order_status": order["current_status"] if order else None,
            "delay_minutes": event.get("delay_minutes", 0),
            "timestamp": event["timestamp"].isoformat(),
        }
        await ws_manager.broadcast(payload)

    async def _evaluate_rules(self, event: dict, order: Optional[dict]) -> None:
        """STEP 9: Decision engine — check alert conditions."""
        from app.config import settings

        # Alert: delivery delay
        if order and event.get("delay_minutes", 0) >= settings.delay_alert_minutes:
            logger.warning(
                f"[ALERT] Shipper {event['shipper_id']} delayed {event['delay_minutes']}min "
                f"| Order {order.get('order_id')}"
            )
            await ws_manager.broadcast({
                "type": "ALERT",
                "alert_type": "DELIVERY_DELAY",
                "shipper_id": event["shipper_id"],
                "order_id": order.get("order_id"),
                "delay_minutes": event["delay_minutes"],
            })

        # Alert: idle (speed < 0.5)
        if event["speed_kmh"] < 0.5:
            logger.debug(f"[RULE] Shipper {event['shipper_id']} is idle")

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid
        return str(uuid.uuid4())

"""
stream_processor.py — ⭐ HÀM CỐT LÕI: process_gps_event()

Mỗi bản tin GPS từ Kafka đi qua 9 bước xử lý tuần tự.
Xem pseudocode chi tiết tại docs/pseudocode.md.

Mục tiêu performance: < 200ms từ nhận GPS → Dashboard hiển thị.
"""
import uuid
import logging
from datetime import datetime, timezone
import random
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.haversine import haversine_km, compute_speed, compute_heading
from app.utils.interpolation import interpolate, compute_eta_minutes
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────

async def process_gps_event(db: AsyncIOMotorDatabase, gps_data: dict) -> Optional[dict]:
    """
    Xử lý 1 bản tin GPS qua 9 bước. Gọi từ kafka_consumer.

    Args:
        db:       Motor database instance
        gps_data: {shipper_id, lat, lon, timestamp (ISO string)}

    Returns:
        TrackingEvent dict đã lưu, hoặc None nếu lỗi validate
    """

    # ══════════════════════════════════════
    # BƯỚC 1: VALIDATE
    # ══════════════════════════════════════
    shipper_id = gps_data.get("shipper_id")
    if not shipper_id:
        logger.warning("[GPS] Rejected: missing shipper_id")
        return None

    lat = gps_data.get("lat")
    lon = gps_data.get("lon")
    if lat is None or lon is None:
        logger.warning(f"[GPS] Rejected: missing lat/lon for {shipper_id}")
        return None


    # ══════════════════════════════════════
    # BƯỚC 2: TẠO TRACKING EVENT MỚI
    # ══════════════════════════════════════
    now = datetime.now(timezone.utc)
    event = {
        "event_id":   str(uuid.uuid4()),
        "timestamp":  now,
        "shipper_id": shipper_id,
        "lat":        lat,
        "lon":        lon,
        "event_type": "LOCATION_UPDATE",
        "status_code": "IN_TRANSIT",
        "order_id":   None,
        "smooth_lat": lat,
        "smooth_lon": lon,
        "speed_kmh":  0.0,
        "heading":    0.0,
        "distance_moved_km": 0.0,
        "eta_minutes":  None,
        "delay_minutes": 0,
        "exception_code": None,
        "note": None,
    }


    # ══════════════════════════════════════
    # BƯỚC 3: TÍNH SPEED + HEADING (Haversine)
    # ══════════════════════════════════════
    prev_event = await _get_last_event(db, shipper_id)
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
    # BƯỚC 4: LINEAR INTERPOLATION
    # ══════════════════════════════════════
    if prev_event:
        smooth_lat, smooth_lon = interpolate(
            prev_event["lat"], prev_event["lon"],
            lat, lon,
            t=0.8,
        )
        event["smooth_lat"] = smooth_lat
        event["smooth_lon"] = smooth_lon


    # ══════════════════════════════════════
    # BƯỚC 5: LẤY ACTIVE ORDER + TÍNH ETA
    # ══════════════════════════════════════
    order = await _get_active_order(db, shipper_id)
    if order:
        event["order_id"] = order.get("order_id")
        eta = compute_eta_minutes(
            event["smooth_lat"], event["smooth_lon"],
            order["dest_lat"], order["dest_lon"],
            event["speed_kmh"],
        )
        event["eta_minutes"] = eta

        # Tính delay so với SLA
        promised_at = order.get("promised_delivery_at")
        if promised_at:
            minutes_left = (promised_at - now).total_seconds() / 60
            event["delay_minutes"] = max(0, int(eta - minutes_left))


    # ══════════════════════════════════════
    # BƯỚC 6: LƯU VÀO MongoDB
    # ══════════════════════════════════════
    await db.tracking_events.insert_one(event)


    # ══════════════════════════════════════
    # BƯỚC 7: CASCADE UPDATE
    # ══════════════════════════════════════
    await _update_shipper_state(db, event)
    await _update_order_state(db, event, order)


    # ══════════════════════════════════════
    # BƯỚC 8: WEBSOCKET BROADCAST (Real-time push)
    # ══════════════════════════════════════
    await _push_realtime(event, order)


    # ══════════════════════════════════════
    # BƯỚC 9: DECISION ENGINE
    # ══════════════════════════════════════
    await _evaluate_rules(db, event, order)

    return event


# ──────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────

async def _get_last_event(db: AsyncIOMotorDatabase, shipper_id: str) -> Optional[dict]:
    """Lấy tracking event gần nhất của shipper (query riêng, không $lookup)."""
    cursor = db.tracking_events.find(
        {"shipper_id": shipper_id, "event_type": "LOCATION_UPDATE"},
        projection={"_id": 0}
    ).sort("timestamp", -1).limit(1)

    results = await cursor.to_list(length=1)
    return results[0] if results else None


async def _get_active_order(db: AsyncIOMotorDatabase, shipper_id: str) -> Optional[dict]:
    """Lấy đơn hàng đang giao (IN_TRANSIT hoặc PICKED_UP) của shipper."""
    return await db.orders.find_one({
        "assigned_shipper_id": shipper_id,
        "current_status": {"$in": ["IN_TRANSIT", "PICKED_UP"]},
    })


async def _update_shipper_state(db: AsyncIOMotorDatabase, event: dict):
    """Cập nhật GPS live + trạng thái shipper (BƯỚC 7a)."""
    await db.shippers.update_one(
        {"shipper_id": event["shipper_id"]},
        {
            "$set": {
                "current_lat":       event["smooth_lat"],
                "current_lon":       event["smooth_lon"],
                "current_speed_kmh": event["speed_kmh"],
                "heading":           event["heading"],
                "last_ping_at":      event["timestamp"],
                "updated_at":        event["timestamp"],
                "signal_status":     "ONLINE"
            },
            "$setOnInsert": {
                "name": f"Tài xế {event['shipper_id'][-3:]}",
                "phone_number": "09" + "".join([str(random.randint(0,9)) for _ in range(8)]),
                "vehicle_type": "motorbike",
                "current_status": "IDLE",
                "created_at": event["timestamp"]
            }
        },
        upsert=True
    )


async def _update_order_state(db: AsyncIOMotorDatabase, event: dict, order: Optional[dict]):
    """Cập nhật ETA + trạng thái đơn hàng (BƯỚC 7b)."""
    if not order or event.get("eta_minutes") is None:
        return
    await db.orders.update_one(
        {"order_id": order["order_id"]},
        {"$set": {
            "eta_minutes":    event["eta_minutes"],
            "current_status": "IN_TRANSIT",
            "updated_at":     event["timestamp"],
        }},
    )


async def _push_realtime(event: dict, order: Optional[dict]):
    """Broadcast GPS payload tới tất cả WebSocket clients (BƯỚC 8)."""
    payload = {
        "event_id":    event["event_id"],
        "shipper_id":  event["shipper_id"],
        "lat":         event["smooth_lat"],
        "lon":         event["smooth_lon"],
        "speed_kmh":   event["speed_kmh"],
        "heading":     event["heading"],
        "eta_minutes": event.get("eta_minutes"),
        "order_id":    event.get("order_id"),
        "order_status": order["current_status"] if order else None,
        "delay_minutes": event.get("delay_minutes", 0),
        "timestamp":   event["timestamp"].isoformat(),
    }
    await ws_manager.broadcast(payload)


async def _evaluate_rules(db: AsyncIOMotorDatabase, event: dict, order: Optional[dict]):
    """Decision Engine: kiểm tra các điều kiện cảnh báo (BƯỚC 9)."""
    from app.config import settings

    # Cảnh báo trễ giao hàng
    if order and event.get("delay_minutes", 0) >= settings.delay_alert_minutes:
        logger.warning(
            f"[ALERT] Shipper {event['shipper_id']} trễ {event['delay_minutes']} phút "
            f"| Order: {order.get('order_id')}"
        )
        await ws_manager.broadcast({
            "type": "ALERT",
            "alert_type": "DELIVERY_DELAY",
            "shipper_id": event["shipper_id"],
            "order_id": order.get("order_id"),
            "delay_minutes": event["delay_minutes"],
        })

    # Cảnh báo đứng yên (tốc độ = 0 liên tục)
    if event["speed_kmh"] < 0.5:
        logger.debug(f"[RULE] Shipper {event['shipper_id']} idle / đứng yên")

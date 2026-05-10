"""
simulate.py — 100 shipper ảo phát GPS mỗi 1 giây qua WebSocket.

Chạy độc lập: python data_generator/simulate.py
Hoặc qua Docker Compose: docker compose --profile simulator up simulator
"""
import asyncio
import json
import math
import random
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── CONFIG ──────────────────────────────────────────────
# Khi chạy trong Docker, cần dùng tên service 'backend' thay vì 'localhost'
BACKEND_WS_URL    = os.getenv("BACKEND_WS_URL", "ws://backend:8000/ws/ingest")
SHIPPER_COUNT     = int(os.getenv("SIMULATOR_SHIPPER_COUNT", "30"))
GPS_INTERVAL      = float(os.getenv("SIMULATOR_GPS_INTERVAL", "1.0"))  # giây
DROPOUT_PROB      = 0.02   # 2% xác suất mất GPS mỗi giây

# TP.HCM bounding box
LAT_MIN, LAT_MAX = 10.65, 10.90
LON_MIN, LON_MAX = 106.55, 106.85

# Tốc độ xe máy điển hình TP.HCM: 20–50 km/h
SPEED_MIN_KMPH = 20
SPEED_MAX_KMPH = 50


# ── SHIPPER DATA CLASS ──────────────────────────────────
@dataclass
class VirtualShipper:
    shipper_id: str
    lat: float
    lon: float
    speed_kmh: float = 30.0
    heading: float = 0.0   # degrees, 0 = North
    online: bool = True
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    # Fields to support snapping to nearest road
    last_snapped_lat: Optional[float] = None
    last_snapped_lon: Optional[float] = None
    last_snap_time: float = 0.0

    def move(self, dt_seconds: float = 1.0):
        """Di chuyển shipper theo hướng + tốc độ hiện tại."""
        if not self.online:
            return

        # Nếu có mục tiêu (về kho hoặc giao hàng), xoay hướng về phía mục tiêu
        if self.target_lat and self.target_lon:
            dy = self.target_lat - self.lat
            dx = self.target_lon - self.lon
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0.0001: # Nếu cách mục tiêu > 10m
                target_heading = math.degrees(math.atan2(dx, dy)) % 360
                # Nội suy hướng đi (xoay từ từ)
                self.heading = (self.heading + (target_heading - self.heading) * 0.2) % 360
                self.speed_kmh = 45.0 # Chạy nhanh về kho

        # Tính delta vị trí
        speed_ms = self.speed_kmh / 3.6
        distance_m = speed_ms * dt_seconds
        distance_deg = distance_m / 111_320  # ~111km per degree latitude

        # Di chuyển theo heading
        self.lat += distance_deg * math.cos(math.radians(self.heading))
        self.lon += distance_deg * math.sin(math.radians(self.heading))

        # Bounce khi chạm biên bounding box
        if self.lat < LAT_MIN or self.lat > LAT_MAX:
            self.heading = 180 - self.heading
            self.lat = max(LAT_MIN, min(LAT_MAX, self.lat))
        if self.lon < LON_MIN or self.lon > LON_MAX:
            self.heading = 360 - self.heading
            self.lon = max(LON_MIN, min(LON_MAX, self.lon))

        # Heading drift: thay đổi nhẹ mỗi giây để trông tự nhiên
        self.heading = (self.heading + random.uniform(-5, 5)) % 360

        # Tốc độ thay đổi nhẹ
        self.speed_kmh = max(SPEED_MIN_KMPH, min(SPEED_MAX_KMPH,
            self.speed_kmh + random.uniform(-2, 2)))

    def to_gps_payload(self) -> dict:
        return {
            "shipper_id": self.shipper_id,
            "lat":        round(self.lat, 6),
            "lon":        round(self.lon, 6),
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }


async def maybe_snap_shipper(shipper: VirtualShipper, session: aiohttp.ClientSession):
    """Snap a shipper's current location to the nearest road using OSRM nearest API.
    To reduce API usage we only call OSRM when the shipper has moved sufficiently
    from the last snapped point or after a time interval.
    """
    SNAP_DISTANCE_DEG = 0.00018  # ~20 meters
    SNAP_INTERVAL_S = 10         # force a resnap at least every 10s
    now = time.time()

    if shipper.last_snapped_lat is not None and shipper.last_snapped_lon is not None:
        dist = math.hypot(shipper.lat - shipper.last_snapped_lat, shipper.lon - shipper.last_snapped_lon)
        if dist < SNAP_DISTANCE_DEG and (now - shipper.last_snap_time) < SNAP_INTERVAL_S:
            return  # no need to resnap

    url = f"https://router.project-osrm.org/nearest/v1/driving/{shipper.lon},{shipper.lat}?number=1"
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                waypoints = data.get("waypoints") or []
                if waypoints:
                    lon, lat = waypoints[0].get("location", [shipper.lon, shipper.lat])
                    shipper.last_snapped_lat = lat
                    shipper.last_snapped_lon = lon
                    shipper.last_snap_time = now
                    # Apply snapped coordinate
                    shipper.lat = lat
                    shipper.lon = lon
    except Exception as e:
        # Ignore OSRM failures (network/rate limit) and keep original coordinates
        logger.debug(f"[Simulator] OSRM snap failed for {shipper.shipper_id}: {e}")

def init_shippers(count: int) -> list[VirtualShipper]:
    """Khởi tạo N shipper với vị trí ngẫu nhiên quanh TP.HCM."""
    shippers = []
    for i in range(1, count + 1):
        shippers.append(VirtualShipper(
            shipper_id = f"SHP-{i:03d}",
            lat        = random.uniform(LAT_MIN, LAT_MAX),
            lon        = random.uniform(LON_MIN, LON_MAX),
            speed_kmh  = random.uniform(SPEED_MIN_KMPH, SPEED_MAX_KMPH),
            heading    = random.uniform(0, 360),
        ))
    return shippers


# ── MAIN SIMULATION LOOP ────────────────────────────────
async def run_simulation():
    shippers = init_shippers(SHIPPER_COUNT)
    logger.info(f"🛵 Initialized {SHIPPER_COUNT} virtual shippers")

    async with aiohttp.ClientSession() as http_session:
        while True:
            try:
                async with websockets.connect(BACKEND_WS_URL) as ws:
                    logger.info(f"✅ Connected to {BACKEND_WS_URL}")
                    tick = 0

                    while True:
                        tick += 1
                        payloads = []

                        for shipper in shippers:
                            # Simulate GPS dropout
                            shipper.online = random.random() > DROPOUT_PROB

                            if shipper.online:
                                shipper.move(GPS_INTERVAL)
                                try:
                                    await maybe_snap_shipper(shipper, http_session)
                                except Exception as e:
                                    logger.debug(f"[Simulator] Snap error for {shipper.shipper_id}: {e}")
                                payloads.append(shipper.to_gps_payload())

                        # Gửi tất cả trong 1 batch (newline-delimited JSON)
                        for p in payloads:
                            await ws.send(json.dumps(p))

                        if tick % 10 == 0:
                            online = sum(1 for s in shippers if s.online)
                            logger.info(f"[tick={tick}] Sent {len(payloads)} GPS | online={online}/{SHIPPER_COUNT}")

                        await asyncio.sleep(GPS_INTERVAL)

            except Exception as e:
                logger.warning(f"[Simulator] Connection error: {e}. Retrying in 3s...")
                await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(run_simulation())

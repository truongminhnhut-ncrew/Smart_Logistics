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
import httpx
from dataclasses import dataclass, field
from datetime import datetime, timezone

import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── CONFIG ──────────────────────────────────────────────
BACKEND_WS_URL    = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/ws/ingest")
BACKEND_API_URL   = os.getenv("BACKEND_API_URL", "http://localhost:8000")
SHIPPER_COUNT     = int(os.getenv("SIMULATOR_SHIPPER_COUNT", "30"))
GPS_INTERVAL      = float(os.getenv("SIMULATOR_GPS_INTERVAL", "1.0"))  # giây
DROPOUT_PROB      = 0.02   # 2% xác suất mất GPS mỗi giây

# TP.HCM bounding box
LAT_MIN, LAT_MAX = 10.65, 10.90
LON_MIN, LON_MAX = 106.55, 106.85

# Tăng tốc độ để shipper di chuyển rõ rệt hơn trên bản đồ
SPEED_MIN_KMPH = 30
SPEED_MAX_KMPH = 60


# ── SHIPPER DATA CLASS ──────────────────────────────────
@dataclass
class VirtualShipper:
    shipper_id: str
    lat: float
    lon: float
    speed_kmh: float = 30.0
    heading: float = 0.0   # degrees, 0 = North
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    online: bool = True

    def move(self, dt_seconds: float = 1.0):
        """Di chuyển shipper theo hướng + tốc độ hiện tại."""
        if not self.online:
            return

        # Nếu có mục tiêu (ví dụ: Kho hàng), điều chỉnh heading về phía mục tiêu
        if self.target_lat and self.target_lon:
            dy = self.target_lat - self.lat
            dx = self.target_lon - self.lon
            target_heading = math.degrees(math.atan2(dx, dy)) % 360
            # Xoay dần heading về hướng mục tiêu
            diff = (target_heading - self.heading + 180) % 360 - 180
            self.heading = (self.heading + diff * 0.5) % 360
            
            # Nếu đã đến gần mục tiêu (< 10m), dừng lại hoặc chờ lệnh tiếp theo
            dist = math.sqrt(dx**2 + dy**2)
            if dist < 0.0001: # Khoảng 10-15m
                self.speed_kmh = 0
                return

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
        self.heading = (self.heading + random.uniform(-15, 15)) % 360

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

    while True:
        try:
            async with websockets.connect(BACKEND_WS_URL) as ws:
                logger.info(f"✅ Connected to {BACKEND_WS_URL}")
                tick = 0

                while True:
                    tick += 1
                    
                    # Mỗi 5 giây cập nhật trạng thái/mục tiêu từ API để biết ai cần về kho
                    if tick % 5 == 1:
                        try:
                            async with httpx.AsyncClient() as client:
                                r = await client.get(f"{BACKEND_API_URL}/shippers")
                                if r.status_code == 200:
                                    shippers_db = {s['shipper_id']: s for s in r.json()}
                                    for s in shippers:
                                        db_data = shippers_db.get(s.shipper_id)
                                        if db_data and db_data.get('target_lat'):
                                            s.target_lat = db_data['target_lat']
                                            s.target_lon = db_data['target_lon']
                                            s.speed_kmh = 45.0 # Chạy nhanh về kho
                        except Exception: pass

                    payloads = []
                    for shipper in shippers:
                        # Simulate GPS dropout
                        shipper.online = random.random() > DROPOUT_PROB

                        if shipper.online:
                            shipper.move(GPS_INTERVAL)
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

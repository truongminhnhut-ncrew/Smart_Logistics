# Công Nghệ Sử Dụng (Tech Stack)

## Tổng quan

| Layer | Công nghệ | Phiên bản | Ghi chú |
|-------|-----------|-----------|---------|
| Backend | Python + FastAPI | 3.11 / 0.111.0 | Async toàn bộ, không blocking I/O |
| Message Queue | Apache Kafka | 7.5.0 (Confluent) | Topic: `gps_stream` |
| Database | MongoDB | 7.0 | Motor async driver |
| Cache | Redis | 7.2-alpine | Lưu GPS state gần nhất, TTL 10s |
| Frontend | React + Vite | 18 / latest | Không dùng CRA |
| Bản đồ | Leaflet.js | 1.9.4 | OpenStreetMap tiles |
| Infrastructure | Docker Compose | v3.9 | 6 services tất cả |
| Zookeeper | Confluent Zookeeper | 7.5.0 | Kafka coordination |

---

## Backend

### Ngôn ngữ & Framework
- **Python 3.11** — Runtime chính
- **FastAPI 0.111.0** — Web framework async
- **Uvicorn** — ASGI server (production: uvicorn[standard])

### Database & Messaging
- **MongoDB 7.0** + **Motor 3.3.2** — Database chính, async driver
- **Apache Kafka 7.5.0** + **confluent-kafka 2.3.0** — Message queue, stream processing
- **Redis 7.2** + **redis[asyncio] 5.0.1** — Cache GPS state, async client

### Thư viện Python chính
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
motor==3.3.2              # MongoDB async driver
confluent-kafka==2.3.0    # Kafka client
redis[asyncio]==5.0.1     # Redis async client
pydantic-settings==2.2.1  # Config từ .env
python-dotenv==1.0.1
httpx==0.27.0             # HTTP client async
```

### Thuật toán xử lý GPS
- **Haversine Formula** — Tính khoảng cách giữa 2 tọa độ GPS (km)
- **Linear Interpolation** — Làm mịn quỹ đạo di chuyển giữa 2 điểm GPS
- **Bearing Calculation** — Tính hướng di chuyển (heading 0–360°)

---

## Frontend

### Framework & Build Tool
- **React 18** — UI framework
- **Vite** — Build tool (fast HMR, ES modules)
- **JSX** — Component syntax

### Bản đồ & Visualization
- **Leaflet.js 1.9.4** — Interactive map library
- **OpenStreetMap** — Tile provider (miễn phí)

### Kết nối Real-time
- **WebSocket API** (native browser) — Nhận GPS broadcast từ backend
- **REST API** — Fetch danh sách shipper, order, stats

### CSS & Design
- **CSS Variables** — Dark theme design system
- **DM Sans** — Font chính (sans-serif)
- **JetBrains Mono** — Font monospace (data display)

**Màu sắc chủ đạo:**
```css
--bg:     #08090b;  /* nền chính */
--green:  #00e5a0;  /* accent — trạng thái DELIVERING */
--amber:  #f5a623;  /* IDLE */
--red:    #ff4757;  /* OFFLINE */
--blue:   #4a9eff;  /* AVAILABLE */
```

---

## Infrastructure (Docker Compose)

| Container | Image | Port | Vai trò |
|-----------|-------|------|---------|
| zookeeper | confluentinc/cp-zookeeper:7.5.0 | 2181 | Quản lý Kafka cluster |
| kafka | confluentinc/cp-kafka:7.5.0 | 9092 | Message broker |
| mongodb | mongo:7.0 | 27017 | Database chính |
| redis | redis:7.2-alpine | 6379 | Cache layer |
| backend | build ./backend | 8000 | FastAPI app |
| frontend | build ./frontend | 3000 | React app |

---

## Database Schema (MongoDB)

### Collection: `shippers`
```json
{
  "shipper_id": "SHP-001",
  "name": "string",
  "current_status": "DELIVERING | IDLE | ASSIGNED | AVAILABLE",
  "current_lat": 10.77695,
  "current_lon": 106.70095,
  "current_speed_kmh": 32.5,
  "heading": 45.3,
  "signal_status": "ONLINE | OFFLINE",
  "last_ping_at": "ISO8601",
  "completed_count": 5,
  "total_distance_km": 12.3
}
```

### Collection: `orders`
```json
{
  "order_id": "ORD-20260508-001",
  "assigned_shipper_id": "SHP-001",
  "current_status": "PENDING | PICKED_UP | IN_TRANSIT | DELIVERED | FAILED",
  "dest_lat": 10.78,
  "dest_lon": 106.72,
  "eta_minutes": 15,
  "delay_minutes": 2,
  "priority": "HIGH | NORMAL | LOW"
}
```

### Collection: `tracking_events` ⚠️ Append-only
```json
{
  "event_id": "UUID-v4",
  "shipper_id": "SHP-001",
  "order_id": "ORD-001",
  "event_type": "LOCATION_UPDATE | STATUS_CHANGE | DELIVERY_COMPLETE",
  "lat": 10.77695,
  "lon": 106.70095,
  "smooth_lat": 10.77691,
  "smooth_lon": 106.70093,
  "speed_kmh": 32.5,
  "heading": 45.3,
  "eta_minutes": 15,
  "timestamp": "ISO8601"
}
```
> **TTL Index:** Tự động xóa sau 7 ngày. KHÔNG BAO GIỜ update/delete record này.

---

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/shippers` | Danh sách tất cả shipper + GPS live |
| GET | `/shippers/{id}` | Chi tiết 1 shipper |
| GET | `/shippers/{id}/history` | 50 tracking events gần nhất |
| GET | `/orders` | Danh sách đơn hàng |
| POST | `/orders` | Tạo đơn hàng mới |
| PATCH | `/orders/{id}/complete` | Xác nhận giao thành công |
| GET | `/stats` | Dashboard: active count, km, top shippers |
| WS | `ws://.../ws` | Broadcast GPS realtime → frontend |
| WS | `ws://.../ws/ingest` | Nhận GPS stream từ simulator |
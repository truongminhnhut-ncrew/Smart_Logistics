# 🚀 CLAUDE.md — ShipTrack Real-time Shipper Tracking System
> **Đây là file hướng dẫn chính cho Claude Code.**
> Đọc toàn bộ file này trước khi viết bất kỳ dòng code nào.

---

## 🎯 Mục tiêu hệ thống

Xây dựng hệ thống theo dõi **100 shipper ảo theo thời gian thực** trên bản đồ TP.HCM:
- GPS streaming qua **WebSocket → Kafka → MongoDB**
- Backend **FastAPI (Python)** xử lý stream, tính Haversine + Linear Interpolation
- Frontend **React + Leaflet.js** hiển thị dashboard dark theme theo đúng `docs/fe_reference.html`
- Chạy hoàn toàn trên **Docker Compose** local

---

## 🧱 Tech Stack — KHÔNG được thay đổi

| Layer | Công nghệ | Ghi chú |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async toàn bộ |
| Message Queue | Apache Kafka | Topic: `gps_stream` |
| Database | MongoDB | Motor (async driver) |
| Cache | Redis | Lưu GPS state gần nhất |
| Frontend | React 18 + Vite | Không dùng CRA |
| Map | Leaflet.js 1.9.4 | OpenStreetMap tiles |
| DevOps | Docker Compose v3.9 | 6 services |

---

## 📁 Cấu trúc thư mục — KHÔNG được tự ý thêm/đổi

```
shiptrack/
├── CLAUDE.md                        ← File này
├── .env.example                     ← Template biến môi trường
├── docker-compose.yml               ← 6 services: zookeeper, kafka, mongodb, redis, backend, frontend
│
├── backend/
│   ├── app/
│   │   ├── main.py                  ← FastAPI app + WebSocket server + startup events
│   │   ├── config.py                ← Pydantic Settings từ .env
│   │   ├── db.py                    ← Motor MongoDB connection pool
│   │   ├── models/
│   │   │   ├── shipper.py           ← Pydantic model cho collection `shippers`
│   │   │   ├── order.py             ← Pydantic model cho collection `orders`
│   │   │   ├── warehouse.py         ← Pydantic model cho collection `warehouses`
│   │   │   └── tracking_event.py    ← Pydantic model cho collection `tracking_events`
│   │   ├── routers/
│   │   │   ├── shippers.py          ← GET /shippers, GET /shippers/{id}, GET /shippers/{id}/history
│   │   │   ├── orders.py            ← GET /orders, POST /orders, PATCH /orders/{id}/complete
│   │   │   └── dashboard.py         ← GET /stats (active count, km, top list)
│   │   ├── services/
│   │   │   ├── gps_ingestion.py     ← WebSocket receiver từ shipper app/simulator
│   │   │   ├── kafka_producer.py    ← Đẩy GPS vào topic `gps_stream`
│   │   │   ├── kafka_consumer.py    ← Tiêu thụ `gps_stream`, gọi stream_processor
│   │   │   ├── stream_processor.py  ← ⭐ HÀM CỐT LÕI: process_gps_event() 9 bước
│   │   │   ├── order_service.py     ← create_order(), assign_shipper(), retry_later()
│   │   │   └── decision_engine.py   ← evaluate_rules(): cảnh báo, retry GPS
│   │   ├── utils/
│   │   │   ├── haversine.py         ← compute_speed(), compute_heading(), distance()
│   │   │   └── interpolation.py     ← interpolate(): Linear Interpolation giữa 2 GPS points
│   │   └── websocket/
│   │       └── manager.py           ← ConnectionManager: broadcast tới tất cả frontend clients
│   ├── data_generator/
│   │   └── simulate.py              ← 100 shipper ảo, mỗi shipper gửi GPS mỗi 1 giây
│   ├── scripts/
│   │   └── init_db.js               ← MongoDB init: tạo collections + indexes + seed warehouse
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TopBar.jsx           ← Header: logo, status dots, clock
│   │   │   ├── ShipperList.jsx      ← Left panel: danh sách 100 shipper
│   │   │   ├── MapView.jsx          ← Center: Leaflet map + markers + trails
│   │   │   ├── RightPanel.jsx       ← Right panel: shipper detail + order info
│   │   │   └── Dashboard.jsx        ← Stats: active count, total km, top list
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js      ← Custom hook: kết nối ws://localhost:8000/ws
│   │   │   └── useShippers.js       ← State management cho 100 shipper
│   │   ├── services/
│   │   │   └── api.js               ← REST API calls tới backend
│   │   ├── styles/
│   │   │   └── theme.css            ← CSS variables từ fe_reference.html
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
│
└── docs/
    ├── project_overview.md          ← Tổng quan dự án
    ├── database_design.md           ← MongoDB schema chi tiết
    ├── pseudocode.md                ← Pseudocode 9 bước xử lý GPS
    └── fe_reference.html            ← UI mẫu (COPY CHÍNH XÁC design này)
```

---

## ⚙️ Thứ tự build — Làm ĐÚNG THỨ TỰ này

### Phase 1: Infrastructure
1. `docker-compose.yml` — khởi tạo 6 services
2. `.env.example` — tất cả biến môi trường
3. `backend/scripts/init_db.js` — MongoDB collections + indexes + seed

### Phase 2: Backend Core
4. `backend/app/config.py` — Pydantic Settings
5. `backend/app/db.py` — Motor connection
6. `backend/app/models/*.py` — 4 Pydantic models (xem schema ở `docs/database_design.md`)
7. `backend/app/utils/haversine.py` — Haversine formula
8. `backend/app/utils/interpolation.py` — Linear Interpolation

### Phase 3: Business Logic
9. `backend/app/services/stream_processor.py` — `process_gps_event()` 9 bước (xem `docs/pseudocode.md`)
10. `backend/app/services/kafka_producer.py`
11. `backend/app/services/kafka_consumer.py`
12. `backend/app/services/order_service.py`
13. `backend/app/services/decision_engine.py`
14. `backend/app/websocket/manager.py`

### Phase 4: API Layer
15. `backend/app/routers/shippers.py`
16. `backend/app/routers/orders.py`
17. `backend/app/routers/dashboard.py`
18. `backend/app/main.py` — wires everything together

### Phase 5: Data Simulator
19. `backend/data_generator/simulate.py` — 100 shipper ảo

### Phase 6: Frontend
20. `frontend/src/styles/theme.css` — CSS variables
21. `frontend/src/hooks/useWebSocket.js`
22. `frontend/src/hooks/useShippers.js`
23. `frontend/src/services/api.js`
24. `frontend/src/components/TopBar.jsx`
25. `frontend/src/components/ShipperList.jsx`
26. `frontend/src/components/MapView.jsx` — Leaflet + markers
27. `frontend/src/components/RightPanel.jsx`
28. `frontend/src/components/Dashboard.jsx`
29. `frontend/src/App.jsx`

---

## 🗄️ Database Schema — PHẢI THEO ĐÚNG

Xem chi tiết tại `docs/database_design.md`. Tóm tắt nhanh:

### Collection: `shippers`
```javascript
{
  shipper_id: "SHP-001",          // PK, unique index
  name, phone_number, vehicle_type, vehicle_plate,
  current_status: "DELIVERING",   // IDLE | ASSIGNED | DELIVERING | AVAILABLE
  current_lat, current_lon,       // 🔴 GPS live, cập nhật mỗi 1s
  current_speed_kmh, heading,
  signal_status: "ONLINE",        // ONLINE | OFFLINE
  last_ping_at,
  completed_count, total_distance_km
}
```

### Collection: `orders`
```javascript
{
  order_id: "ORD-20250101-001",   // PK, unique index
  warehouse_id, assigned_shipper_id,
  dest_lat, dest_lon, destination_text,
  current_status: "IN_TRANSIT",   // PENDING | PICKED_UP | IN_TRANSIT | DELIVERED | FAILED
  eta_minutes,                    // 🔴 Live, tính lại mỗi ~5s
  promised_delivery_at, priority
}
```

### Collection: `tracking_events`
```javascript
{
  event_id,                       // UUID v4
  shipper_id, order_id,
  event_type: "LOCATION_UPDATE",  // LOCATION_UPDATE | STATUS_CHANGE | DELIVERY_COMPLETE
  lat, lon, smooth_lat, smooth_lon,
  speed_kmh, heading, distance_moved_km,
  eta_minutes, delay_minutes
}
// ⚠️ APPEND-ONLY — KHÔNG BAO GIỜ update/delete
// TTL index: tự xóa sau 7 ngày
```

---

## ⭐ Hàm cốt lõi: `process_gps_event()` — 9 bước bắt buộc

File: `backend/app/services/stream_processor.py`

```
BƯỚC 1: Validate — kiểm tra shipper_id không null
BƯỚC 2: Tạo TrackingEvent mới (event_id, timestamp, lat, lon)
BƯỚC 3: Tính speed_kmh + heading từ Haversine (prev → current)
BƯỚC 4: Linear Interpolation → smooth_lat, smooth_lon
BƯỚC 5: Lấy active order → tính eta_minutes + delay_minutes
BƯỚC 6: Lưu tracking_event vào MongoDB (append-only)
BƯỚC 7: CASCADE UPDATE: update_shipper_state() + update_order_state() + update_warehouse_state()
BƯỚC 8: push_realtime() → WebSocket broadcast tới tất cả frontend
BƯỚC 9: evaluate_rules() → kiểm tra cảnh báo (đứng yên, trễ, mất GPS)
```

Xem pseudocode đầy đủ tại `docs/pseudocode.md`.

---

## 🎨 UI Design — COPY CHÍNH XÁC từ `docs/fe_reference.html`

### Layout (3-panel)
```
┌─────────────────────────────────────────────────┐
│  TopBar (46px): Logo | Status dots | Clock      │
├──────────┬──────────────────────┬────────────────┤
│  Left    │    Map (Leaflet)     │  Right Panel  │
│  250px   │    Center (flex:1)   │  272px        │
│  Shipper │                      │  Shipper detail│
│  List    │  OpenStreetMap       │  + Order info  │
└──────────┴──────────────────────┴────────────────┘
```

### CSS Variables (bắt buộc dùng)
```css
--bg:      #08090b;   /* nền chính */
--bg2:     #0f1115;   /* panels */
--bg3:     #161a20;   /* hover states */
--border:  #1c2028;
--text:    #cdd6e0;
--text2:   #5f7080;
--green:   #00e5a0;   /* accent chính */
--amber:   #f5a623;
--red:     #ff4757;
--blue:    #4a9eff;
--mono:    'JetBrains Mono', monospace;
--sans:    'DM Sans', sans-serif;
```

### Shipper status colors
- `DELIVERING` → `--green` (dot xanh + tag `live`)
- `IDLE` → `--amber` (dot vàng + tag `idle`)
- `OFFLINE` → `--red` (dot đỏ + tag `lost`)
- `AVAILABLE` → `--blue` (dot xanh dương + tag `available`)
- `ASSIGNED` → `--purple` (dot tím + tag `assigned`)

---

## 🌐 API Endpoints

```
REST:
  GET  /shippers                     → Danh sách tất cả shipper + GPS live
  GET  /shippers/{id}                → Chi tiết 1 shipper
  GET  /shippers/{id}/history        → 50 tracking events gần nhất
  GET  /orders                       → Danh sách đơn hàng
  POST /orders                       → Tạo đơn hàng mới
  PATCH /orders/{id}/complete        → Xác nhận giao thành công
  GET  /stats                        → Dashboard: active, km, top shippers

WebSocket:
  ws://localhost:8000/ws             → Broadcast GPS realtime (mỗi 1s)
  
  Payload format:
  {
    "event_id": "uuid",
    "shipper_id": "SHP-001",
    "lat": 10.77695,
    "lon": 106.70095,
    "speed_kmh": 32.5,
    "eta_minutes": 15,
    "order_status": "IN_TRANSIT"
  }
```

---

## 🐳 Docker Compose Services

```yaml
services:
  zookeeper:    image: confluentinc/cp-zookeeper:7.5.0,  port: 2181
  kafka:        image: confluentinc/cp-kafka:7.5.0,      port: 9092
  mongodb:      image: mongo:7.0,                        port: 27017
  redis:        image: redis:7.2-alpine,                 port: 6379
  backend:      build: ./backend,                        port: 8000
  frontend:     build: ./frontend,                       port: 3000
```

**Dependency order:** `zookeeper` → `kafka` → `mongodb` + `redis` → `backend` → `frontend`

---

## 📦 Python Dependencies (`requirements.txt`)

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
motor==3.3.2              # MongoDB async
confluent-kafka==2.3.0    # Kafka
redis[asyncio]==5.0.1     # Redis async
pydantic-settings==2.2.1
python-dotenv==1.0.1
httpx==0.27.0             # HTTP client
```

---

## 📍 Data Generator — 100 Shipper ảo

File: `backend/data_generator/simulate.py`

- Khởi tạo 100 shipper với `lat/lng` ngẫu nhiên quanh TP.HCM (bounding box: lat 10.65–10.90, lon 106.55–106.85)
- Mỗi shipper di chuyển theo hướng ngẫu nhiên, tốc độ 20–50 km/h
- Mỗi 1 giây: tính vị trí mới bằng Linear Interpolation, gửi WebSocket tới `ws://backend:8000/ws/ingest`
- Simulate GPS dropout ngẫu nhiên 2% để test cảnh báo `OFFLINE`

---

## ⚠️ Các quy tắc bắt buộc

1. **Async toàn bộ backend** — dùng `async/await`, không dùng blocking I/O
2. **Motor, không pymongo** — `AsyncIOMotorClient` cho tất cả MongoDB operations
3. **`tracking_events` là append-only** — KHÔNG BAO GIỜ `updateOne()` hay `deleteOne()`
4. **WebSocket manager** phải xử lý được disconnect gracefully (try/except)
5. **Kafka consumer** phải có Dead Letter Queue khi `process_gps_event()` lỗi
6. **Frontend** dùng `useRef` cho Leaflet map instance, không re-create map khi re-render
7. **Marker update** — dùng `marker.setLatLng()` thay vì xóa/tạo lại marker
8. **Không dùng** `$lookup` trong realtime path — query riêng từng collection
9. **Environment variables** — tất cả config phải đọc từ `.env`, không hardcode
10. **CORS** — backend phải allow `http://localhost:3000`

---

## 🚦 Khi gặp lỗi — Hướng xử lý

| Lỗi | Hướng xử lý |
|---|---|
| Kafka connection refused | Retry với exponential backoff, log warning |
| MongoDB timeout | Trả về cached data từ Redis |
| WebSocket client disconnect | Xóa khỏi `ConnectionManager.active_connections`, không raise |
| GPS data invalid | Log error + `continue`, không crash loop |
| `shipper_id` not in DB | Dùng `upsert=True` khi update GPS |

---

## 💡 Gợi ý khi prompt Claude Code

Khi bắt đầu một file mới, dùng prompt theo dạng:

```
Build [tên file] theo đúng CLAUDE.md:
- Tham khảo schema tại docs/database_design.md (collection: X)
- Implement hàm Y theo pseudocode tại docs/pseudocode.md (bước A→B)
- UI theo design tại docs/fe_reference.html (component Z)
```

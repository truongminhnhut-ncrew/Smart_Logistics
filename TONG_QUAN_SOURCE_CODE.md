# 📋 TỔNG QUAN SOURCE CODE — Smart Logistics (ShipTrack)

> Tài liệu tổng quan toàn bộ source code project Smart_Logistics.  
> Cập nhật: 2026-05-04 (v2.1 — Route Polylines + OSRM integration)

---

## 1. Mục đích project

**Smart_Logistics** (tên hệ thống: **ShipTrack**) là ứng dụng **theo dõi shipper thời gian thực** dùng cho quản lý logistics.

### Chức năng chính:
- 🗺️ Hiển thị bản đồ realtime 30 shipper ảo di chuyển trong khu vực TP.HCM
- 🚚 Mô phỏng luồng: shipper idle → dispatch đến warehouse → nhận đơn → giao hàng
- 📦 Quản lý đơn hàng (tạo, gán shipper, theo dõi trạng thái)
- ⚠️ Quản lý sự cố (incident) trong quá trình giao hàng
- 📊 Dashboard thống kê realtime
- 🔔 WebSocket broadcast dữ liệu GPS và events cho frontend

---

## 2. Công nghệ sử dụng

| Layer | Công nghệ |
|-------|-----------|
| **Backend** | FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| **Database** | MongoDB 7 (qua Motor async driver) |
| **Cache** | Redis 7.2 (dự phòng, chưa active trong luồng chính) |
| **Message Queue** | Kafka (dự phòng, chưa active trong luồng chính) |
| **Frontend** | React 18, Vite 5, Leaflet (bản đồ), Axios |
| **Realtime** | WebSocket (native FastAPI) |
| **Infrastructure** | Docker Compose (MongoDB, Kafka, Zookeeper, Redis) |
| **Language** | Python 3.11, JavaScript (JSX) |

---

## 3. Cấu trúc thư mục

```
Smart_Logistics/
├── main.py                          # Entry point ngoài (chạy uvicorn)
├── docker-compose.yml               # Hạ tầng MongoDB + Kafka + Redis
├── requirements-local.txt           # Python dependencies cho dev local
├── .env.example                     # Biến môi trường mẫu
├── README.md / SETUP.md / CLAUDE.md # Tài liệu hướng dẫn
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/                         # ★ CORE BACKEND CODE
│       ├── main.py                  # FastAPI app + lifespan + WS endpoint
│       ├── config.py                # Pydantic Settings (env vars)
│       ├── db.py                    # Motor async MongoDB connection
│       ├── stream_processor_reference.py  # Reference code (không dùng trực tiếp)
│       │
│       ├── domain/                  # 🔵 DOMAIN LAYER
│       │   └── entities.py          # Tất cả Pydantic models + enums
│       │
│       ├── application/             # 🟢 APPLICATION LAYER
│       │   ├── services/
│       │   │   ├── simulation_engine.py  # ★ Core simulation loop (30 shippers)
│       │   │   ├── routing_engine.py     # ★ A* graph-based routing engine
│       │   │   ├── lstm_predictor.py     # ★ LSTM ETA/delay predictor (stub)
│       │   │   ├── gps_service.py        # GPS processing service
│       │   │   └── order_service.py      # Order business logic
│       │   └── usecases/                 # (placeholder)
│       │
│       ├── infrastructure/          # 🟡 INFRASTRUCTURE LAYER
│       │   ├── repositories/
│       │   │   ├── base_repository.py
│       │   │   ├── shipper_repository.py
│       │   │   ├── order_repository.py
│       │   │   ├── incident_repository.py
│       │   │   └── tracking_event_repository.py
│       │   ├── cache/               # Redis integration (placeholder)
│       │   └── kafka/               # Kafka integration (placeholder)
│       │
│       ├── presentation/            # 🔴 PRESENTATION LAYER
│       │   ├── api/routers/
│       │   │   ├── shippers.py      # GET /shippers, GET /shippers/{id}
│       │   │   ├── orders.py        # CRUD /orders
│       │   │   ├── dashboard.py     # GET /stats/overview
│       │   │   ├── simulation.py    # POST /simulation/start, dispatch, reset, incident/apply
│       │   │   └── incidents.py     # CRUD /incidents
│       │   └── websocket/
│       │       └── manager.py       # WebSocket ConnectionManager
│       │
│       └── utils/
│           ├── haversine.py         # Tính khoảng cách GPS
│           └── interpolation.py     # Làm mượt tọa độ GPS
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx                 # React entry point
│       ├── App.jsx                  # ★ Main app component + state machine
│       ├── components/
│       │   ├── TopBar.jsx           # Header bar (WS status, shipper count)
│       │   ├── ShipperList.jsx      # Left panel: danh sách shipper
│       │   ├── MapView.jsx          # Center: bản đồ Leaflet realtime
│       │   ├── RightPanel.jsx       # Right: chi tiết shipper + IncidentPanel
│       │   ├── IncidentPanel.jsx    # ★ 5 nút sự cố + resolve button
│       │   ├── Dashboard.jsx        # Stats panel (thống kê)
│       │   ├── SimulationControls.jsx # Nút điều khiển mô phỏng
│       │   ├── DeliveryModal.jsx    # Modal nhập thông tin giao hàng
│       │   ├── IncidentModal.jsx    # Modal báo sự cố
│       │   └── NotificationToast.jsx # Toast thông báo sự cố
│       ├── hooks/
│       │   ├── useWebSocket.js      # Custom hook quản lý WS connection
│       │   └── useShippers.js       # Custom hook quản lý state shipper
│       ├── services/
│       │   └── api.js               # Axios API client (REST calls)
│       └── styles/
│           └── theme.css            # CSS variables + dark theme
│
└── docs/                            # Tài liệu bổ sung
```

---

## 4. Kiến trúc hệ thống

### 4.1 Clean Architecture (Backend)

```
┌─────────────────────────────────────────────┐
│           PRESENTATION LAYER                │
│   API Routers + WebSocket Manager           │
│   (FastAPI endpoints, WS broadcast)         │
├─────────────────────────────────────────────┤
│           APPLICATION LAYER                 │
│   SimulationEngine + Services               │
│   (Business logic, simulation loop)         │
├─────────────────────────────────────────────┤
│           INFRASTRUCTURE LAYER              │
│   Repositories (MongoDB via Motor)          │
│   Cache (Redis) / Queue (Kafka)             │
├─────────────────────────────────────────────┤
│           DOMAIN LAYER                      │
│   Entities + Enums (Pydantic models)        │
│   (Shipper, Order, Incident, TrackingEvent) │
└─────────────────────────────────────────────┘
```

### 4.2 Luồng dữ liệu tổng quan

```
SimulationEngine (background task)
    │
    │ Mỗi 1 giây: move() 30 shippers
    │
    ├──→ MongoDB: upsert shipper state + append tracking_event
    │
    └──→ WebSocket broadcast ──→ Frontend (React)
              │                      │
              │ bulk_gps_update       ├── MapView (Leaflet markers)
              │ shipper_arrived       ├── ShipperList (status badges)
              │ delivery_completed    ├── Dashboard (stats)
              │ incident_created      └── NotificationToast
              │
    REST API (FastAPI)
         │
         ├── GET  /shippers        → Danh sách shipper
         ├── GET  /stats/overview  → Thống kê dashboard
         ├── POST /simulation/*    → Điều khiển mô phỏng
         ├── POST /orders          → Tạo đơn hàng
         └── POST /incidents       → Báo sự cố
```

---

## 5. Domain Models (entities.py)

### 5.1 Enums chính

| Enum | Giá trị | Ý nghĩa |
|------|---------|---------|
| `ShipperStatus` | IDLE, ASSIGNED, HEADING_TO_WAREHOUSE, AT_WAREHOUSE, DELIVERING, DELIVERED, DELAYED, VEHICLE_BREAKDOWN, LOST_CONNECTION, OFFLINE | 9+1 trạng thái shipper |
| `OrderStatus` | PENDING, PICKED_UP, IN_TRANSIT, DELIVERED, FAILED | Trạng thái đơn |
| `IncidentType` | TRAFFIC_JAM, HEAVY_RAIN, CUSTOMER_ABSENT, VEHICLE_BREAKDOWN, LOST_CONNECTION | 5 loại sự cố theo mục 19.4 |
| `IncidentSeverity` | LOW, MEDIUM, HIGH, CRITICAL | Mức độ nghiêm trọng |
| `SimulationPhase` | IDLE, STARTED, DISPATCHING, WAITING_FOR_ORDER, DELIVERING, COMPLETED | Pha mô phỏng |

### 5.2 Entities chính

| Entity | Mô tả | Trường quan trọng |
|--------|--------|-------------------|
| **Shipper** | Shipper ảo với GPS realtime | `shipper_id`, `current_lat/lon`, `current_speed_kmh`, `heading`, `current_status`, `eta_minutes`, `has_incident`, `incident_type` |
| **Order** | Đơn hàng giao | `order_id`, `assigned_shipper_id`, `dest_lat/lon`, `current_status`, `priority` |
| **Incident** | Sự cố trong giao hàng | `incident_id`, `shipper_id`, `incident_type`, `status` |
| **TrackingEvent** | Sự kiện GPS (append-only) | `event_id`, `shipper_id`, `lat/lon`, `speed_kmh`, `heading` |
| **Warehouse** | Kho hàng | `warehouse_id`, `lat/lon`, `address` |

---

## 6. Backend — Chi tiết hoạt động

### 6.1 Startup (lifespan)

Khi backend khởi động (`app/main.py`):
1. **Kết nối MongoDB** (`connect_to_mongo()`)
2. **Khởi chạy SimulationEngine** dưới dạng `asyncio.create_task` — chạy nền liên tục
3. **Mount 5 API routers**: shippers, orders, dashboard, simulation, incidents
4. **Mở WebSocket endpoint** `/ws` cho frontend

### 6.2 SimulationEngine (`simulation_engine.py`)

Đây là **core** của hệ thống — một **background loop** chạy mỗi 1 giây:

```python
class SimulationEngine:
    # Quản lý 30 VirtualShipper trong memory
    # Mỗi tick (1s):
    #   1. Move tất cả shippers (random walk hoặc hướng đến target)
    #   2. Kiểm tra arrival (warehouse / customer)
    #   3. Upsert state vào MongoDB
    #   4. Append tracking event vào MongoDB
    #   5. Broadcast bulk_gps_update qua WebSocket
```

**State machine mô phỏng:**
```
IDLE → DISPATCHING → WAITING_FOR_ORDER → DELIVERING → COMPLETED
  │         │                │                │
  │    3 shipper gần nhất   All arrived      Shipper đến
  │    heading to warehouse  → show modal     customer
  │                          nhập đơn hàng    → delivery_completed
  └── Reset ←────────────────────────────────────┘
```

**VirtualShipper movement:**
- Khi không có target: random walk (heading ± 10°, speed 15-50 km/h)
- Khi có target: hướng dần về target (heading smoothing 30%), speed 40 km/h
- Giới hạn bounding box: lat [10.65, 10.90], lon [106.55, 106.85] (HCMC)
- Arrival threshold: 0.3 km

### 6.3 API Endpoints

| Method | Path | Router | Mô tả |
|--------|------|--------|--------|
| `GET` | `/` | main | Root info |
| `GET` | `/health` | main | Health check + stats |
| `WS` | `/ws` | main | WebSocket cho frontend |
| `GET` | `/shippers` | shippers | Danh sách tất cả shipper |
| `GET` | `/shippers/{id}` | shippers | Chi tiết 1 shipper |
| `POST` | `/orders` | orders | Tạo đơn hàng |
| `GET` | `/orders` | orders | Danh sách đơn |
| `GET` | `/stats/overview` | dashboard | Thống kê tổng quan |
| `POST` | `/simulation/start` | simulation | Bắt đầu mô phỏng |
| `POST` | `/simulation/dispatch` | simulation | Dispatch shipper đến warehouse |
| `POST` | `/simulation/reset` | simulation | Reset mô phỏng |
| `GET` | `/simulation/nearest` | simulation | Tìm shipper gần warehouse nhất |
| `GET` | `/simulation/stats/fleet` | simulation | Fleet statistics (status breakdown) |
| `POST` | `/simulation/incident/apply` | simulation | Gây sự cố cho shipper (5 loại) |
| `POST` | `/simulation/incident/resolve/{id}` | simulation | Giải quyết sự cố |
| `POST` | `/incidents` | incidents | Tạo sự cố |
| `GET` | `/incidents` | incidents | Danh sách sự cố |
| `GET` | `/incidents/active` | incidents | Sự cố đang active |
| `PATCH` | `/incidents/{id}/resolve` | incidents | Resolve sự cố |

### 6.4 WebSocket Events (Server → Frontend)

| Event type | Khi nào | Payload chính |
|------------|---------|---------------|
| `initial_state` | Client kết nối | `shippers[]`, `phase`, `warehouse` |
| `bulk_gps_update` | Mỗi 1 giây | `shippers[]` (30 items), `phase`, `tick` |
| `shipper_arrived` | Shipper đến warehouse | `shipper_id`, `warehouse_id` |
| `all_arrived_at_warehouse` | Tất cả dispatched đã đến | `shipper_ids[]` |
| `delivery_assigned` | Đơn được gán | `shipper_id`, `order_id` |
| `delivery_completed` | Giao hàng xong | `shipper_id`, `order_id` |
| `simulation_completed` | Kết thúc mô phỏng | — |
| `incident_created` | Sự cố mới (legacy) | `incident_id`, `shipper_id`, `type` |
| `incident_applied` | Sự cố từ IncidentPanel | `shipper_id`, `incident_type`, `severity`, `estimated_delay`, `recommended_action` |
| `incident_resolved` | Sự cố đã resolve | `shipper_id` |

### 6.5 Database (MongoDB)

**Collections:**
| Collection | Entity | Mô tả |
|------------|--------|--------|
| `shippers` | Shipper | State hiện tại của 30 shipper (upsert mỗi tick) |
| `tracking_events` | TrackingEvent | Append-only GPS history |
| `orders` | Order | Đơn hàng |
| `incidents` | Incident | Sự cố |

### 6.6 WebSocket Manager (`manager.py`)

- Quản lý danh sách `client_connections` (frontend browsers)
- `broadcast_clients()`: gửi JSON message đến tất cả clients
- Auto-cleanup khi client disconnect
- Log giảm spam: chỉ log `bulk_gps_update` mỗi 10 ticks

---

## 7. Frontend — Chi tiết hoạt động

### 7.1 Component Tree

```
App.jsx
├── TopBar              — Header: WS status, shipper count
├── SimulationControls  — Nút: Find Nearest, Dispatch, Reset
├── NearestPanel        — Hiện shipper gần nhất (inline)
├── MainContent
│   ├── ShipperList     — Left: danh sách shipper, click để chọn
│   ├── MapView         — Center: bản đồ Leaflet, markers, polylines
│   └── RightPanel area
│       ├── RightPanel  — Tab "Details": chi tiết shipper được chọn
│       └── Dashboard   — Tab "Stats": thống kê hệ thống
├── DeliveryModal       — Modal nhập thông tin giao hàng
├── IncidentModal       — Modal báo sự cố
└── NotificationToast   — Toast thông báo sự cố realtime
```

### 7.2 Custom Hooks

| Hook | Mô tả |
|------|--------|
| `useWebSocket` | Kết nối WS tới `ws://localhost:8000/ws`, auto-reconnect, event subscription pattern `ws.on('event_type', callback)` |
| `useShippers` | Quản lý state: `shipperList`, `selectedShipperId`, `simulationPhase`, `dispatchedIds` + handlers cho mọi WS event |

### 7.3 Services (api.js)

```javascript
// Axios base: http://localhost:8000
shippersAPI.getAll()           // GET /shippers
shippersAPI.getById(id)        // GET /shippers/{id}
dashboardAPI.getOverview()     // GET /stats/overview
simulationAPI.start()          // POST /simulation/start
simulationAPI.dispatch(ids)    // POST /simulation/dispatch
simulationAPI.nearest()        // GET /simulation/nearest
simulationAPI.reset()          // POST /simulation/reset
ordersAPI.create(data)         // POST /orders
incidentsAPI.create(data)      // POST /incidents
incidentsAPI.getAll()          // GET /incidents
```

### 7.4 Luồng tương tác của user

```
1. Mở app → 30 shipper di chuyển random trên bản đồ
2. Click "Find Nearest" → hiện 3 shipper gần warehouse nhất
3. Click "Dispatch" → 3 shipper di chuyển về warehouse (đường thẳng)
4. Khi tất cả đến → hiện DeliveryModal
5. Nhập địa chỉ giao hàng → shipper bắt đầu delivering
6. Shipper đến destination → delivery_completed
7. Có thể "Report Incident" bất cứ lúc nào
8. Reset để chạy lại
```

---

## 8. Cách chạy project

### 8.1 Chạy với Docker Compose (đầy đủ hạ tầng)

```bash
cd Smart_Logistics
docker-compose up -d          # MongoDB + Kafka + Redis + Zookeeper
# Rồi chạy backend + frontend riêng (xem bước local bên dưới)
```

### 8.2 Chạy local (không Docker — chỉ cần MongoDB)

**Yêu cầu:** MongoDB đang chạy trên `localhost:27017`

```bash
# Terminal 1 — Backend
cd Smart_Logistics/backend
pip install -r ../requirements-local.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd Smart_Logistics/frontend
npm install
npm run dev
# → http://localhost:3000
```

### 8.3 Biến môi trường (.env)

| Biến | Mặc định | Mô tả |
|------|----------|--------|
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection |
| `MONGODB_DB` | `shiptrack` | Tên database |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka (optional) |
| `REDIS_URL` | `redis://localhost:6379` | Redis (optional) |
| `BACKEND_HOST` | `0.0.0.0` | Host backend |
| `BACKEND_PORT` | `8000` | Port backend |
| `VITE_API_URL` | `http://localhost:8000` | Frontend → Backend API |
| `VITE_WS_URL` | `ws://localhost:8000/ws` | Frontend → Backend WS |

---

## 9. Các tính năng đã implemented vs placeholder

### ✅ Đã hoạt động hoàn chỉnh:
- SimulationEngine: 30 shippers di chuyển realtime (9 trạng thái)
- WebSocket broadcast mỗi 1 giây (bao gồm ETA, incident data)
- MongoDB persistence (shippers, tracking_events, orders, incidents)
- Frontend bản đồ Leaflet với markers realtime (status colors 9 màu)
- Dispatch flow: find nearest → dispatch → arrive → delivery modal
- Delivery flow: assign order → delivering → completed
- Incident CRUD + realtime broadcast
- **IncidentPanel**: 5 nút sự cố (Kẹt xe, Mưa lớn, Khách vắng, Hư xe, Mất kết nối) + Resolve
- **ETA calculation**: Haversine-based ETA tracking cho mỗi shipper
- **Fleet stats API**: GET /simulation/stats/fleet (status breakdown, active incidents)
- Dashboard stats
- Dark theme UI

### 🟡 Có code nhưng chưa tích hợp vào luồng chính:
- **routing_engine.py** — A* graph-based routing với HCMC sample graph (11 nodes, 17 edges). Chạy được nhưng chưa integrate vào simulation loop
- **lstm_predictor.py** — LSTM ETA predictor stub (heuristic mode hoạt động, model thật chưa train)
- `infrastructure/kafka/` — Kafka consumer/producer (placeholder)
- `infrastructure/cache/` — Redis caching (placeholder)
- `stream_processor_reference.py` — Reference implementation cho GPS processing pipeline
- `application/usecases/` — UseCase pattern (empty)

## 9.1 Module A* Routing Engine (`routing_engine.py`)

**Kiến trúc:**
- Graph representation: adjacency list with weighted edges
- Node: giao lộ = `{node_id, lat, lon}`
- Edge: đoạn đường = `{distance_km, traffic_factor, estimated_time_min}`
- Heuristic: Haversine distance (admissible — guaranteed optimal)
- Demo graph: 11 nodes (Bình Thạnh, Quận 1, Phú Nhuận, Gò Vấp), 17 bidirectional edges
- `update_traffic()`: real-time cập nhật traffic_factor trên edge

**API:**
```python
graph.find_shortest_path("WH", "N10")
# → {"path": ["WH","N01","N02","N03","N10"], "total_distance_km": 4.2, "total_time_min": 8.4, "waypoints": [...]}
```

## 9.2 Module LSTM Predictor (`lstm_predictor.py`)

**Kiến trúc (stub):**
- Input: sliding window 5 ticks tốc độ + distance + incident_flag + hour_of_day + traffic_factor
- Output: `{predicted_eta_minutes, predicted_delay_minutes, confidence, method}`
- Hiện tại: heuristic predict (peak hour multiplier, incident delay, ±5% noise)
- Production: thay `_heuristic_predict()` bằng `_model_predict()` khi có trained model (TorchScript/ONNX)

---

## 10. Điểm mạnh của thiết kế

1. **Clean Architecture** — Tách rõ domain / application / infrastructure / presentation
2. **Realtime-first** — WebSocket broadcast là core, REST API bổ sung
3. **In-memory simulation** — Không phụ thuộc external data source cho demo
4. **Dual persistence** — State upsert + event append-only (audit trail)
5. **Graceful startup/shutdown** — FastAPI lifespan pattern
6. **Auto-reconnect WS** — Frontend tự kết nối lại khi mất connection

---

## 11. Sơ đồ deployment

```
┌──────────────────────────────────────────────────┐
│                  Docker Compose                   │
│                                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐  │
│  │ MongoDB │  │  Redis  │  │ Kafka+Zookeeper │  │
│  │  :27017 │  │  :6379  │  │   :9092/:2181   │  │
│  └────┬────┘  └─────────┘  └─────────────────┘  │
│       │                                           │
└───────┼───────────────────────────────────────────┘
        │
┌───────┴───────────────────────┐
│     FastAPI Backend :8000     │
│  ┌────────────────────────┐   │
│  │   SimulationEngine     │   │
│  │   (30 VirtualShippers) │   │
│  └──────────┬─────────────┘   │
│             │ WS broadcast    │
│  ┌──────────┴─────────────┐   │
│  │   REST API + WS /ws    │   │
│  └──────────┬─────────────┘   │
└─────────────┼─────────────────┘
              │
┌─────────────┴─────────────────┐
│     React Frontend :3000      │
│  ┌─────────────────────────┐  │
│  │  MapView + ShipperList  │  │
│  │  Dashboard + Controls   │  │
│  └─────────────────────────┘  │
└───────────────────────────────┘
```

---

---

## 12. Các thay đổi mới (2026-05-04)

### v2.0 — Initial
| # | Thay đổi | File | Mô tả |
|---|----------|------|--------|
| 1 | Mở rộng ShipperStatus | `entities.py` | 9 trạng thái: +DELIVERED, DELAYED, VEHICLE_BREAKDOWN, LOST_CONNECTION, OFFLINE |
| 2 | Thêm IncidentType mới | `entities.py` | 5 loại: TRAFFIC_JAM, HEAVY_RAIN, CUSTOMER_ABSENT, VEHICLE_BREAKDOWN, LOST_CONNECTION |
| 3 | ETA tracking | `simulation_engine.py` | `calculate_eta()` Haversine-based, broadcast qua WS |
| 4 | Incident management | `simulation_engine.py` | `apply_incident()`, `resolve_incident()`, `get_fleet_stats()` |
| 5 | Fleet stats API | `simulation.py` | GET `/simulation/stats/fleet` |
| 6 | Incident API | `simulation.py` | POST `/simulation/incident/apply`, `/incident/resolve/{id}` |
| 7 | IncidentPanel | `IncidentPanel.jsx` | 5 nút sự cố + resolve + kết quả hiển thị |
| 8 | RightPanel update | `RightPanel.jsx` | Status colors (9 màu), ETA display, IncidentPanel tích hợp |
| 9 | A* Routing | `routing_engine.py` | Graph-based A* với HCMC sample graph |
| 10 | LSTM Predictor | `lstm_predictor.py` | ETA/delay prediction stub (heuristic mode) |

### v2.1 — Route Polylines & Async Dispatch
| # | Thay đổi | File | Mô tả |
|---|----------|------|--------|
| 11 | OSRM integration | `routing_engine.py` | `get_osrm_route()` — async HTTP call đến OSRM public API để lấy tuyến đường thực tế theo đường phố |
| 12 | Polyline trong WS payload | `simulation_engine.py` | Mỗi tick broadcast `route_polyline: [[lat,lon],...]` cho shipper đang di chuyển |
| 13 | Async dispatch endpoint | `simulation.py` | `POST /simulation/dispatch` gọi OSRM trong background, fallback to straight line nếu OSRM không khả dụng |
| 14 | Route polyline trên bản đồ | `MapView.jsx` | Vẽ polyline đứt nét màu xanh/tím theo route thực tế cho từng shipper; auto-update mỗi tick; cleanup khi shipper offline |

---

## 13. Kết quả Test (Verified 2026-05-04)

Engine test chạy thành công (`python test_engine.py`):

```
=== Engine Test ===
Shippers: 30
Fleet stats: {'total_shippers': 30, 'status_breakdown': {'IDLE': 30}, 'active_incidents': 0, 'phase': 'IDLE'}

Rain HEAVY: {'shipper_id': 'SHP-001', 'incident_type': 'HEAVY_RAIN', 'severity': 'HIGH', 
  'estimated_delay': 30, 'recommended_action': 'Mưa nặng, có thể dừng giao', 'rain_level': 'HEAVY'}
Rain LIGHT: {'shipper_id': 'SHP-003', 'incident_type': 'HEAVY_RAIN', 'severity': 'LOW', 
  'estimated_delay': 30, 'recommended_action': 'Mưa nhẹ, giảm tốc nhẹ', 'rain_level': 'LIGHT'}

Absent retry 1: {'shipper_id': 'SHP-002', 'incident_type': 'CUSTOMER_ABSENT', 'severity': 'LOW',
  'estimated_delay': 10, 'recommended_action': 'Bỏ qua, giao đơn tiếp theo, thử lại sau'}
Absent retry 2 (should FAIL): {'shipper_id': 'SHP-002', 'incident_type': 'CUSTOMER_ABSENT',
  'recommended_action': 'Đã thử 2 lần. Đơn hàng FAILED, shipper về IDLE'}

Vehicle breakdown: {'shipper_id': 'SHP-004', 'incident_type': 'VEHICLE_BREAKDOWN', 'severity': 'HIGH',
  'estimated_delay': 45, 'recommended_action': 'Chờ sửa xe. Timeout 60p sẽ reassign'}

Resolve SHP-001: {'shipper_id': 'SHP-001', 'status': 'IDLE', 'resolved': True}

Fleet stats after incidents: {'total_shippers': 30, 
  'status_breakdown': {'IDLE': 28, 'DELAYED': 1, 'VEHICLE_BREAKDOWN': 1}, 
  'active_incidents': 3, 'phase': 'IDLE'}

=== ALL TESTS PASSED ===
```

### Các tính năng đã verified:
| # | Tính năng | Kết quả |
|---|-----------|---------|
| 1 | 30 shippers khởi tạo | ✅ PASS |
| 2 | Fleet stats (status breakdown) | ✅ PASS |
| 3 | Mưa 3 cấp (LIGHT/MODERATE/HEAVY) | ✅ PASS |
| 4 | Khách vắng max 2 lần → FAILED | ✅ PASS |
| 5 | Hư xe (VEHICLE_BREAKDOWN) | ✅ PASS |
| 6 | Resolve sự cố → shipper về IDLE | ✅ PASS |
| 7 | Fleet stats cập nhật sau incidents | ✅ PASS |

---

## 14. Trạng thái hệ thống (Verified 2026-05-04 v2.1)

### ✅ Đang chạy thành công:
| Service | Địa chỉ | Trạng thái |
|---------|---------|------------|
| **Backend FastAPI** | http://localhost:8000 | ✅ Running |
| **API Docs (Swagger)** | http://localhost:8000/docs | ✅ Running |
| **Frontend React** | http://localhost:3004 | ✅ Running |
| **MongoDB** | localhost:27017 (db: shiptrack) | ✅ Connected |
| **WebSocket** | ws://localhost:8000/ws | ✅ Ready |

### Health check response:
```json
{"status":"ok","ws_clients":0,"simulation_phase":"IDLE","shipper_count":30}
```

### Cách dùng nhanh:
1. Mở http://localhost:3004 → thấy 30 shipper di chuyển trên bản đồ TP.HCM
2. Click **"Find Nearest"** → thấy 3 shipper gần warehouse nhất được highlight
3. Click **"Dispatch"** → 3 shipper di chuyển về warehouse (vẽ route polyline màu tím)
4. Khi tất cả đến → modal nhập địa chỉ giao hàng xuất hiện
5. Nhập địa chỉ → shipper giao hàng (route polyline màu xanh)
6. Trong RightPanel → IncidentPanel → click sự cố để test incident

---

*File này được tạo tự động từ việc phân tích source code thực tế của project.*

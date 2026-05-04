# Tổng quan source code Smart_Logistics

## 1. Mục đích project

`Smart_Logistics` là hệ thống **theo dõi shipper thời gian thực** tên **ShipTrack**.  
Project triển khai theo hướng **clean architecture**, gồm backend FastAPI, frontend React/Vite và hạ tầng Docker Compose.

Theo tài liệu trong `README.md`, mục tiêu chính của hệ thống là:

- theo dõi vị trí shipper theo thời gian thực
- hiển thị dashboard bản đồ
- quản lý đơn hàng
- broadcast dữ liệu qua WebSocket
- mô phỏng shipper ảo để test luồng realtime

---

## 2. Công nghệ sử dụng

### Backend
- FastAPI
- Uvicorn
- Motor / PyMongo
- Redis async
- Confluent Kafka
- Pydantic / pydantic-settings
- WebSockets

### Frontend
- React 18
- Vite
- Axios
- Leaflet

### Infrastructure
- Docker Compose
- MongoDB 7
- Kafka 7.5 + Zookeeper
- Redis 7.2

---

## 3. Cấu trúc thư mục chính

```text
Smart_Logistics/
├── README.md
├── SETUP.md
├── docker-compose.yml
├── .env.example
├── main.py
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── main.py
│   │   ├── stream_processor_reference.py
│   │   ├── application/
│   │   ├── domain/
│   │   ├── infrastructure/
│   │   ├── presentation/
│   │   └── utils/
│   ├── data_generator/
│   │   └── simulate.py
│   └── scripts/
│       └── init_db.js
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── components/
│       ├── hooks/
│       ├── services/
│       └── styles/
└── docs/
```

---

## 4. Kiến trúc tổng thể

Tài liệu mô tả project theo mô hình:

```text
Domain Layer
   ↓
Application Layer
   ↓
Infrastructure Layer
   ↓
Presentation Layer
```

### Ý nghĩa từng layer

#### Domain
Chứa business entities cốt lõi.  
Trong project có file:

- `backend/app/domain/entities.py`

Đây là nơi nên chứa các model nghiệp vụ như shipper, order, tracking event.

#### Application
Chứa service/use-case điều phối logic nghiệp vụ.  
Thư mục:

- `backend/app/application/services/`
- `backend/app/application/usecases/`

Backend `main.py` đang dùng:
- `simulation_engine`

=> cho thấy application layer đang điều phối luồng mô phỏng shipper.

#### Infrastructure
Chứa phần truy cập dữ liệu và tích hợp hệ thống ngoài:
- repositories
- cache
- kafka

Thư mục:
- `backend/app/infrastructure/repositories/`
- `backend/app/infrastructure/cache/`
- `backend/app/infrastructure/kafka/`

#### Presentation
Chứa API và WebSocket phục vụ frontend:
- `backend/app/presentation/api/`
- `backend/app/presentation/websocket/`

---

## 5. Backend hoạt động như thế nào

File quan trọng nhất của backend là:

- `backend/app/main.py`

### Những gì backend khởi tạo
Từ nội dung file này, backend sẽ:

1. kết nối MongoDB
2. khởi chạy simulation engine nền
3. mount các API router
4. mở WebSocket endpoint cho frontend

### Các endpoint chính thấy được
Trong `backend/app/main.py` có:

- `GET /`
- `GET /health`
- `WS /ws`

Ngoài ra backend còn include router từ:

- `shippers`
- `orders`
- `dashboard`
- `simulation`
- `incidents`

Theo `SETUP.md`, hệ thống còn có các nhóm API như:
- `/shippers`
- `/orders`
- `/stats/...`
- `/simulation/...`

### Health check
`GET /health` trả về:
- trạng thái backend
- số client websocket
- phase mô phỏng
- số shipper trong engine

### WebSocket
`WS /ws` dùng cho frontend browser nhận dữ liệu realtime.

Các event được mô tả trong code gồm:
- `initial_state`
- `bulk_gps_update`
- `shipper_arrived`
- `all_arrived_at_warehouse`
- `delivery_assigned`
- `delivery_completed`
- `simulation_completed`
- `incident_created`
- `incident_resolved`

---

## 6. Frontend hoạt động như thế nào

### Entry point
- `frontend/src/main.jsx`
- `frontend/src/App.jsx`

### Các thành phần giao diện
Trong `frontend/src/components/` có các component chính:

- `Dashboard.jsx`
- `DeliveryModal.jsx`
- `IncidentModal.jsx`
- `MapView.jsx`
- `NotificationToast.jsx`
- `RightPanel.jsx`
- `ShipperList.jsx`
- `SimulationControls.jsx`
- `TopBar.jsx`

Từ tên file có thể thấy frontend có:
- dashboard tổng quan
- danh sách shipper
- bản đồ
- modal giao đơn / sự cố
- thông báo realtime
- control mô phỏng

### Hooks
- `hooks/useShippers.js`
- `hooks/useWebSocket.js`

=> frontend có custom hooks để:
- quản lý trạng thái shipper
- kết nối WebSocket realtime

### Service
- `services/api.js`

=> nơi gọi REST API backend.

### Build scripts
Trong `frontend/package.json` có:
- `npm run dev`
- `npm run build`
- `npm run preview`
- `npm run lint`

---

## 7. Docker Compose gồm những service nào

Theo `docker-compose.yml`, hệ thống có các service:

- `zookeeper`
- `kafka`
- `mongodb`
- `redis`
- `backend`
- `simulator`
- `frontend`

### Port mapping
- Frontend: `3000`
- Backend: `8000`
- MongoDB: `27017`
- Kafka host: `9092`
- Redis: `6379`

### Môi trường runtime quan trọng
Backend dùng:
- `KAFKA_BOOTSTRAP_SERVERS=kafka:29092`
- `MONGODB_URL=mongodb://mongodb:27017`
- `REDIS_URL=redis://redis:6379`

Frontend dùng:
- `VITE_API_URL=http://localhost:8000`
- `VITE_WS_URL=ws://localhost:8000/ws`

---

## 8. Cách chạy project

## Cách 1: Docker Compose
Theo tài liệu:

```powershell
cd Smart_Logistics
Copy-Item .env.example .env
docker compose up -d
```

Sau đó truy cập:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

Chạy simulator:
```powershell
docker compose --profile simulator up simulator
```

## Cách 2: Local development
### Backend
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-local.txt
docker compose up -d mongodb kafka redis zookeeper
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

---

## 9. Trạng thái kiểm tra thực tế trên máy hiện tại

### Đã kiểm tra được
Tôi đã chạy:

```powershell
cd Smart_Logistics/frontend
npm run build
```

Kết quả:
- frontend **build thành công**
- Vite tạo ra bundle production bình thường

Điều này cho thấy:
- source frontend hợp lệ
- dependency frontend đã có thể sử dụng
- cấu trúc React/Vite không bị lỗi build tại thời điểm kiểm tra

### Chưa chạy được toàn bộ Docker stack
Khi chạy:

```powershell
docker compose up -d
```

máy báo lỗi kết nối Docker engine:

```text
unable to get image 'confluentinc/cp-zookeeper:7.5.0' ...
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

### Kết luận nguyên nhân
Lỗi này cho thấy:
- Docker Desktop hoặc Docker Linux engine **chưa chạy**
- vì vậy chưa thể xác minh full stack backend + database + kafka + redis bằng Docker trên máy hiện tại

---

## 10. Nhận xét kỹ thuật

### Điểm mạnh
- cấu trúc thư mục rõ ràng
- có chia layer theo clean architecture
- có tài liệu README và SETUP khá đầy đủ
- có frontend realtime rõ ràng theo component
- backend có WebSocket và health check
- hỗ trợ Docker Compose cho full môi trường

### Điểm cần lưu ý
- `docker-compose.yml` vẫn có thuộc tính `version`, Docker hiện cảnh báo là obsolete
- ✅ **Chốt chính thức: Demo dùng 30 shipper.** Code thực tế trong `main.py` log `Simulation engine started (30 shippers)`. README gốc ghi 100 shipper là **sai**, cần cập nhật lại README thành 30 shipper.
- muốn chạy full project bắt buộc cần Docker engine hoạt động

---

## 11. Đề xuất để chạy thành công trên máy này

1. mở **Docker Desktop**
2. chờ Docker engine khởi động xong
3. chạy lại:

```powershell
cd Smart_Logistics
docker compose up -d
docker compose ps
```

4. nếu các service đã lên, chạy simulator:

```powershell
docker compose --profile simulator up simulator
```

5. mở:
- http://localhost:3000
- http://localhost:8000/docs

---

## 12. Kết luận ngắn

`Smart_Logistics` là một project realtime logistics khá hoàn chỉnh, gồm:

- backend FastAPI
- frontend React/Vite
- MongoDB + Kafka + Redis
- WebSocket realtime
- simulator shipper ảo
- cấu trúc clean architecture

Hiện tại:
- **frontend build OK**
- **full project chưa start được** do **Docker Desktop/engine chưa chạy**

File này được tạo để dùng như bản tổng quan nhanh khi đọc source code.

---

## 13. Chi tiết cấu trúc & chức năng từng thành phần

### 13.1 Frontend — Cấu trúc component

```text
App.jsx                        ← Root component, state machine chính
├── TopBar.jsx                 ← Header: logo, trạng thái WS, số lượng shipper
├── SimulationControls.jsx     ← Nút điều khiển theo phase (Start/Find Nearest/Reset)
├── [nearestPanel]             ← Hiện danh sách shipper gần nhất (inline trong App)
├── ShipperList.jsx            ← Sidebar trái: danh sách shipper, click để chọn
├── MapView.jsx                ← Bản đồ Leaflet: marker shipper + warehouse
├── RightPanel.jsx             ← Sidebar phải tab "Details": thông tin shipper đang chọn
├── Dashboard.jsx              ← Sidebar phải tab "Stats": thống kê fleet overview
├── DeliveryModal.jsx          ← Modal giao đơn: hiện khi tất cả shipper đến kho
├── IncidentModal.jsx          ← Modal báo sự cố cho shipper đang giao
├── IncidentPanel.jsx          ← Sidebar trái: bảng 5 nút sự cố (kẹt xe/mưa/khách vắng/hư xe/mất kết nối)
└── NotificationToast.jsx      ← Toast popup khi có incident mới
```

### 13.2 Frontend — Custom hooks

| Hook | Chức năng |
|------|-----------|
| `useWebSocket` | Kết nối WS, tự động reconnect 3s, pub/sub theo event type |
| `useShippers` | State management cho Map<shipper_id, shipper>, xử lý tất cả WS event |

### 13.3 Frontend — API Service (`services/api.js`)

| Module | Endpoint | Mô tả |
|--------|----------|-------|
| `shippersAPI.getAll` | `GET /shippers` | Lấy tất cả shipper |
| `shippersAPI.getById` | `GET /shippers/:id` | Chi tiết 1 shipper |
| `shippersAPI.getHistory` | `GET /shippers/:id/history` | Lịch sử GPS shipper |
| `ordersAPI.getAll` | `GET /orders` | Tất cả đơn hàng |
| `ordersAPI.getPending` | `GET /orders/pending` | Đơn chờ xử lý |
| `ordersAPI.create` | `POST /orders` | Tạo đơn mới |
| `ordersAPI.assign` | `PATCH /orders/:id/assign` | Gán shipper cho đơn |
| `ordersAPI.complete` | `PATCH /orders/:id/complete` | Hoàn thành đơn |
| `ordersAPI.bulkImport` | `POST /orders/bulk-import` | Import hàng loạt |
| `dashboardAPI.getOverview` | `GET /stats/overview` | Thống kê tổng quan |
| `dashboardAPI.getFleetStats` | `GET /stats/fleet` | Thống kê fleet |
| `simulationAPI.start` | `POST /simulation/start` | Bắt đầu mô phỏng |
| `simulationAPI.getState` | `GET /simulation/state` | Trạng thái hiện tại |
| `simulationAPI.getNearest` | `GET /simulation/nearest?top_n=3` | Tìm shipper gần kho |
| `simulationAPI.dispatch` | `POST /simulation/dispatch` | Điều shipper về kho |
| `simulationAPI.assignDelivery` | `POST /simulation/assign-delivery` | Gán đơn giao cho shipper |
| `simulationAPI.reset` | `POST /simulation/reset` | Reset toàn bộ mô phỏng |
| `incidentsAPI.getAll` | `GET /incidents` | Tất cả sự cố |
| `incidentsAPI.getActive` | `GET /incidents/active` | Sự cố đang mở |
| `incidentsAPI.create` | `POST /incidents` | Báo sự cố mới |
| `incidentsAPI.resolve` | `PATCH /incidents/:id/resolve` | Giải quyết sự cố |

### 13.4 Backend — Routers (Presentation Layer)

```text
backend/app/presentation/
├── api/routers/
│   ├── shippers.py        ← CRUD shipper, lịch sử GPS
│   ├── orders.py          ← CRUD đơn hàng, assign, complete
│   ├── dashboard.py       ← Thống kê overview, fleet stats
│   ├── simulation.py      ← Điều khiển simulation engine
│   └── incidents.py       ← Quản lý sự cố
└── websocket/
    └── manager.py         ← WebSocket manager: broadcast events đến tất cả client
```

### 13.5 Backend — Simulation Engine

File: `backend/app/application/services/simulation_engine.py`

Simulation engine là **trái tim** của hệ thống demo. Nó:
- tạo 30 shipper ảo với vị trí ngẫu nhiên quanh TP.HCM
- mỗi tick (1 giây) cập nhật tọa độ GPS cho từng shipper
- tính khoảng cách đến kho bằng Haversine formula
- phát hiện shipper đã đến kho
- điều phối giao đơn: shipper di chuyển từ kho đến điểm đích
- phát hiện giao hàng xong
- broadcast tất cả sự kiện qua WebSocket

### 13.6 Backend — Infrastructure Layer

```text
infrastructure/
├── repositories/          ← MongoDB data access
│   ├── shipper_repo.py    ← CRUD shipper trong MongoDB
│   └── order_repo.py      ← CRUD đơn hàng trong MongoDB
├── cache/
│   └── redis_cache.py     ← Cache vị trí shipper realtime trong Redis
└── kafka/
    └── producer.py        ← Gửi tracking event vào Kafka topic
```

### 13.7 Backend — Domain Layer

File: `backend/app/domain/entities.py`

Chứa các Pydantic model/entity cốt lõi:
- Shipper (id, tên, vị trí, trạng thái, tốc độ)
- Order (id, shipper, trạng thái, điểm đầu/cuối)
- Incident (id, shipper, loại sự cố, trạng thái)

### 13.8 Backend — Utils

```text
utils/
├── haversine.py       ← Tính khoảng cách giữa 2 tọa độ GPS (km)
└── interpolation.py   ← Nội suy vị trí trung gian để shipper "di chuyển mượt"
```

---

## 14. Flow hoạt động chính của Web Application

### 14.1 Flow tổng quan (State Machine)

```text
                 ┌──────────────────────────────────────────────┐
                 │                                              │
   ┌─────┐  Start   ┌─────────┐  Find Nearest  ┌────────────┐ │
   │ IDLE │────────→│ STARTED │───────────────→│ (hiện list) │ │
   └─────┘         └─────────┘                └──────┬───────┘ │
      ↑                                              │         │
      │                                    Dispatch   │         │
      │                                              ↓         │
      │                                    ┌──────────────┐    │
      │              Reset                 │ DISPATCHING  │    │
      │←──────────────────────────────────│  (về kho)     │    │
      │                                    └──────┬───────┘    │
      │                                           │            │
      │                              All arrived  │            │
      │                                           ↓            │
      │                                ┌───────────────────┐   │
      │                                │ WAITING_FOR_ORDER │   │
      │                                │  (hiện modal)     │   │
      │                                └────────┬──────────┘   │
      │                                         │              │
      │                          Assign delivery │              │
      │                                         ↓              │
      │                                  ┌────────────┐        │
      │              Reset               │ DELIVERING │        │
      │←────────────────────────────────│  (giao đơn) │        │
      │                                  └──────┬─────┘        │
      │                                         │              │
      │                       Delivery complete  │              │
      │                                         ↓              │
      │                                  ┌───────────┐         │
      │              Reset               │ COMPLETED │         │
      │←────────────────────────────────│             │─────────┘
                                         └───────────┘
```

### 14.2 Flow chi tiết từng bước

#### Bước 1: Khởi tạo (IDLE)
1. User mở trang web → frontend kết nối WS tới `ws://localhost:8000/ws`
2. Frontend gọi `GET /shippers` lấy 30 shipper ban đầu
3. Backend gửi event `initial_state` qua WS
4. Bản đồ Leaflet hiển thị 30 marker shipper rải rác quanh TP.HCM
5. Warehouse marker (vàng) hiện tại 02 Võ Oanh, Bình Thạnh

#### Bước 2: Start Simulation (STARTED)
1. User bấm nút **🚀 Bắt đầu giao hàng**
2. Frontend gọi `POST /simulation/start`
3. Backend đổi phase → `STARTED`
4. Simulation engine bắt đầu tick mỗi 1s: cập nhật GPS 30 shipper
5. Backend broadcast `bulk_gps_update` qua WS mỗi tick
6. Frontend nhận → cập nhật vị trí marker trên bản đồ (realtime)
7. Nút đổi thành **🔍 Tìm 3 shipper gần kho nhất**

#### Bước 3: Tìm shipper gần nhất
1. User bấm nút **🔍 Tìm 3 shipper gần kho nhất**
2. Frontend gọi `GET /simulation/nearest?top_n=3`
3. Backend tính khoảng cách Haversine từ mỗi shipper đến kho
4. Trả về 3 shipper gần nhất kèm distance (km)
5. Frontend hiện panel danh sách: "SHP-001 (2.3km), SHP-015 (3.1km), ..."
6. User bấm **🚚 Dispatch to Warehouse**

#### Bước 4: Dispatch về kho (DISPATCHING)
1. Frontend gọi `POST /simulation/dispatch` với danh sách shipper_ids
2. Backend đổi phase → `DISPATCHING`, broadcast event `dispatch_started`
3. Simulation engine di chuyển các shipper được chọn hướng về kho
4. Mỗi tick: shipper tiến gần kho hơn, WS broadcast `bulk_gps_update`
5. Khi một shipper đến kho: broadcast `shipper_arrived`, đổi status → `AT_WAREHOUSE`
6. Marker trên bản đồ đổi màu theo status mới

#### Bước 5: Tất cả đến kho (WAITING_FOR_ORDER)
1. Khi tất cả shipper dispatched đã đến: broadcast `all_arrived_at_warehouse`
2. Frontend đổi phase → `WAITING_FOR_ORDER`
3. **DeliveryModal** tự động hiện lên
4. User nhập thông tin đơn: điểm giao, tên, trọng lượng
5. User chọn shipper và bấm giao

#### Bước 6: Giao hàng (DELIVERING)
1. Frontend gọi `POST /simulation/assign-delivery`
2. Backend tạo order trong MongoDB, gán shipper
3. Broadcast `delivery_assigned` qua WS
4. Shipper bắt đầu di chuyển từ kho đến điểm giao
5. Bản đồ hiện shipper di chuyển (marker xanh lá)
6. Khi đến nơi: broadcast `delivery_completed`
7. Order được mark hoàn thành trong MongoDB

#### Bước 7: Hoàn thành / Reset
1. Tất cả giao xong → broadcast `simulation_completed`, phase → `COMPLETED`
2. User có thể bấm **🔄 Reset Simulation** bất kỳ lúc nào
3. Reset: xóa dữ liệu, tạo lại 30 shipper mới, phase → `IDLE`

### 14.3 Flow sự cố (Incident)

```text
User bấm "⚠️ Report Incident"
    → IncidentModal hiện lên
    → Chọn shipper đang DELIVERING
    → Nhập loại sự cố (hỏng xe, thời tiết, tai nạn...)
    → POST /incidents
    → Backend lưu MongoDB + broadcast "incident_created"
    → NotificationToast popup trên tất cả client
    → Admin có thể PATCH /incidents/:id/resolve
    → Broadcast "incident_resolved"
```

### 14.4 Flow realtime data

```text
┌──────────────┐     tick 1s      ┌──────────────────┐
│  Simulation  │ ───────────────→ │  WebSocket Mgr   │
│   Engine     │  bulk_gps_update │  (ws_manager)     │
│  (30 shipper)│                  │                   │
└──────────────┘                  └────────┬──────────┘
                                           │ broadcast
                                           ↓
                                  ┌──────────────────┐
                                  │  Browser Client   │
                                  │  (React App)      │
                                  │                   │
                                  │  useWebSocket     │
                                  │    ↓ on(type)     │
                                  │  useShippers      │
                                  │    ↓ setState     │
                                  │  MapView re-render│
                                  │  ShipperList      │
                                  └──────────────────┘
```

### 14.5 Flow dữ liệu lưu trữ

```text
Simulation Engine
    │
    ├──→ MongoDB (Motor async)
    │     ├── collection: shippers    ← vị trí, status, tốc độ
    │     ├── collection: orders      ← đơn hàng, gán shipper
    │     └── collection: incidents   ← sự cố
    │
    ├──→ Redis (async)
    │     └── cache vị trí GPS mới nhất (tốc độ truy xuất cao)
    │
    └──→ Kafka (optional)
          └── topic: tracking_events  ← ghi log GPS event cho phân tích sau
```

---

## 15. Bảng tổng hợp WebSocket Events

| Event Type | Hướng | Mô tả |
|------------|-------|-------|
| `initial_state` | Server → Client | Gửi toàn bộ trạng thái shipper khi client mới kết nối |
| `bulk_gps_update` | Server → Client | Cập nhật GPS tất cả shipper mỗi 1s |
| `dispatch_started` | Server → Client | Thông báo bắt đầu điều shipper về kho |
| `shipper_arrived` | Server → Client | Một shipper đã đến kho |
| `all_arrived_at_warehouse` | Server → Client | Tất cả shipper dispatched đã đến kho |
| `delivery_assigned` | Server → Client | Đơn hàng được gán cho shipper |
| `delivery_completed` | Server → Client | Shipper giao xong đơn |
| `simulation_completed` | Server → Client | Toàn bộ mô phỏng hoàn thành |
| `simulation_reset` | Server → Client | Mô phỏng được reset |
| `incident_created` | Server → Client | Sự cố mới được báo |
| `incident_resolved` | Server → Client | Sự cố được giải quyết |
| `system_alert` | Server → Client | Hệ thống tự phát hiện bất thường (tốc độ thấp, mất GPS...) — hỏi shipper |
| `customer_notification` | Server → Client | Thông báo đến khách hàng khi đơn bị delay |
| `route_updated` | Server → Client | Tuyến đường shipper được tính lại (sau sự cố kẹt xe/mưa) |
| `eta_updated` | Server → Client | ETA đơn hàng được cập nhật (kèm trong bulk_gps_update hoặc riêng) |

---

## 16. Bảng tổng hợp trạng thái Shipper

| Status | Màu trên bản đồ | Ý nghĩa |
|--------|-----------------|----------|
| `IDLE` | Xám (`--text2`) | Shipper đang rảnh, chưa được điều phối |
| `HEADING_TO_WAREHOUSE` | Tím (`--purple`) | Đang di chuyển về kho |
| `AT_WAREHOUSE` | Xanh dương (`--blue`) | Đã đến kho, chờ nhận đơn |
| `DELIVERING` | Xanh lá (`--green`) | Đang giao hàng |
| `DELIVERED` | Xanh lá (`--green`) | Giao xong |
| `OFFLINE` | Đỏ (`--red`) | Mất kết nối / sự cố |
| `VEHICLE_BREAKDOWN` | Đỏ (`--red`) + icon 🔧 | Shipper hư xe, chờ sửa (timeout 60p → reassign) |
| `LOST_CONNECTION` | Đỏ (`--red`) + icon ❓ | Mất kết nối GPS (timeout 60p → cảnh báo admin) |
| `DELAYED` | Cam (`--orange`) | Shipper đang bị delay do sự cố (kẹt xe/mưa/hư xe) |

---

## 17. Các nhóm chức năng chính của hệ thống (Bổ sung chi tiết)

### 17.0 Bản đồ thời gian thực

- Hiển thị vị trí **30 shipper ảo** trên bản đồ TP.HCM (thư viện **Leaflet**)
- Cập nhật vị trí liên tục mỗi **1 giây** qua WebSocket event `bulk_gps_update`
- Đổi màu marker theo trạng thái:
  - 🟣 Tím — `HEADING_TO_WAREHOUSE`
  - 🔵 Xanh dương — `AT_WAREHOUSE`
  - 🟢 Xanh lá — `DELIVERING` / `DELIVERED`
  - 🔴 Đỏ — `OFFLINE` / Sự cố
  - 🔴 Đỏ + 🔧 — `VEHICLE_BREAKDOWN` (hư xe)
  - 🔴 Đỏ + ❓ — `LOST_CONNECTION` (mất kết nối)
  - 🟠 Cam — `DELAYED` (đang bị delay do sự cố)
- Marker kho (vàng) tại **02 Võ Oanh, Bình Thạnh**
- Chuyển động mượt nhờ **Linear Interpolation** (nội suy vị trí trung gian, không "nhảy cóc")

### 17.1 Điều phối mô phỏng

- `POST /simulation/start` — engine tự động tick mỗi 1 giây
- `POST /simulation/reset` — xóa dữ liệu cũ, tạo lại 30 shipper mới
- `GET /simulation/nearest?top_n=3` — tìm shipper gần kho nhất
- `POST /simulation/dispatch` — điều shipper về kho
- `GET /simulation/state` — xem trạng thái mô phỏng

**Phân vai thuật toán (ĐÃ SỬA theo feedback):**

| Mục đích | Thuật toán | Ghi chú |
|----------|-----------|---------|
| Tính khoảng cách GPS | **Haversine** | Khoảng cách giữa 2 tọa độ trên mặt cầu |
| Làm mượt chuyển động | **Linear Interpolation** | Nội suy vị trí trung gian mỗi tick |
| Lọc nhiễu GPS | **Kalman Filter** | Loại bỏ jitter / nhiễu tín hiệu GPS |
| Dự đoán sự cố & ETA | **LSTM** | Dự đoán delay, đề xuất tuyến đường |
| Tìm đường ngắn nhất | **A\* (A-star)** | Trên graph đường phố (xem mục 18) |

**Routing trên bản đồ (ĐÃ BỔ SUNG theo feedback):**

- Shipper phải đi **đúng trên tuyến đường** của bản đồ, không đi xuyên nhà
- Các ngã 3, ngã 4 là **node** trên graph, nối nhau bằng đường thẳng (edge)
- Thuật toán tìm đường: **A\*** (A-star) — nhanh hơn Dijkstra nhờ heuristic
- Nguồn dữ liệu graph: dùng **OSRM (OpenStreetMap Routing Machine)** hoặc trích xuất từ OSM data để lấy graph đường thực tế quận Bình Thạnh
- Phạm vi: bán kính **5km** quanh 02 Võ Oanh (10.8051, 106.7144)
- Số lượng node ước tính: **200–500 node** (đủ tự nhiên, không quá nặng)
- Shipper được random tạo ra tại các node ngẫu nhiên trong vùng bán kính này

### 17.2 Quản lý đơn hàng

- Tạo đơn mới: điểm giao, tên, trọng lượng, kích thước kiện (`POST /orders`)
- Gán đơn cho shipper (`POST /simulation/assign-delivery`)
- Vòng đời đơn: `PENDING → PICKED_UP → IN_TRANSIT → DELIVERED`
- Import hàng loạt (`POST /orders/bulk-import`)
- Xem đơn chờ xử lý (`GET /orders/pending`)
- Lưu bằng chứng giao hàng POD — ảnh/chữ ký (`proof_of_delivery_ref`)

### 17.3 Quản lý sự cố

- Báo sự cố cho shipper đang giao (`POST /incidents`)
- Toast popup realtime qua WebSocket (`incident_created`)
- Giải quyết sự cố (`PATCH /incidents/:id/resolve`)
- Xem sự cố đang mở (`GET /incidents/active`)

### 17.4 Dashboard thống kê

- Tổng quan fleet: tổng shipper, phân bổ theo trạng thái (`GET /stats/fleet`)
- Thống kê đơn hàng: tổng, đang giao, hoàn thành, thất bại (`GET /stats/overview`)
- Hiệu suất: `completed_order_count`, `rating`, `performance_counts`

### 17.5 Quản lý shipper

- Sidebar trái: danh sách shipper, click xem chi tiết (`GET /shippers`)
- Lịch sử GPS (`GET /shippers/:id/history`)
- Realtime: vị trí, tốc độ (`current_speed_kmh`), hướng (`heading`), tín hiệu (`signal_status`), lần ping cuối (`last_ping_at`)
- Cache vị trí mới nhất trong **Redis**

### 17.6 Bảng nhập tình huống sự cố (Chi tiết)

→ Xem mục 19 bên dưới

---

## 18. Hệ thống Routing trên bản đồ (Graph-based)

### 18.1 Kiến trúc Graph

```text
┌──────────────────────────────────────────────────────┐
│              Quận Bình Thạnh — Bán kính 5km          │
│                                                      │
│    ●──────●──────●          ● = Node (ngã 3/4)       │
│    │      │      │          ─ = Edge (đoạn đường)    │
│    ●──────●──────●                                   │
│    │      │      │          ★ = Warehouse             │
│    ●──────★──────●              (02 Võ Oanh)         │
│    │      │      │                                   │
│    ●──────●──────●          🛵 = Shipper              │
│           │                     (random tại node)    │
│           ●                                          │
└──────────────────────────────────────────────────────┘
```

### 18.2 Quy trình tìm đường

```text
1. Shipper nhận đơn tại kho
2. Hệ thống xác định node gần điểm giao nhất
3. A* tìm đường ngắn nhất từ warehouse-node → destination-node
4. Shipper di chuyển theo chuỗi node (edge by edge)
5. Linear Interpolation nội suy vị trí giữa 2 node mỗi tick
6. Nếu gặp sự cố kẹt xe → A* tìm đường thay thế (tránh edge bị block)
```

### 18.3 Dữ liệu Graph

- **Nguồn**: OSRM (OpenStreetMap Routing Machine) hoặc trích xuất trực tiếp từ OSM data khu vực Bình Thạnh
- **Số lượng node**: ~200–500 (ngã 3, ngã 4, điểm chuyển hướng)
- **Lưu trữ**: JSON file hoặc MongoDB collection `road_graph`
- **Cấu trúc node**: `{ node_id, lat, lon, neighbors: [{ node_id, distance_m, travel_time_s }] }`

---

## 19. Bảng nhập sự cố — Định nghĩa chi tiết

### 19.1 Layout giao diện

```text
┌──────────────────┬────────────────────┬──────────────────┐
│  BẢNG SỰ CỐ     │     BẢN ĐỒ MAP    │  THÔNG TIN       │
│  (sidebar trái)  │     (Leaflet)      │  REALTIME         │
│                  │                    │  (sidebar phải)   │
│  [🚗 Kẹt xe]    │                    │                   │
│  [🌧️ Mưa lớn]  │    🛵  🛵         │  Shipper: SHP-001 │
│  [👤 Khách vắng] │       ★           │  Status: DELAY    │
│  [🔧 Hư xe]     │    🛵      🛵     │  ETA: +15 phút    │
│  [🔋 Hết pin]   │                    │  Speed: 0 km/h    │
│                  │                    │                   │
└──────────────────┴────────────────────┴──────────────────┘
```

### 19.2 Cơ chế hoạt động

- Mỗi loại sự cố là **1 nút bấm** với data mặc định đã định sẵn
- User chỉ cần: **chọn shipper → bấm nút sự cố** → data tự động điền
- Hệ thống lập tức cập nhật realtime thông tin shipper

### 19.3 Schema bảng nhập sự cố (8 fields)

| # | Field | Kiểu | Mô tả | Giá trị mặc định theo nút |
|---|-------|------|-------|--------------------------|
| 1 | `shipper_id` | string | Shipper gặp sự cố | Auto-detect (đang chọn) hoặc chọn từ list |
| 2 | `incident_type` | enum | Loại sự cố | Theo nút bấm: `TRAFFIC_JAM`, `HEAVY_RAIN`, `CUSTOMER_ABSENT`, `VEHICLE_BREAKDOWN`, `LOST_CONNECTION` |
| 3 | `severity` | enum | Mức độ nghiêm trọng | `LOW` / `MEDIUM` / `HIGH` — auto theo loại |
| 4 | `location` | object | Vị trí xảy ra | `{ lat, lon }` — lấy từ GPS realtime |
| 5 | `description` | string | Mô tả thêm | Template text mặc định, có thể sửa |
| 6 | `estimated_delay` | int | Ước tính delay (phút) | LSTM tự điền dựa trên lịch sử |
| 7 | `recommended_action` | string | Hành động gợi ý | Hệ thống tự đề xuất (xem mục 19.4) |
| 8 | `timestamp` | datetime | Thời điểm xảy ra | Auto — `datetime.utcnow()` |

### 19.4 Xử lý từng loại sự cố (Chi tiết)

#### Sự cố 1: 🚗 Kẹt xe / Tắc đường

```text
Trigger:
  - User bấm nút "Kẹt xe" HOẶC
  - Hệ thống tự phát hiện: tốc độ < 5 km/h liên tục > 3 phút
    → Gửi thông báo hỏi shipper: "Bạn đang gặp vấn đề gì?"
    → Shipper xác nhận: Kẹt xe

Xử lý:
  1. Đánh dấu edge hiện tại trên graph là BLOCKED (trọng số tăng 10x)
  2. A* tìm đường thay thế ngắn nhất (tránh edge bị block)
  3. Hiển thị trên map: đoạn đường kẹt = ĐƯỜNG ĐỎ
  4. Cập nhật ETA: tăng thời gian giao dựa trên độ dài đường mới
  5. Shipper tự động chuyển sang tuyến đường mới
  6. Lưu data vào DB: { edge_id, time_of_day, day_of_week, congestion_level }
  7. LSTM học từ data này → lần sau tránh edge đó vào khung giờ tương tự

Default data khi bấm nút:
  - severity: MEDIUM
  - estimated_delay: 15 phút (LSTM điều chỉnh)
  - action: "Đang tìm đường thay thế..."
```

#### Sự cố 2: 🌧️ Mưa lớn / Ngập đường

```text
Trigger:
  - User bấm nút "Mưa lớn" HOẶC
  - Tốc độ shipper giảm đột ngột > 40%

Phân cấp mức độ (ĐÃ BỔ SUNG theo feedback):
  ┌─────────────┬──────────────┬───────────────────────────────┐
  │ Mức độ      │ Tốc độ       │ Hành động                     │
  ├─────────────┼──────────────┼───────────────────────────────┤
  │ Mưa nhẹ    │ Giảm 20%     │ Nới ETA, tiếp tục giao        │
  │ Mưa vừa    │ Giảm 40%     │ Cảnh báo, shipper quyết định  │
  │ Mưa nặng   │ Dừng hẳn     │ Dừng giao, về kho / chờ tại   │
  │             │              │ chỗ, reassign đơn cho shipper  │
  │             │              │ khác nếu có                    │
  └─────────────┴──────────────┴───────────────────────────────┘

Xử lý:
  1. Tương tự kẹt xe: đánh dấu edge ngập, A* tìm đường tránh
  2. Map hiển thị vùng ngập = vùng xanh đậm
  3. Nếu mưa nặng: cho shipper nghỉ, đơn hàng chờ hoặc reassign
  4. Lưu data: { edge_id, weather_condition, timestamp }

Default data khi bấm nút:
  - severity: HIGH
  - estimated_delay: 30 phút
  - action: "Đánh giá mức mưa, có thể dừng giao"
```

#### Sự cố 3: 👤 Khách vắng mặt / Từ chối nhận

```text
Trigger:
  - Shipper bấm nút "Khách vắng" khi đến nơi

Xử lý:
  1. Đơn hàng → trạng thái `DELIVERY_FAILED_ATTEMPT_1`
  2. Shipper bỏ qua đơn này, tiếp tục giao đơn tiếp theo
  3. Hệ thống kiểm tra: có đơn nào trong bán kính 3km gần đó không?
     - CÓ → Giao đơn gần trước, đơn failed xếp lại sau đơn gần đó
     - KHÔNG → Đơn failed xếp cuối danh sách giao
  4. A* tính lại tuyến đường tối ưu cho các đơn còn lại
  5. Thông báo cho khách hàng: "Shipper đã đến nhưng không liên lạc được"

Giới hạn thử lại (ĐÃ BỔ SUNG theo feedback):
  - Tối đa 2 lần thử giao lại
  - Lần 1 failed → xếp lại theo logic 3km ở trên
  - Lần 2 failed → đơn chuyển trạng thái FAILED hoàn toàn
  - Hệ thống tự động thông báo khách: "Đơn hàng không giao được sau 2 lần"
  - Đơn FAILED được log vào DB để phân tích

Default data khi bấm nút:
  - severity: LOW
  - estimated_delay: 10 phút
  - action: "Bỏ qua, giao đơn tiếp theo, thử lại sau"
```

#### Sự cố 4: 🔧 Shipper hư xe

```text
Trigger:
  - Shipper bấm nút "Hư xe"

Xử lý:
  1. Shipper → trạng thái `VEHICLE_BREAKDOWN` (hiển thị marker đỏ trên map)
  2. Tất cả đơn đang giao → trạng thái `DELAYED`
  3. ETA cập nhật: "Đang delay — chờ sửa xe"
  4. Khi shipper báo sửa xong → A* tính lại tuyến đường, tiếp tục giao

Timeout reassign (ĐÃ BỔ SUNG theo feedback):
  - Nếu hư xe > 60 phút:
    → Hệ thống tự động reassign đơn cho shipper khác gần nhất
    → Shipper hư xe → trạng thái OFFLINE
    → Dashboard hiện cảnh báo: "SHP-001 hư xe quá 60 phút, đã chuyển đơn"
  - Nếu không có shipper khác → giữ đơn DELAYED, cảnh báo admin

Default data khi bấm nút:
  - severity: HIGH
  - estimated_delay: 45 phút (LSTM điều chỉnh dựa trên lịch sử)
  - action: "Chờ sửa xe. Timeout 60p sẽ reassign"
```

#### Sự cố 5: 🔋 Hết pin / Mất kết nối

```text
Trigger:
  - Hệ thống tự phát hiện: không nhận GPS ping > 2 phút

Xử lý:
  1. Marker shipper trên map → MÀU ĐỎ + icon "?" (mất kết nối)
  2. Hệ thống liên tục ping lại GPS mỗi 30 giây
  3. Nếu kết nối lại < 60 phút:
     → Shipper tiếp tục giao bình thường
     → ETA cập nhật lại
  4. Nếu mất kết nối > 60 phút:
     → Shipper → trạng thái OFFLINE
     → Dashboard hiện cảnh báo: "SHP-001 mất kết nối > 1 giờ, yêu cầu kiểm tra"
     → Đơn hàng → cân nhắc reassign

Default data khi bấm nút:
  - severity: MEDIUM
  - estimated_delay: không xác định
  - action: "Đang thử kết nối lại..."
```

### 19.5 Flow tổng thể xử lý sự cố

```text
Sự cố xảy ra (user bấm nút hoặc hệ thống tự phát hiện)
    │
    ├──→ Lưu vào MongoDB collection `incidents`
    │
    ├──→ Broadcast WS event `incident_created` → tất cả client
    │     └──→ NotificationToast popup
    │
    ├──→ Cập nhật trạng thái shipper trong engine + MongoDB
    │
    ├──→ Tính toán xử lý (tùy loại sự cố):
    │     ├── A* tìm đường thay thế (kẹt xe / mưa)
    │     ├── Sắp xếp lại danh sách đơn (khách vắng)
    │     ├── Đặt timer timeout (hư xe / mất kết nối)
    │     └── Cập nhật ETA mới
    │
    ├──→ Thông báo cho khách hàng (ĐÃ BỔ SUNG):
    │     └── "Đơn hàng của bạn bị delay X phút do [lý do]"
    │
    └──→ Lưu data sự cố vào DB cho LSTM học:
          { incident_type, edge_id, time_of_day, day_of_week,
            duration_min, resolution, impact_on_eta }
```

---

## 20. ETA — Estimated Time of Arrival (ĐÃ BỔ SUNG theo feedback)

### 20.1 Công thức tính ETA

```text
ETA = ETA_base + ETA_incident + ETA_weather

Trong đó:
  ETA_base     = (tổng khoảng cách còn lại trên graph) / (tốc độ trung bình shipper)
  ETA_incident = LSTM dự đoán delay dựa trên:
                   - Loại sự cố hiện tại
                   - Lịch sử sự cố tương tự (cùng edge, cùng khung giờ)
                   - Thời gian đã delay
  ETA_weather  = hệ số thời tiết:
                   - Bình thường: ×1.0
                   - Mưa nhẹ: ×1.2
                   - Mưa vừa: ×1.4
                   - Mưa nặng: ×2.0 hoặc INFINITY (dừng giao)
```

### 20.2 Hiển thị ETA trên UI

| Vị trí | Nội dung |
|--------|----------|
| **RightPanel** (sidebar phải) | ETA cho shipper đang chọn: "Dự kiến giao: 14:35 (~12 phút)" |
| **Dashboard** (tab Stats) | Tổng hợp ETA fleet: trung bình, max, đang delay |
| **MapView** (tooltip marker) | Hover shipper → "ETA: 12 phút" |
| **DeliveryModal** | Khi gán đơn → "Ước tính giao trong: 15 phút" |

### 20.3 Cập nhật ETA

- ETA được tính lại **mỗi tick** (1 giây) dựa trên vị trí hiện tại
- Khi có sự cố → ETA nhảy lên + hiển thị icon ⚠️
- Broadcast qua WS trong `bulk_gps_update` mỗi shipper kèm field `eta_minutes`

---

## 21. LSTM — Chiến lược huấn luyện (ĐÃ LÀM RÕ theo feedback)

### 21.1 Cách tiếp cận

LSTM được huấn luyện **offline (batch training)**, không phải online realtime.

### 21.2 Quy trình

```text
1. Mỗi sự cố xảy ra → lưu vào MongoDB collection `incident_history`:
   {
     incident_type, edge_id, time_of_day, day_of_week,
     duration_min, speed_before, speed_after,
     weather_condition, resolution_type, actual_delay_min
   }

2. Định kỳ (mỗi ngày / mỗi tuần) chạy batch training:
   - Trích xuất data từ `incident_history`
   - Train LSTM model trên data mới
   - Xuất model mới → file `.pt` hoặc `.h5`
   - Backend load model mới khi khởi động lại

3. Trong demo:
   - LSTM được PRE-TRAIN SẴN với data mẫu
   - Khi sự cố xảy ra → model inference → trả về estimated_delay
   - Data sự cố mới vẫn được lưu vào DB (cho training sau)
```

### 21.3 Input/Output LSTM

```text
Input (sequence):
  - [time_of_day, day_of_week, edge_id, incident_type,
     current_speed, avg_speed_history, weather_code]

Output:
  - estimated_delay_minutes (float)
  - can_continue (boolean) — shipper có thể tiếp tục không?
  - recommended_action (enum) — REROUTE / WAIT / RETURN_TO_WAREHOUSE
```

---

## 22. Hệ thống phát hiện sự cố tự động

Ngoài user bấm nút, hệ thống **tự phát hiện** bất thường:

| Điều kiện | Nghi ngờ | Hành động |
|-----------|----------|-----------|
| Tốc độ < 5 km/h liên tục > 3 phút | Kẹt xe | Gửi WS hỏi shipper |
| Tốc độ giảm đột ngột > 40% | Mưa lớn | Gửi WS hỏi shipper |
| Không nhận GPS ping > 2 phút | Mất kết nối | Tự động đánh dấu, thử reconnect |
| Shipper dừng tại điểm giao > 10 phút | Khách vắng? | Gửi WS hỏi shipper |
| Tốc độ = 0 liên tục > 15 phút (không phải điểm giao) | Hư xe? | Gửi WS hỏi shipper |

```text
Flow tự động phát hiện:

Simulation Engine (mỗi tick)
    │
    ├── Kiểm tra tốc độ mỗi shipper
    ├── Kiểm tra thời gian dừng
    ├── Kiểm tra GPS ping interval
    │
    └── Nếu bất thường:
        ├── Broadcast WS: "system_alert" → Frontend hiện popup hỏi shipper
        ├── Shipper chọn loại sự cố → Auto-fill data → POST /incidents
        └── Hệ thống bắt đầu xử lý theo quy trình mục 19.4
```

---

## 23. Luồng thông báo khách hàng (ĐÃ BỔ SUNG theo feedback)

```text
Sự cố xảy ra
    │
    ├──→ Dashboard nội bộ cập nhật (đã có)
    │
    ├──→ Tính toán ETA mới
    │
    └──→ Gửi thông báo cho khách hàng:
         │
         ├── WebSocket event `customer_notification`:
         │   {
         │     "order_id": "ORD-001",
         │     "message": "Đơn hàng của bạn bị delay ~15 phút do kẹt xe",
         │     "new_eta": "14:50",
         │     "reason": "TRAFFIC_JAM"
         │   }
         │
         ├── (Mở rộng) Email / SMS notification
         │
         └── Khách có thể:
             ├── Chờ → không action
             ├── Hủy đơn → đơn → CANCELLED
             └── Liên hệ shipper → (ngoài scope demo)
```

---

## 24. Tóm tắt các điểm đã sửa / bổ sung theo feedback

| # | Vấn đề | Trước | Sau (đã sửa) | Mục |
|---|--------|-------|--------------|-----|
| 1 | Sai thuật toán tính khoảng cách | Linear Interpolation | **Haversine** (khoảng cách), Linear Interpolation chỉ dùng làm mượt | 17.1 |
| 2 | Routing chưa có thuật toán | Chưa nêu | **A\*** trên graph OSRM | 17.1, 18 |
| 3 | Giới hạn retry khách vắng | Chưa có | **Max 2 lần**, sau đó FAILED | 19.4 (sự cố 3) |
| 4 | Hư xe quá lâu | Chờ vô hạn | **Timeout 60 phút** → reassign | 19.4 (sự cố 4) |
| 5 | LSTM online/offline | Chưa rõ | **Offline batch** + pre-train sẵn | 21 |
| 6 | Mưa chưa phân cấp | Chung chung | **3 mức**: nhẹ/vừa/nặng | 19.4 (sự cố 2) |
| 7 | Thiếu thông báo khách | Chưa có | **WS event `customer_notification`** | 23 |
| 8 | ETA chưa định nghĩa | Chưa có | **Công thức + vị trí hiển thị** | 20 |
| 9 | Bảng sự cố chưa có fields | Chưa có | **8 fields chi tiết** | 19.3 |
| 10 | Bảng WS thiếu event mới | 11 event | **15 event** (+system_alert, customer_notification, route_updated, eta_updated) | 15 |
| 11 | Bảng status thiếu trạng thái mới | 6 status | **9 status** (+VEHICLE_BREAKDOWN, LOST_CONNECTION, DELAYED) | 16 |
| 12 | IncidentPanel.jsx chưa có trong danh sách | Thiếu | **Đã thêm** vào Section 13.1 | 13.1 |
| 13 | Số shipper chưa chốt | "có thể lệch" | **Chốt 30 shipper**, README cần sửa | 10 |
# Smart Logistics — Bộ tài liệu dự án

Tài liệu này là mục lục trung tâm sau khi rà soát folder `Smart_Logistics`.

## 1. Project làm gì?

Smart Logistics là hệ thống mô phỏng và theo dõi đội shipper theo thời gian thực tại TP.HCM.

Các chức năng chính:

- Hiển thị vị trí shipper realtime trên bản đồ Leaflet.
- Mô phỏng 30 shipper di chuyển quanh khu Bình Thạnh / TP.HCM.
- Tìm shipper gần kho nhất.
- Dispatch shipper về kho.
- Gán đơn giao hàng từ kho tới khách.
- Theo dõi trạng thái đơn / shipper.
- Báo cáo và xử lý incident:
  - `TRAFFIC_JAM`
  - `HEAVY_RAIN`
  - `CUSTOMER_ABSENT`
  - `VEHICLE_BREAKDOWN`
  - `LOST_CONNECTION`
- Cập nhật realtime từ backend sang frontend qua WebSocket.

## 2. Tech stack

### Backend

- Python
- FastAPI
- Uvicorn
- MongoDB
- Motor async MongoDB driver
- Redis
- Kafka / Zookeeper
- WebSocket
- Docker

### Frontend

- React 18
- Vite
- Axios
- Leaflet
- WebSocket browser API

### Infrastructure

- Docker Compose
- MongoDB volume
- Backend container
- Frontend container
- Optional simulator profile

## 3. Cấu trúc folder quan trọng

```txt
Smart_Logistics/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── domain/
│   │   │   └── entities.py
│   │   ├── application/
│   │   │   └── services/
│   │   │       ├── gps_service.py
│   │   │       ├── order_service.py
│   │   │       ├── routing_engine.py
│   │   │       ├── simulation_engine.py
│   │   │       ├── lstm_predictor.py
│   │   │       └── train_lstm.py
│   │   ├── infrastructure/
│   │   │   └── repositories/
│   │   │       ├── base_repository.py
│   │   │       ├── shipper_repository.py
│   │   │       ├── order_repository.py
│   │   │       ├── incident_repository.py
│   │   │       └── tracking_event_repository.py
│   │   └── presentation/
│   │       ├── api/routers/
│   │       │   ├── dashboard.py
│   │       │   ├── incidents.py
│   │       │   ├── orders.py
│   │       │   ├── shippers.py
│   │       │   └── simulation.py
│   │       └── websocket/
│   │           └── manager.py
│   ├── data_generator/
│   │   └── simulate.py
│   ├── scripts/
│   │   └── init_db.js
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── styles/
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── docs/
│   └── README.md
├── docker-compose.yml
├── .env.example
├── README.md
└── SETUP.md
```

## 4. Tài liệu nên giữ

Các file `.md` chính nên giữ lại / gom vào `Smart_Logistics/docs`:

| File | Mục đích |
|---|---|
| `README.md` | Tổng quan nhanh project |
| `SETUP.md` | Hướng dẫn setup |
| `ARCHITECTURE.md` | Kiến trúc tổng thể |
| `BACKEND_GUIDE.md` | Hướng dẫn backend |
| `FRONTEND_GUIDE.md` | Hướng dẫn frontend |
| `DATA_FLOW.md` | Luồng dữ liệu |
| `API_DOCUMENTATION.md` | REST API + WebSocket |
| `CLEAN_ARCHITECTURE_OVERVIEW.md` | Giải thích clean architecture |
| `BACKEND_FLOW.md` | Luồng backend chi tiết |
| `FRONTEND_FLOW.md` | Luồng frontend chi tiết |
| `QUICK_START_VIET.md` | Chạy nhanh bằng tiếng Việt |
| `SMART_LOGISTICS_OVERVIEW_VIET.md` | Tổng quan tiếng Việt |
| `CLEANUP_GUIDE.md` | Kế hoạch clean folder |

## 5. File code / config nên giữ

Không nên xoá các file sau vì cần để chạy hệ thống:

```txt
Smart_Logistics/.env.example
Smart_Logistics/.gitignore
Smart_Logistics/docker-compose.yml
Smart_Logistics/requirements-local.txt
Smart_Logistics/run_automation.py

Smart_Logistics/backend/Dockerfile
Smart_Logistics/backend/requirements.txt
Smart_Logistics/backend/app/**
Smart_Logistics/backend/data_generator/**
Smart_Logistics/backend/scripts/**

Smart_Logistics/frontend/Dockerfile
Smart_Logistics/frontend/index.html
Smart_Logistics/frontend/package.json
Smart_Logistics/frontend/package-lock.json
Smart_Logistics/frontend/vite.config.js
Smart_Logistics/frontend/src/**
```

## 6. File có thể cân nhắc archive / dọn sau

Chỉ nên archive sau khi đã backup hoặc commit git:

```txt
Smart_Logistics/CLAUDE.md
Smart_Logistics/project.md
Smart_Logistics_DOCS/MOTA.txt
```

Lý do:

- `CLAUDE.md`: thường là ghi chú cho AI/dev assistant, không cần cho runtime.
- `project.md`: có thể trùng thông tin với README/overview.
- `MOTA.txt`: không phải markdown, nếu muốn giữ tài liệu thống nhất thì đổi sang `.md` hoặc đưa nội dung vào overview.

## 7. Cách chạy nhanh bằng Docker

Từ folder:

```txt
C:\Users\USER\OneDrive\Desktop\Everyhing_tosave\PussyU\smart-log\Smart_Logistics
```

Tạo file `.env` từ `.env.example`, sau đó chạy:

```bash
docker compose up --build
```

Dịch vụ:

| Service | URL |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| Swagger Docs | `http://localhost:8000/docs` |
| WebSocket | `ws://localhost:8000/ws` |
| MongoDB | `localhost:27017` |
| Redis | `localhost:6379` |
| Kafka | `localhost:9092` |

Chạy thêm simulator profile nếu cần:

```bash
docker compose --profile simulator up --build
```

## 8. Cách chạy local không Docker

### Backend

```bash
cd Smart_Logistics/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Yêu cầu MongoDB/Redis/Kafka đang chạy hoặc chỉnh `.env` cho phù hợp.

### Frontend

```bash
cd Smart_Logistics/frontend
npm install
npm run dev
```

Frontend mặc định chạy ở:

```txt
http://localhost:5173
```

Trong Docker Compose frontend được map:

```txt
http://localhost:3000
```

## 9. Backend flow tổng quan

```txt
Client / Frontend
   |
   | REST API / WebSocket
   v
FastAPI app.main
   |
   ├── API routers
   |   ├── /shippers
   |   ├── /orders
   |   ├── /stats
   |   ├── /simulation
   |   └── /incidents
   |
   ├── WebSocket /ws
   |   └── gửi realtime events cho frontend
   |
   ├── WebSocket /ws/ingest
   |   └── nhận GPS từ simulator
   |
   ├── application/services
   |   ├── simulation_engine
   |   ├── gps_service
   |   ├── order_service
   |   └── routing_engine
   |
   ├── infrastructure/repositories
   |   └── đọc/ghi MongoDB
   |
   └── MongoDB / Redis / Kafka
```

## 10. Frontend flow tổng quan

```txt
main.jsx
  |
  v
App.jsx
  |
  ├── useWebSocket()
  |     └── nhận event realtime từ ws://localhost:8000/ws
  |
  ├── useShippers()
  |     └── quản lý state danh sách shipper + phase simulation
  |
  ├── services/api.js
  |     └── gọi REST API bằng axios
  |
  ├── components/MapView.jsx
  |     └── hiển thị shipper trên bản đồ Leaflet
  |
  ├── components/SimulationControls.jsx
  |     └── start / nearest / dispatch / reset
  |
  ├── components/DeliveryModal.jsx
  |     └── gán đơn giao hàng
  |
  ├── components/IncidentModal.jsx
  |     └── báo cáo incident
  |
  └── components/NotificationToast.jsx
        └── hiển thị cảnh báo realtime
```

## 11. WebSocket event chính

Backend gửi các event qua `/ws`.

| Event type | Ý nghĩa |
|---|---|
| `initial_state` | Gửi state ban đầu khi frontend connect |
| `bulk_gps_update` | Cập nhật vị trí nhiều shipper |
| `dispatch_started` | Bắt đầu điều shipper về kho |
| `shipper_arrived` | Một shipper đã tới kho |
| `all_arrived_at_warehouse` | Tất cả shipper được dispatch đã tới kho |
| `delivery_assigned` | Đã gán đơn giao hàng |
| `delivery_completed` | Shipper giao xong đơn |
| `simulation_completed` | Simulation kết thúc |
| `simulation_reset` | Reset simulation |
| `incident_created` | Có incident mới |
| `incident_resolved` | Incident được xử lý |
| `eta_updated` | ETA thay đổi |
| `customer_notification` | Gửi thông báo cho khách |
| `system_alert` | Hệ thống phát hiện bất thường |

## 12. REST API chính

### Health

```http
GET /health
GET /
```

### Shippers

```http
GET /shippers
GET /shippers/{shipper_id}
GET /shippers/{shipper_id}/history?limit=50
```

### Orders

```http
GET /orders
GET /orders/pending
GET /orders/{order_id}
POST /orders
POST /orders/bulk-import
PATCH /orders/{order_id}/assign
PATCH /orders/{order_id}/complete
```

### Dashboard / Stats

```http
GET /stats/overview
GET /stats/fleet
GET /stats/tracking-events
GET /stats/recent-events
```

### Simulation

```http
POST /simulation/start
GET /simulation/state
GET /simulation/shippers
GET /simulation/nearest?top_n=3
POST /simulation/dispatch
POST /simulation/assign-delivery
POST /simulation/complete
POST /simulation/reset
GET /simulation/stats/fleet
POST /simulation/incident/apply
POST /simulation/incident/resolve/{shipper_id}
```

### Incidents

```http
GET /incidents
GET /incidents/active
POST /incidents
PATCH /incidents/{incident_id}/resolve
GET /incidents/shipper/{shipper_id}
```

## 13. Luồng nghiệp vụ chính

### 13.1 Start simulation

```txt
Frontend click Start
  -> POST /simulation/start
  -> backend đổi phase STARTED
  -> backend tìm nearest shipper
  -> backend dispatch shipper về kho
  -> broadcast dispatch_started
  -> frontend cập nhật UI/map
```

### 13.2 Dispatch shipper về kho

```txt
Frontend chọn nearest / dispatch
  -> POST /simulation/dispatch
  -> simulation_engine tạo route về warehouse
  -> bulk_gps_update mỗi tick
  -> shipper_arrived khi tới kho
  -> all_arrived_at_warehouse khi đủ shipper tới kho
```

### 13.3 Gán đơn giao hàng

```txt
Frontend mở DeliveryModal
  -> nhập destination
  -> POST /simulation/assign-delivery
  -> backend tạo order trong MongoDB
  -> assign shipper
  -> shipper status = DELIVERING
  -> broadcast delivery_assigned
  -> shipper di chuyển tới khách
```

### 13.4 Hoàn tất giao hàng

```txt
simulation_engine phát hiện shipper tới customer
  -> update order complete
  -> update shipper status
  -> broadcast delivery_completed
```

### 13.5 Incident

```txt
Frontend mở IncidentModal
  -> POST /incidents hoặc /simulation/incident/apply
  -> backend lưu incident / apply effect
  -> broadcast incident_created
  -> có thể broadcast eta_updated / customer_notification / system_alert
  -> frontend hiện toast và cập nhật map/panel
```

## 14. Clean architecture hiện tại

Dự án đang theo hướng Clean Architecture:

```txt
domain
  -> entity / schema / business object

application
  -> service nghiệp vụ
  -> simulation / gps / routing / order

infrastructure
  -> repository
  -> database/cache/kafka adapter

presentation
  -> FastAPI router
  -> WebSocket manager
```

Ưu điểm:

- API không gọi DB trực tiếp quá nhiều, có repository trung gian.
- Business logic tập trung trong `application/services`.
- Dễ thay MongoDB bằng storage khác nếu repository interface ổn định.
- Frontend tách rõ API client, hook, component.

Điểm nên cải thiện:

- Trong `simulation.py` có dấu hiệu duplicate endpoint `/simulation/incident/apply` và `/simulation/incident/resolve/{shipper_id}`. Nên merge thành một implementation duy nhất.
- Nên thống nhất incident API: hoặc dùng `/incidents`, hoặc dùng `/simulation/incident/*`, tránh 2 luồng cùng làm một việc.
- Nên đưa hằng số warehouse vào config riêng.
- Nên thêm test cho simulation engine.
- Nên có `.env` mẫu đầy đủ và không commit `.env` thật.

## 15. Quy ước clean folder đề xuất

### Root `Smart_Logistics/`

Chỉ giữ:

```txt
README.md
SETUP.md
docker-compose.yml
.env.example
.gitignore
requirements-local.txt
run_automation.py
backend/
frontend/
docs/
```

### Tài liệu

Đưa toàn bộ tài liệu `.md` chi tiết vào:

```txt
Smart_Logistics/docs/
```

Ví dụ:

```txt
Smart_Logistics/docs/
├── README.md
├── ARCHITECTURE.md
├── SETUP.md
├── BACKEND_GUIDE.md
├── FRONTEND_GUIDE.md
├── DATA_FLOW.md
├── API_DOCUMENTATION.md
├── CLEAN_ARCHITECTURE_OVERVIEW.md
├── BACKEND_FLOW.md
├── FRONTEND_FLOW.md
├── QUICK_START_VIET.md
└── CLEANUP_GUIDE.md
```

Root `README.md` nên chỉ là entry point ngắn, link về `docs/README.md`.

## 16. Checklist sanity check

Sau khi clean folder / chỉnh code, kiểm tra:

```bash
docker compose config
```

Backend import check:

```bash
cd Smart_Logistics/backend
python -m compileall app
```

Frontend build:

```bash
cd Smart_Logistics/frontend
npm run build
```

Chạy toàn hệ thống:

```bash
cd Smart_Logistics
docker compose up --build
```

Kiểm tra:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`
- `http://localhost:3000`
- WebSocket connected trên TopBar frontend
- Map hiển thị shipper
- Start simulation chạy được
- Dispatch shipper về kho
- Assign delivery thành công
- Report incident hiện toast realtime
# Cấu Trúc Repository (Repo Structure)

## Tổng quan cấu trúc thư mục

```
Smart_Logistics/
├── .env.example                     # Template biến môi trường
├── docker-compose.yml               # 6 services: zookeeper, kafka, mongodb, redis, backend, frontend
│
├── backend/                         # FastAPI backend (Python 3.11)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                  # FastAPI app + WebSocket server + startup events
│   │   ├── config.py                # Pydantic Settings đọc từ .env
│   │   ├── db.py                    # Motor MongoDB connection pool (async)
│   │   │
│   │   ├── domain/                  # Domain Layer — Business entities
│   │   │   └── models.py            # Pydantic models: Shipper, Order, TrackingEvent, Warehouse
│   │   │
│   │   ├── application/             # Application Layer — Business logic services
│   │   │   ├── stream_processor.py  # ⭐ HÀM CỐT LÕI: process_gps_event() 9 bước
│   │   │   ├── order_service.py     # create_order(), assign_shipper(), retry_later()
│   │   │   └── decision_engine.py   # evaluate_rules(): cảnh báo, retry GPS
│   │   │
│   │   ├── infrastructure/          # Infrastructure Layer — Data access
│   │   │   ├── kafka_producer.py    # Đẩy GPS vào Kafka topic: gps_stream
│   │   │   ├── kafka_consumer.py    # Tiêu thụ gps_stream, gọi stream_processor
│   │   │   ├── repositories.py      # MongoDB CRUD operations (Motor async)
│   │   │   └── redis_cache.py       # Redis cache cho GPS state
│   │   │
│   │   ├── presentation/            # Presentation Layer — API + WebSocket
│   │   │   ├── shippers.py          # GET /shippers, GET /shippers/{id}, GET /shippers/{id}/history
│   │   │   ├── orders.py            # GET /orders, POST /orders, PATCH /orders/{id}/complete
│   │   │   └── dashboard.py         # GET /stats (active count, km, top list)
│   │   │
│   │   ├── utils/
│   │   │   ├── haversine.py         # Haversine: compute_speed(), compute_heading(), distance()
│   │   │   └── interpolation.py     # Linear Interpolation giữa 2 GPS points
│   │   │
│   │   └── websocket/
│   │       └── manager.py           # ConnectionManager: broadcast tới frontend clients
│   │
│   ├── data_generator/
│   │   └── simulate.py              # 100 shipper ảo, GPS mỗi 1 giây
│   │
│   └── scripts/
│       └── init_db.js               # MongoDB init: collections + indexes + seed warehouse
│
├── frontend/                        # React 18 + Vite frontend
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx                 # Entry point
│       ├── App.jsx                  # Root component
│       ├── components/
│       │   ├── TopBar.jsx           # Header: logo, status dots, clock
│       │   ├── ShipperList.jsx      # Left panel: danh sách 100 shipper
│       │   ├── MapView.jsx          # Center: Leaflet map + markers + trails
│       │   ├── RightPanel.jsx       # Right panel: shipper detail + order info
│       │   └── Dashboard.jsx        # Stats: active count, total km, top list
│       ├── hooks/
│       │   ├── useWebSocket.js      # Custom hook: kết nối ws://localhost:8000/ws
│       │   └── useShippers.js       # State management cho 100 shipper
│       ├── services/
│       │   └── api.js               # REST API calls tới backend
│       └── styles/
│           └── theme.css            # CSS variables (dark theme)
│
└── docs/                            # Tài liệu bổ sung
```

## Kiến trúc Clean Architecture

Dự án backend được tổ chức theo **Clean Architecture** với 4 layer:

```
┌─────────────────────────────────────┐
│       Presentation Layer            │  ← API Routers + WebSocket
│       (presentation/)               │
├─────────────────────────────────────┤
│       Application Layer             │  ← Business Logic Services
│       (application/)                │
├─────────────────────────────────────┤
│       Domain Layer                  │  ← Entities / Models
│       (domain/)                     │
├─────────────────────────────────────┤
│       Infrastructure Layer          │  ← Repositories, Kafka, Redis
│       (infrastructure/)             │
└─────────────────────────────────────┘
```

**Nguyên tắc phụ thuộc (Dependency Rule):**
- Layer trên chỉ phụ thuộc vào layer dưới
- Domain Layer **không phụ thuộc** bất kỳ layer nào khác
- Infrastructure Layer implement các interface được định nghĩa ở Application Layer

## Docker Compose Services

| Service    | Image                            | Port  | Vai trò                  |
|------------|----------------------------------|-------|--------------------------|
| zookeeper  | confluentinc/cp-zookeeper:7.5.0  | 2181  | Kafka coordination       |
| kafka      | confluentinc/cp-kafka:7.5.0      | 9092  | Message queue            |
| mongodb    | mongo:7.0                        | 27017 | Database chính           |
| redis      | redis:7.2-alpine                 | 6379  | Cache GPS state          |
| backend    | build: ./backend                 | 8000  | FastAPI app              |
| frontend   | build: ./frontend                | 3000  | React dashboard          |

**Thứ tự khởi động:** `zookeeper` → `kafka` → `mongodb` + `redis` → `backend` → `frontend`
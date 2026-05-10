# 🏛️ Clean Architecture Overview

**Real-time Smart Logistics System**

---

## Architecture Layers

Smart Logistics follows **Clean Architecture** principles with 4 distinct layers:

```
┌─────────────────────────────────────────────┐
│   PRESENTATION LAYER (API + WebSocket)     │
│   ├─ FastAPI routers                        │
│   ├─ WebSocket handlers                     │
│   └─ Request/Response models                │
├─────────────────────────────────────────────┤
│   APPLICATION LAYER (Services)              │
│   ├─ GPS Processing Engine                  │
│   ├─ Order Management                       │
│   └─ Decision Engine (Alerts)                │
├─────────────────────────────────────────────┤
│   INFRASTRUCTURE LAYER (External Services) │
│   ├─ MongoDB Repository                     │
│   ├─ Kafka Producer/Consumer                │
│   ├─ Redis Cache                            │
│   └─ HTTP Clients                           │
├─────────────────────────────────────────────┤
│   DOMAIN LAYER (Entities & Business Rules) │
│   ├─ VirtualShipper                         │
│   ├─ TrackingEvent                          │
│   ├─ Order                                  │
│   └─ Warehouse                              │
└─────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. **Domain Layer** (`backend/app/domain/`)
Pure business logic, no external dependencies.

**Components:**
- `VirtualShipper` - Shipper entity with GPS state
- `TrackingEvent` - GPS event record
- `Order` - Delivery order entity
- `Warehouse` - Warehouse location entity

**Key Features:**
- Independent of framework
- Testable without infrastructure
- Contains business rules (speed validation, ETA calculation)

```python
# Example: Domain entity
class VirtualShipper:
    def __init__(self, shipper_id, lat, lon, speed_kmh, heading):
        self.shipper_id = shipper_id
        self.lat = lat
        self.lon = lon
        self.speed_kmh = speed_kmh
        self.heading = heading
        self.status = "IDLE"
    
    def distance_to(self, lat, lon) -> float:
        """Calculate distance to target (Haversine formula)"""
        ...
```

---

### 2. **Application Layer** (`backend/app/application/services/`)
Business logic orchestration and workflows.

**Components:**
- `SimulationEngine` - Virtual shipper management
- `GPSProcessor` - 9-step GPS pipeline (core)
- `OrderService` - Order lifecycle
- `AlertService` - Decision engine

**Responsibilities:**
- Coordinate domain entities
- Implement 9-step GPS processing
- Handle order assignment
- Trigger alerts on conditions

```python
# Example: Service orchestration
class SimulationEngine:
    def __init__(self, graph, mongodb, kafka, websocket_manager):
        self.routing_graph = graph
        self.mongodb = mongodb
        self.kafka = kafka
        self.websocket_manager = websocket_manager
    
    async def process_gps_event(self, gps_data):
        """Execute 9-step GPS processing pipeline"""
        # STEP 1: Validate
        # STEP 2: Create event
        # STEP 3-4: Calculate speed/heading
        # STEP 5: Fetch ETA
        # STEP 6: Save event
        # STEP 7: Update shipper
        # STEP 8: Broadcast
        # STEP 9: Evaluate alerts
```

---

### 3. **Infrastructure Layer** (`backend/app/infrastructure/`)
External service integration (database, cache, messaging).

**Components:**
- `MongoDBRepository` - Database access
- `KafkaProducer/Consumer` - Message queue
- `RedisCache` - Cache layer
- `OSRMClient` - Routing API

**Responsibilities:**
- Database operations
- Message queue handling
- Cache management
- External API calls

```python
# Example: Repository pattern
class MongoDBRepository:
    async def save_tracking_event(self, event: TrackingEvent):
        """Append-only insert to tracking_events collection"""
        ...
    
    async def update_shipper(self, shipper_id, updates):
        """Update shipper live data"""
        ...
```

---

### 4. **Presentation Layer** (`backend/app/presentation/`)
API endpoints and WebSocket handlers.

**Components:**
- `routers/shippers.py` - Shipper endpoints
- `routers/orders.py` - Order endpoints
- `routers/dashboard.py` - Stats endpoints
- `websocket/` - Real-time handlers

**Responsibilities:**
- HTTP request handling
- WebSocket connection management
- Request validation
- Response serialization

```python
# Example: API endpoint
@router.get("/shippers")
async def list_shippers(db: Database, limit: int = 100):
    """GET /shippers - List all shippers"""
    return await db.get_all_shippers(limit)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket /ws - Real-time GPS updates"""
    await manager.connect(websocket)
    while True:
        message = await websocket.receive_json()
        await manager.broadcast(message)
```

---

## Data Flow Through Layers

```
Frontend                    Backend (Clean Architecture)
────────────────────────────────────────────────────────

1. GPS Input
   │
   └──→ WebSocket /ws/ingest
        │
        └──→ Presentation Layer
             (WebSocket handler)
             │
             └──→ Application Layer
                  (SimulationEngine)
                  │
                  ├─→ Domain Layer
                  │   (Validate, calculate)
                  │
                  └──→ Infrastructure Layer
                       ├─ MongoDB (save)
                       ├─ Kafka (queue)
                       ├─ Redis (cache)
                       └─ WebSocket (broadcast)

2. Frontend Update
   ←───── Presentation Layer
          (broadcast_message)
```

---

## Key Design Patterns

### 1. **Dependency Injection**
Services receive dependencies via constructor, enabling easy testing.

```python
class SimulationEngine:
    def __init__(self, db: Database, kafka: KafkaProducer, cache: Redis):
        self.db = db
        self.kafka = kafka
        self.cache = cache
```

### 2. **Repository Pattern**
Abstract database operations behind repositories.

```python
class ShipperRepository:
    async def get_by_id(self, shipper_id: str) -> Shipper:
        ...
    
    async def update(self, shipper: Shipper):
        ...
```

### 3. **Observer Pattern (WebSocket)**
Clients subscribe to updates through WebSocket channels.

```python
class WebSocketManager:
    async def connect(self, websocket):
        self.active_connections.append(websocket)
    
    async def broadcast(self, message):
        for conn in self.active_connections:
            await conn.send_json(message)
```

### 4. **Pipeline Pattern (9-Step GPS)**
Sequential processing steps with clear separation.

```
GPS Event
   ↓
[VALIDATE] → Check data integrity
   ↓
[CREATE] → Generate tracking event
   ↓
[CALCULATE] → Speed, heading, bearing
   ↓
[INTERPOLATE] → Smooth GPS noise
   ↓
[FETCH ETA] → Query active order
   ↓
[SAVE] → Append to database
   ↓
[UPDATE] → Cascade updates
   ↓
[BROADCAST] → WebSocket push
   ↓
[EVALUATE] → Decision engine (alerts)
```

---

## Module Organization

```
backend/app/
├── domain/                          # Business entities (no dependencies)
│   ├── entities.py                  # Shipper, Order, TrackingEvent, Warehouse
│   └── value_objects.py             # GPS coordinates, Speed, Heading
│
├── application/                     # Service orchestration
│   ├── services/
│   │   ├── simulation_engine.py      # Virtual shipper management + 9-step GPS
│   │   ├── order_service.py          # Order lifecycle
│   │   ├── alert_service.py          # Decision engine
│   │   └── gps_processor.py          # GPS pipeline (optional, may be in engine)
│   └── dto/                          # Data Transfer Objects
│       └── gps_dto.py                # GPS request/response models
│
├── infrastructure/                  # External services
│   ├── repositories/
│   │   ├── shipper_repository.py     # MongoDB shipper operations
│   │   ├── order_repository.py       # MongoDB order operations
│   │   └── tracking_repository.py    # MongoDB tracking events
│   ├── kafka/
│   │   ├── producer.py               # Kafka GPS publisher
│   │   └── consumer.py               # Kafka GPS consumer
│   ├── cache/
│   │   └── redis_cache.py            # Redis operations
│   ├── routing/
│   │   ├── osrm_client.py            # OSRM API calls
│   │   └── routing_graph.py          # In-memory graph (A*)
│   └── external/
│       └── http_client.py            # Shared HTTP client
│
├── presentation/                    # API & WebSocket
│   ├── api/
│   │   ├── routers/
│   │   │   ├── shippers.py           # Shipper endpoints
│   │   │   ├── orders.py             # Order endpoints
│   │   │   └── dashboard.py          # Stats endpoints
│   │   ├── dependencies.py           # FastAPI dependencies (DB, etc.)
│   │   └── middleware.py             # CORS, logging, error handling
│   ├── websocket/
│   │   ├── handlers.py               # WebSocket endpoints
│   │   ├── manager.py                # Connection management
│   │   └── schema.py                 # WebSocket message schemas
│   └── schemas/                      # Pydantic request/response models
│       ├── shipper_schema.py         # Shipper DTO
│       ├── order_schema.py           # Order DTO
│       └── tracking_schema.py        # TrackingEvent DTO
│
├── config.py                         # App configuration
├── main.py                           # FastAPI app entry point
└── db.py                             # Database initialization
```

---

## Dependency Flow (Clean Architecture Rule)

Dependencies flow **inward** only:

```
Domain ← Application ← Infrastructure ← Presentation

Outer layers depend on inner layers, never the reverse.
- Presentation calls Application Services
- Application Services use Domain Entities
- Infrastructure provides implementations to Application
- Domain is framework-agnostic
```

---

## Benefits of This Architecture

✅ **Testability**: Domain and Application layers are framework-independent  
✅ **Maintainability**: Clear separation of concerns  
✅ **Scalability**: Easy to add features without affecting existing code  
✅ **Flexibility**: Swap infrastructure (MongoDB ↔ PostgreSQL) without changing business logic  
✅ **Reusability**: Services can be used in different contexts (API, Kafka consumer, etc.)

---

## Running Services by Layer

```bash
# Start Infrastructure (Docker Compose)
docker compose up -d mongodb kafka redis zookeeper

# Start Backend (all layers together)
docker compose up -d backend

# Start Frontend (separate presentation)
docker compose up -d frontend

# Access API (Presentation layer)
curl http://localhost:8000/shippers
curl http://localhost:8000/docs
```

---

For implementation details, see:
- **BACKEND_GUIDE.md** - Backend file structure and modules
- **DATA_FLOW.md** - 9-step GPS processing pipeline
- **FRONTEND_GUIDE.md** - Frontend architecture
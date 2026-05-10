# Backend Development Guide

## Backend Overview

The backend is built with Python using FastAPI or Flask framework, providing RESTful API endpoints and WebSocket support for real-time communication.

## Technology Stack

- **Language**: Python 3.8+
- **Framework**: FastAPI (or Flask)
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL / MySQL / MongoDB
- **Package Manager**: pip
- **Key Libraries**:
  - `fastapi` - Web framework
  - `sqlalchemy` - ORM
  - `pydantic` - Data validation
  - `uvicorn` - ASGI server
  - `motor` - Async MongoDB driver
  - `python-dotenv` - Environment variable management

## Folder Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration settings
│   ├── db.py                   # Database connection
│   ├── api/                    # API route handlers
│   │   ├── routers/            # Endpoint definitions
│   │   └── dependencies.py     # Shared dependencies
│   ├── models/                 # Database/Pydantic models
│   ├── schemas/                # Request/Response validation
│   ├── services/               # Business logic
│   ├── infrastructure/         # External services (Kafka, Redis)
│   ├── domain/                 # Domain entities
│   ├── utils/                  # Utility functions
│   └── presentation/           # API & WebSocket
├── data_generator/             # Simulator/test data
├── scripts/                    # Database initialization
├── tests/                      # Unit and integration tests
├── requirements.txt            # Python dependencies
└── Dockerfile
```

## Core Modules

### 1. Models (`app/models/` or `app/domain/`)
SQLAlchemy ORM / Pydantic models:
- Shipper model - Shipper/driver information
- Order model - Order/shipment data
- TrackingEvent model - GPS tracking events
- Warehouse model - Warehouse locations
- Vehicle model - Fleet management

### 2. Schemas (`app/schemas/`)
Pydantic models for request/response validation:
- Ensure data integrity
- API documentation through OpenAPI/Swagger
- Type hints and validation rules

### 3. API Routes (`app/api/` or `app/presentation/`)
RESTful endpoints:
```
GET    /shippers              - List all shippers
GET    /shippers/{id}         - Get shipper details
GET    /orders                - List all orders
POST   /orders                - Create new order
GET    /stats                 - Dashboard statistics
```

### 4. Services (`app/services/`)
Business logic layer:
- GPS processing (9-step pipeline)
- Order management
- Shipper tracking
- Decision engine for alerts

### 5. Infrastructure (`app/infrastructure/`)
External service integrations:
- Kafka producer/consumer
- Redis cache
- MongoDB repositories
- HTTP client setup

### 6. WebSocket & Real-time (`app/presentation/websocket/`)
Real-time communication:
- Connection manager
- Event broadcasting
- Client subscriptions

## API Endpoints

### Shippers
```
GET  /shippers                    - List all shippers
GET  /shippers/{id}               - Get shipper details
GET  /shippers/{id}/history       - Get shipper tracking history
```

### Orders
```
GET    /orders                    - List orders
POST   /orders                    - Create order
PATCH  /orders/{id}/assign        - Assign to shipper
PATCH  /orders/{id}/complete      - Mark as delivered
```

### Dashboard
```
GET  /stats/overview              - Fleet overview
GET  /stats/fleet                 - Fleet statistics
GET  /stats/tracking-events       - Tracking statistics
```

### WebSocket
```
WS  /ws                           - Real-time GPS updates
WS  /ws/ingest                    - GPS stream input (simulator)
```

## Database Design

### Collections/Tables

**shippers**
- shipper_id (PK)
- name, phone, vehicle_type, vehicle_plate
- current_lat, current_lon (live GPS)
- current_speed_kmh, heading
- current_status (IDLE, ASSIGNED, DELIVERING, AVAILABLE)
- signal_status (ONLINE, OFFLINE)
- last_ping_at

**orders**
- order_id (PK)
- warehouse_id, assigned_shipper_id
- dest_lat, dest_lon
- current_status (PENDING, PICKED_UP, IN_TRANSIT, DELIVERED)
- eta_minutes
- promised_delivery_at

**tracking_events** (Append-only)
- event_id (UUID)
- shipper_id, order_id
- lat, lon, smooth_lat, smooth_lon
- speed_kmh, heading
- eta_minutes, delay_minutes
- TTL: 7 days

**warehouses**
- warehouse_id (PK)
- name, lat, lon
- capacity

## Running the Backend

### Development Mode
```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API docs: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Docker
```bash
docker compose up backend
```

## Environment Configuration

Create a `.env` file:

```env
# Database
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=shiptrack

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_GPS=gps_stream

# Redis
REDIS_URL=redis://localhost:6379

# API
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Business Rules
GPS_TIMEOUT_SECONDS=30
MAX_SPEED_KMPH=80
IDLE_WARNING_SECONDS=120
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_shippers.py
```

## Key Features

### 9-Step GPS Processing Pipeline
1. Validate GPS data
2. Create TrackingEvent record
3. Calculate speed + heading (Haversine)
4. Linear Interpolation for smoothing
5. Fetch active order & compute ETA
6. Save to MongoDB (append-only)
7. Cascade update (shipper, order, warehouse)
8. WebSocket broadcast to all clients
9. Decision Engine (alert evaluation)

### Real-time Updates
- WebSocket broadcast on GPS updates
- Event streaming via Kafka
- Redis caching for performance

### Append-Only Tracking
- tracking_events never updated/deleted
- Complete audit trail
- TTL-based automatic cleanup

## Performance Optimization

- Database indexing on frequently queried fields
- Redis caching for GPS state
- Kafka for message queuing
- Async/await throughout (Motor for MongoDB)

## Debugging

```bash
# View logs
docker compose logs -f backend

# MongoDB shell
docker compose exec mongodb mongosh shiptrack

# Test endpoint
curl http://localhost:8000/shippers

# Health check
curl http://localhost:8000/health
```

For setup instructions, see [SETUP.md](SETUP.md)
For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md)
For data flow details, see [DATA_FLOW.md](DATA_FLOW.md)
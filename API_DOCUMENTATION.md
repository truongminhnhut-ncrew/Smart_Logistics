# Smart Logistics API Documentation

Complete REST API and WebSocket reference for the Smart Logistics system.

## Base Configuration

- **Base URL**: `http://localhost:8000` (dev) | `https://api.smartlogistics.com` (production)
- **Content-Type**: `application/json`
- **Port**: 8000
- **Auto-Documentation**: http://localhost:8000/docs (Swagger UI)

## Shipper Endpoints

### List All Shippers
```http
GET /shippers HTTP/1.1
Host: localhost:8000

Response (200 OK):
{
  "shippers": [
    {
      "shipper_id": "SHP-001",
      "name": "Nguyen Van A",
      "phone": "0901234567",
      "vehicle_type": "motorcycle",
      "vehicle_plate": "72-B1-12345",
      "current_lat": 10.77695,
      "current_lon": 106.70095,
      "current_speed_kmh": 32.5,
      "heading": 45.3,
      "current_status": "DELIVERING",
      "signal_status": "ONLINE",
      "last_ping_at": "2026-05-08T12:00:00Z",
      "completed_count": 25,
      "total_distance_km": 450.5
    },
    ...
  ]
}
```

### Get Shipper Details
```http
GET /shippers/{shipper_id} HTTP/1.1

Response (200 OK):
{
  "shipper_id": "SHP-001",
  "name": "Nguyen Van A",
  "phone": "0901234567",
  "vehicle_type": "motorcycle",
  "vehicle_plate": "72-B1-12345",
  "current_lat": 10.77695,
  "current_lon": 106.70095,
  "current_speed_kmh": 32.5,
  "heading": 45.3,
  "current_status": "DELIVERING",
  "signal_status": "ONLINE",
  "last_ping_at": "2026-05-08T12:00:00Z",
  "completed_count": 25,
  "total_distance_km": 450.5,
  "current_order": {
    "order_id": "ORD-001",
    "destination": "District 1, HCMC",
    "eta_minutes": 15,
    "delay_minutes": 2
  }
}
```

### Get Shipper Tracking History
```http
GET /shippers/{shipper_id}/history HTTP/1.1

Query Parameters:
- limit: number of events (default: 50, max: 200)
- offset: pagination offset (default: 0)

Response (200 OK):
{
  "shipper_id": "SHP-001",
  "total_events": 1500,
  "events": [
    {
      "event_id": "uuid-001",
      "timestamp": "2026-05-08T12:00:00Z",
      "lat": 10.77695,
      "lon": 106.70095,
      "smooth_lat": 10.77691,
      "smooth_lon": 106.70093,
      "speed_kmh": 32.5,
      "heading": 45.3,
      "distance_moved_km": 0.5,
      "eta_minutes": 15,
      "delay_minutes": 2
    },
    ...
  ]
}
```

## Order Endpoints

### List All Orders
```http
GET /orders HTTP/1.1

Query Parameters:
- status: PENDING | PICKED_UP | IN_TRANSIT | DELIVERED | FAILED
- skip: pagination offset (default: 0)
- limit: pagination limit (default: 20, max: 100)

Response (200 OK):
{
  "total": 500,
  "skip": 0,
  "limit": 20,
  "items": [
    {
      "order_id": "ORD-20260508-001",
      "warehouse_id": "WH-01",
      "assigned_shipper_id": "SHP-001",
      "destination": "District 1, HCMC",
      "dest_lat": 10.77695,
      "dest_lon": 106.70095,
      "current_status": "IN_TRANSIT",
      "eta_minutes": 15,
      "delay_minutes": 2,
      "promised_delivery_at": "2026-05-08T13:00:00Z",
      "priority": "high",
      "created_at": "2026-05-08T12:00:00Z"
    },
    ...
  ]
}
```

### Create Order
```http
POST /orders HTTP/1.1
Content-Type: application/json

{
  "warehouse_id": "WH-01",
  "destination": "District 1, HCMC",
  "dest_lat": 10.77695,
  "dest_lon": 106.70095,
  "promised_delivery_at": "2026-05-08T13:00:00Z",
  "priority": "high"
}

Response (201 Created):
{
  "order_id": "ORD-20260508-001",
  "warehouse_id": "WH-01",
  "current_status": "PENDING",
  "created_at": "2026-05-08T12:00:00Z"
}
```

### Assign Order to Shipper
```http
PATCH /orders/{order_id}/assign HTTP/1.1
Content-Type: application/json

{
  "shipper_id": "SHP-001"
}

Response (200 OK):
{
  "order_id": "ORD-20260508-001",
  "assigned_shipper_id": "SHP-001",
  "current_status": "PICKED_UP",
  "eta_minutes": 25
}
```

### Complete Delivery
```http
PATCH /orders/{order_id}/complete HTTP/1.1
Content-Type: application/json

{
  "actual_location": "District 1, HCMC",
  "notes": "Delivered successfully"
}

Response (200 OK):
{
  "order_id": "ORD-20260508-001",
  "current_status": "DELIVERED",
  "delivered_at": "2026-05-08T12:45:00Z"
}
```

## Dashboard/Stats Endpoints

### Fleet Overview
```http
GET /stats/overview HTTP/1.1

Response (200 OK):
{
  "total_shippers": 100,
  "active_shippers": 87,
  "idle_shippers": 8,
  "offline_shippers": 5,
  "total_distance_km": 15234.5,
  "active_orders": 87,
  "delivered_today": 234,
  "avg_delivery_time_minutes": 28
}
```

### Fleet Statistics
```http
GET /stats/fleet HTTP/1.1

Response (200 OK):
{
  "statistics": {
    "status_breakdown": {
      "DELIVERING": 87,
      "IDLE": 8,
      "OFFLINE": 5
    },
    "top_shippers": [
      {
        "shipper_id": "SHP-001",
        "name": "Nguyen Van A",
        "completed_count": 45,
        "total_distance_km": 750.5
      },
      ...
    ],
    "performance_metrics": {
      "avg_speed_kmh": 32.5,
      "on_time_percentage": 94.5,
      "customer_satisfaction": 4.7
    }
  }
}
```

### Tracking Events Stats
```http
GET /stats/tracking-events HTTP/1.1

Query Parameters:
- shipper_id: optional filter
- start_time: ISO 8601 timestamp
- end_time: ISO 8601 timestamp
- limit: number of events (default: 100)

Response (200 OK):
{
  "total_events": 1000,
  "time_period": {
    "start": "2026-05-08T00:00:00Z",
    "end": "2026-05-08T23:59:59Z"
  },
  "events": [ ... ]
}
```

## Health Check

### Server Status
```http
GET /health HTTP/1.1

Response (200 OK):
{
  "status": "ok",
  "timestamp": "2026-05-08T12:00:00Z",
  "uptime_seconds": 3600,
  "ws_connections": 45,
  "database": "connected",
  "kafka": "connected",
  "redis": "connected"
}
```

## WebSocket API

### Connection
```javascript
// Connect to real-time GPS stream
const ws = new WebSocket('ws://localhost:8000/ws')

ws.onopen = () => {
  console.log('Connected to real-time stream')
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  // Handle real-time update
}

ws.onclose = () => {
  console.log('Disconnected')
}
```

### Ingest Stream (Simulator)
```javascript
// Simulator sends GPS data
const ws = new WebSocket('ws://localhost:8000/ws/ingest')

ws.send(JSON.stringify({
  shipper_id: "SHP-001",
  latitude: 10.77695,
  longitude: 106.70095,
  timestamp: "2026-05-08T12:00:00Z"
}))
```

### Real-time Update Format
```javascript
// Message from server to connected clients
{
  "event_id": "uuid-12345",
  "shipper_id": "SHP-001",
  "lat": 10.77695,
  "lon": 106.70095,
  "smooth_lat": 10.77691,
  "smooth_lon": 106.70093,
  "speed_kmh": 32.5,
  "heading": 45.3,
  "eta_minutes": 15,
  "delay_minutes": 2,
  "order_status": "IN_TRANSIT",
  "shipper_status": "DELIVERING",
  "signal_status": "ONLINE",
  "timestamp": "2026-05-08T12:00:00Z"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data",
  "error_code": "INVALID_INPUT",
  "timestamp": "2026-05-08T12:00:00Z"
}
```

### 404 Not Found
```json
{
  "detail": "Shipper not found",
  "error_code": "SHIPPER_NOT_FOUND",
  "shipper_id": "SHP-001"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "error_code": "INTERNAL_ERROR",
  "request_id": "req-abc123",
  "timestamp": "2026-05-08T12:00:00Z"
}
```

## Response Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 404 | Not Found |
| 500 | Server Error |

## Rate Limiting

All endpoints support basic rate limiting:
- **Default**: 100 requests per minute
- **Headers returned**:
  ```
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1651945200
  ```

## Pagination

List endpoints support pagination:

```http
GET /orders?skip=0&limit=20 HTTP/1.1

Response:
{
  "items": [...],
  "total": 500,
  "skip": 0,
  "limit": 20,
  "has_more": true
}
```

## Performance Targets

- **Response Time**: < 100ms (95th percentile)
- **WebSocket Latency**: < 200ms (GPS → Dashboard)
- **Availability**: 99.9% uptime

For setup instructions, see [SETUP.md](SETUP.md)
For data flow details, see [DATA_FLOW.md](DATA_FLOW.md)
For backend implementation, see [BACKEND_GUIDE.md](BACKEND_GUIDE.md)
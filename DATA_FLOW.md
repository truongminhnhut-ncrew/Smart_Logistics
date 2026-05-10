# Data Flow and Process Documentation

## System Data Flow Overview

This document describes how data flows through the Smart Logistics system, from GPS events through backend processing to real-time UI updates.

## Complete Data Flow: GPS Update

### Step-by-Step Process

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: GPS Event Generation (Simulator/Device)                │
├─────────────────────────────────────────────────────────────────┤
│ Virtual shipper or mobile device generates GPS:                 │
│ {                                                                │
│   "shipper_id": "SHP-001",                                      │
│   "latitude": 10.77695,                                         │
│   "longitude": 106.70095,                                       │
│   "timestamp": "2026-05-08T12:00:00Z"                           │
│ }                                                                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: WebSocket Ingestion (Frontend/Simulator → Backend)     │
├─────────────────────────────────────────────────────────────────┤
│ 1. Connect to ws://backend:8000/ws/ingest                      │
│ 2. Send GPS payload as JSON                                     │
│ 3. Backend receives on /ws/ingest endpoint                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Kafka Producer (Backend)                                │
├─────────────────────────────────────────────────────────────────┤
│ 1. GPS event pushed to Kafka topic: gps_stream                  │
│ 2. Kafka cluster stores for durability                          │
│ 3. Enables async processing & scaling                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Kafka Consumer (Backend)                                │
├─────────────────────────────────────────────────────────────────┤
│ 1. Consumer group: shiptrack-consumer                           │
│ 2. Reads GPS events from topic                                  │
│ 3. Calls process_gps_event() handler                            │
│ 4. On error: dead-letter-queue (retry logic)                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: 9-Step GPS Processing (Core Business Logic)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ STEP 5.1: VALIDATE                                              │
│   - Check shipper_id not null                                   │
│   - Validate lat/lon ranges                                     │
│   - Reject if speed > 80 km/h (data error)                      │
│                                                                  │
│ STEP 5.2: CREATE TRACKING EVENT                                 │
│   - Generate event_id (UUID v4)                                 │
│   - Set timestamp = now()                                       │
│   - Record: shipper_id, lat, lon                                │
│                                                                  │
│ STEP 5.3: CALCULATE SPEED & HEADING                             │
│   - Use Haversine formula: distance(prev → current)             │
│   - speed_kmh = distance / time_delta                           │
│   - heading = bearing(prev → current)                           │
│                                                                  │
│ STEP 5.4: LINEAR INTERPOLATION                                  │
│   - Smooth GPS noise between points                             │
│   - smooth_lat, smooth_lon = interpolate(prev, current)         │
│   - Better visualization on map                                 │
│                                                                  │
│ STEP 5.5: FETCH & COMPUTE ETA                                   │
│   - Get active order for shipper                                │
│   - Remaining distance to destination                           │
│   - eta_minutes = distance / (speed_kmh * safety_factor)        │
│   - delay_minutes = eta - promised_time                         │
│                                                                  │
│ STEP 5.6: SAVE TRACKING EVENT                                   │
│   - INSERT tracking_event to MongoDB (append-only)              │
│   - Never UPDATE/DELETE existing events                         │
│   - TTL index: auto-delete after 7 days                         │
│                                                                  │
│ STEP 5.7: CASCADE UPDATE                                        │
│   - UPDATE shippers: current_lat, lon, speed, heading           │
│   - UPDATE orders: eta_minutes, status                          │
│   - UPDATE warehouse: total_km, active_count                    │
│   - Single transaction (ACID guarantee)                         │
│                                                                  │
│ STEP 5.8: WEBSOCKET BROADCAST                                   │
│   - Emit message to all connected frontend clients              │
│   - Payload: event_id, shipper_id, lat, lon, eta, status       │
│   - ~100 msg/sec (100 shippers × 1 msg/sec)                    │
│                                                                  │
│ STEP 5.9: DECISION ENGINE                                       │
│   - Check: is shipper stationary > 2 min? → IDLE alert          │
│   - Check: ETA delay > 15 min? → DELAY alert                    │
│   - Check: no ping > 30 sec? → OFFLINE alert                    │
│   - Store alerts in alerts collection                           │
│                                                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: MongoDB Storage (Async Write)                           │
├─────────────────────────────────────────────────────────────────┤
│ Three collections updated in transaction:                       │
│                                                                  │
│ 1. shippers collection:                                         │
│    UPDATE {_id: "SHP-001"} SET {                                │
│      current_lat: 10.77695,                                     │
│      current_lon: 106.70095,                                    │
│      current_speed_kmh: 32.5,                                   │
│      heading: 45.3,                                             │
│      last_ping_at: NOW(),                                       │
│      signal_status: "ONLINE"                                    │
│    }                                                             │
│                                                                  │
│ 2. orders collection:                                           │
│    UPDATE {_id: "ORD-001", assigned_shipper_id: "SHP-001"} SET {│
│      eta_minutes: 15,                                           │
│      delay_minutes: 2,                                          │
│      current_status: "IN_TRANSIT"                               │
│    }                                                             │
│                                                                  │
│ 3. tracking_events collection (APPEND ONLY):                    │
│    INSERT {                                                     │
│      event_id: UUID,                                            │
│      shipper_id: "SHP-001",                                     │
│      order_id: "ORD-001",                                       │
│      lat: 10.77695,                                             │
│      lon: 106.70095,                                            │
│      smooth_lat: 10.77691,                                      │
│      smooth_lon: 106.70093,                                     │
│      speed_kmh: 32.5,                                           │
│      heading: 45.3,                                             │
│      eta_minutes: 15,                                           │
│      delay_minutes: 2,                                          │
│      timestamp: NOW()                                           │
│    }                                                             │
│                                                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: Redis Cache (Optional Performance Layer)                │
├─────────────────────────────────────────────────────────────────┤
│ Cache latest GPS for 10 seconds:                                │
│ SET "shipper:SHP-001:gps" { ... } EX 10                         │
│ Speeds up map reloads without DB query                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: WebSocket Broadcast to Frontend                         │
├─────────────────────────────────────────────────────────────────┤
│ Message sent to all frontend clients via /ws:                   │
│ {                                                                │
│   "event_id": "uuid-12345",                                     │
│   "shipper_id": "SHP-001",                                      │
│   "lat": 10.77695,                                              │
│   "lon": 106.70095,                                             │
│   "smooth_lat": 10.77691,                                       │
│   "smooth_lon": 106.70093,                                      │
│   "speed_kmh": 32.5,                                            │
│   "heading": 45.3,                                              │
│   "eta_minutes": 15,                                            │
│   "delay_minutes": 2,                                           │
│   "order_status": "IN_TRANSIT",                                 │
│   "shipper_status": "DELIVERING",                               │
│   "signal_status": "ONLINE"                                     │
│ }                                                                │
│                                                                  │
│ Broadcast type:                                                 │
│   for each client in WebSocketManager.active_connections        │
│     send(JSON payload)                                          │
│                                                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 9: Frontend Reception & UI Update                          │
├─────────────────────────────────────────────────────────────────┤
│ 1. WebSocket message received in useWebSocket hook              │
│ 2. Parse JSON payload                                           │
│ 3. Update Redux/Context state:                                  │
│    dispatch(updateShipper(message))                             │
│ 4. Component re-renders (MapView listens to state change)       │
│ 5. Leaflet marker.setLatLng() - update pin position             │
│ 6. Update shipper detail panel (RightPanel)                     │
│ 7. Update dashboard stats (total km, eta count)                 │
│ 8. Show status indicator (DELIVERING → green dot)               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **GPS Stream** | 100 shippers × 1 msg/sec | 100 events/sec |
| **Processing Latency** | < 200ms | GPS → Dashboard |
| **Database Writes** | ~300 ops/sec | With batching |
| **WebSocket Throughput** | 1000+ msg/sec | Broadcast to all clients |
| **Memory Usage** | ~1.5 GB | All services combined |
| **CPU Usage** | 10-20% | Under 100 msg/sec load |

## Error Handling Flow

```
GPS Processing Error
    ↓
    ├─→ Validation error
    │   └─→ Log warning, skip event, continue
    │
    ├─→ Database error
    │   ├─→ Retry with backoff
    │   └─→ Fall back to Redis cache
    │
    ├─→ Kafka error
    │   ├─→ Push to dead-letter-queue
    │   └─→ Alert monitoring system
    │
    └─→ WebSocket error
        ├─→ Catch disconnect gracefully
        ├─→ Remove from connection pool
        └─→ Log but don't crash loop
```

## State Management (Frontend)

### Redux Store Structure

```javascript
{
  shippers: {
    byId: {
      "SHP-001": {
        id: "SHP-001",
        name: "Shipper 1",
        lat: 10.77695,
        lon: 106.70095,
        status: "DELIVERING",
        signal: "ONLINE",
        speed_kmh: 32.5
      },
      // ... 99 more shippers
    },
    allIds: ["SHP-001", "SHP-002", ...],
    selected: "SHP-001",
    loading: false,
    error: null
  },
  
  orders: {
    byId: { ... },
    allIds: [ ... ]
  },
  
  stats: {
    activeCount: 100,
    totalKm: 2500,
    topShippers: [ ... ]
  },
  
  ui: {
    mapCenter: [10.77, 106.70],
    mapZoom: 13,
    panelOpen: true
  }
}
```

## Caching Strategy

### Redis Cache Layer
```
Key: shipper:{id}:gps
Value: { lat, lon, speed, heading, timestamp }
TTL: 10 seconds
Used: Map reload, quick history lookup
```

### Frontend Cache (Redux)
```
- Shipper list: cached until new event
- Order details: cached until status change
- Stats: cached, updated every 5 seconds
- UI state: persisted in localStorage
```

## Real-time Guarantees

✅ **At-least-once delivery**: Kafka + tracking DB  
✅ **Append-only audit trail**: tracking_events immutable  
✅ **Eventual consistency**: DB updates within 200ms  
✅ **Graceful degradation**: Cached fallback when DB slow  

## Scaling Considerations

- **Current**: 100 shippers × 1 msg/sec
- **Scalable to**: 1000+ shippers × 10+ msg/sec
- **Bottleneck**: WebSocket broadcast (solve with Redis pub/sub)
- **Next improvement**: Message batching + compression

For setup instructions, see [SETUP.md](SETUP.md)
For backend implementation, see [BACKEND_GUIDE.md](BACKEND_GUIDE.md)
For frontend implementation, see [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md)
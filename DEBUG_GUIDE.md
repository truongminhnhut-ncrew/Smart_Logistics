# 🔍 ShipTrack Comprehensive Debugging Guide

**Last Updated:** 2026-04-27  
**Purpose:** Systematic error investigation and logging

---

## 📋 Quick Diagnosis Commands

### Phase 1: Service Health Check
```bash
# Check all containers running
docker compose ps

# Expected: All 6 services with status "running" or "healthy"

# Check service connectivity
curl http://localhost:8000/health
# Expected: {"status": "ok", "ws_connections": N}

# Check MongoDB accessibility
docker compose exec mongodb mongosh shiptrack
# Inside: db.shippers.countDocuments()
# Expected: > 0 (if simulator ran) or 0 (if not)
```

### Phase 2: Data Flow Inspection

#### LAYER 1: Simulator → Backend
```bash
# Terminal 1: Watch backend GPS ingest logs
docker compose logs backend -f | grep -E "WebSocket|ingest|GPS|processed"

# Terminal 2: Start simulator and watch output
docker compose --profile simulator up simulator

# EXPECTED LOG SEQUENCE:
# Backend should show:
#   🔌 [WebSocket] New GPS ingest connection
#   [GPS] SHP-XXX processed: lat=..., lon=..., speed=...

# Simulator should show:
#   ✅ Connected to ws://backend:8000/ws/ingest
#   [tick=10] Sent 100 GPS | online=100/100
```

#### LAYER 2: Backend Processing → MongoDB
```bash
# Terminal 1: Monitor tracking_events collection growth
docker compose exec mongodb mongosh shiptrack
db.watch([])  # Real-time change stream
# or
setInterval(() => db.tracking_events.countDocuments().then(console.log), 5000)

# Terminal 2: Watch backend application logs
docker compose logs backend -f | grep -E "Step|Error|failed|append"

# EXPECTED: count should increase every 1-2 seconds
```

#### LAYER 3: WebSocket Broadcast → Frontend
```bash
# Check WebSocket broadcast logs
docker compose logs backend -f | grep -E "broadcast|ws_manager"

# Open frontend DevTools → Network → WS tab
# Should see: ws://localhost:8000/ws
# Message flow: every 1 second should see GPS update payload
```

---

## 🔧 Layer-by-Layer Debugging

### Layer A: Simulator Connection
**File:** `backend/app/main.py` lines 77-121

**Commands to verify endpoint exists:**
```bash
# Check if endpoint is registered
curl -i http://localhost:8000/docs
# Look for: /ws/ingest in API documentation

# Check routing
docker compose logs backend | grep -i "route\|include_router"

# Verify WebSocket endpoint code
docker compose exec backend python -c "
import asyncio
from app.main import app
for route in app.routes:
    if 'websocket' in str(route):
        print(route)
"
```

**Expected Issues & Fixes:**
- ❌ Endpoint not showing in `/docs` → Check `@app.websocket()` decorator
- ❌ WebSocket not connecting → Check CORS middleware settings (line 54-60)
- ❌ Connection drops immediately → Check exception handling (line 116-119)

---

### Layer B: GPS Validation & Processing
**File:** `backend/app/application/services/gps_service.py` lines 32-170

**Add detailed logging at each step:**
```bash
# Create enhanced logging version (test locally first)
cat > /tmp/test_gps_pipeline.py << 'EOF'
import json
from datetime import datetime, timezone

# Simulate 9-step pipeline
gps_data = {"shipper_id": "SHP-001", "lat": 10.8231, "lon": 106.6297, "timestamp": None}

print("=" * 50)
print("STEP 1: VALIDATE GPS DATA")
print(f"Input: {json.dumps(gps_data, indent=2)}")
shipper_id = gps_data.get("shipper_id")
lat = gps_data.get("lat")
lon = gps_data.get("lon")
print(f"Validation: shipper_id={bool(shipper_id)}, lat={lat}, lon={lon}")
if not shipper_id or lat is None or lon is None:
    print("❌ FAILED: Missing required fields")
else:
    print("✅ PASSED")

print("\nSTEP 2: CREATE TRACKING EVENT")
now = datetime.now(timezone.utc)
event = {
    "event_id": "EVT-001",
    "timestamp": now,
    "shipper_id": shipper_id,
    "lat": lat,
    "lon": lon,
    "speed_kmh": 0.0,
}
print(f"✅ Created event: {event['event_id']}")

print("\nSTEP 3-9: (Would fetch from DB, compute, broadcast, etc.)")
EOF

python /tmp/test_gps_pipeline.py
```

**Instrumentation to add (minimal):**
```python
# Add at line 47 in gps_service.py
print(f"\n[STEP 1] Validating: shipper_id={shipper_id}, lat={lat}, lon={lon}")

# Add at line 138
print(f"[STEP 6] Appending event: {event['event_id']} for {shipper_id}")

# Add at line 208
print(f"[STEP 8] Broadcasting: {event['event_id']} to {len(ws_manager.active_connections)} clients")
```

---

### Layer C: MongoDB Data Persistence
**File:** `backend/app/infrastructure/repositories/tracking_event_repository.py`

**Verify data is being written:**
```bash
# Live document count
watch -n 1 'docker compose exec -T mongodb mongosh shiptrack --eval "db.tracking_events.countDocuments()"'

# Check write errors
docker compose logs backend -f | grep -i "insert\|write\|error"

# Verify TTL index exists
docker compose exec mongodb mongosh shiptrack --eval "db.tracking_events.getIndexes()"
# Should show: expireAfterSeconds: 604800 (7 days)

# Check if data is actually being written
docker compose exec mongodb mongosh shiptrack --eval "
db.tracking_events.findOne({}, {timestamp: 1, shipper_id: 1})
"
```

---

### Layer D: WebSocket Manager & Broadcasting
**File:** `backend/app/presentation/websocket/manager.py`

**Verify broadcast mechanics:**
```bash
# Check active connections
docker compose logs backend -f | grep -E "connect|disconnect|broadcast"

# Simulate WebSocket connection and observe
docker compose exec backend python << 'EOF'
import asyncio
from app.presentation.websocket.manager import ws_manager

print(f"Active connections: {ws_manager.get_connection_count()}")
print(f"Connections list: {len(ws_manager.active_connections)}")
EOF
```

---

## 🚨 Critical Failure Points Checklist

| Component | Failure Symptom | Root Cause Check | Fix Command |
|-----------|-----------------|------------------|------------|
| **Simulator** | No connection logs | CORS? Wrong URL? Firewall? | `docker compose logs simulator \| tail -20` |
| **GPS Endpoint** | Not in `/docs` | Endpoint not registered | `docker compose exec backend python -c "from app.main import app; print([r for r in app.routes if '/ws/ingest' in str(r)])"` |
| **WebSocket Handler** | Immediate disconnect | Exception in `websocket_gps_ingest()` | Add try-except around line 94-114 |
| **Data Validation** | `None` returned in STEP 1 | Missing shipper_id/lat/lon | `docker compose logs backend \| grep "Validation failed"` |
| **MongoDB Write** | No documents in DB | Connection dropped? Credentials? | `docker compose logs backend \| grep "Step 6"` |
| **Broadcast** | Frontend sees 0/100 | WS manager not initialized? | `docker compose logs backend \| grep "active_connections"` |

---

## 📊 State Verification Queries

### MongoDB Direct Inspection
```bash
docker compose exec mongodb mongosh shiptrack << 'EOF'

// How many shippers are seeded?
print("Shippers:", db.shippers.countDocuments());

// How many tracking events?
print("Tracking Events:", db.tracking_events.countDocuments());

// Any events in last 5 minutes?
print("Recent Events:", db.tracking_events.countDocuments({
  timestamp: { $gte: new Date(Date.now() - 5*60000) }
}));

// Sample shipper document
printjson(db.shippers.findOne());

// Sample tracking event
printjson(db.tracking_events.findOne({}, {sort: {timestamp: -1}}));

EOF
```

### Backend Health Endpoints
```bash
# Overall health
curl http://localhost:8000/health

# Shipper data API (should return from seeded data)
curl http://localhost:8000/shippers | jq '.[] | {shipper_id, status, current_lat, current_lon}'

# Tracking events
curl http://localhost:8000/stats/tracking-events

# Orders
curl http://localhost:8000/orders
```

---

## 🧬 Complete Error Isolation Flow

### Step 1: Verify Simulator is Sending Data
```bash
# Terminal 1: Clear logs and restart backend
docker compose down && docker compose up -d && sleep 3

# Terminal 2: Monitor backend for ANY ingest activity
docker compose logs -f backend 2>&1 | tee /tmp/backend.log

# Terminal 3: Start simulator
docker compose --profile simulator up simulator

# Terminal 4: Check if connection logs appear
sleep 5
grep -i "ingest\|gps.*process" /tmp/backend.log

# If 0 matches → PROBLEM: Simulator not connecting or endpoint missing
# If matches → PROBLEM: Connection works but processing fails downstream
```

### Step 2: Verify WebSocket Endpoint Registration
```bash
# Does the route exist?
curl -s http://localhost:8000/docs | grep -i "/ws/ingest"

# Detailed endpoint info
docker compose exec backend python << 'PYEOF'
from app.main import app
routes = [str(r) for r in app.routes]
ws_routes = [r for r in routes if 'websocket' in r.lower()]
print("WebSocket Routes:")
for r in ws_routes:
    print(f"  {r}")
PYEOF
```

### Step 3: Verify Data Flows Through Pipeline
```bash
# Monitor each layer in parallel
# Window 1: Backend processing logs
docker compose logs -f backend | grep -E "STEP|processed|error"

# Window 2: MongoDB write confirmation
watch -n 1 'docker compose exec -T mongodb mongosh shiptrack --eval "console.log(\"Events: \" + db.tracking_events.countDocuments())"'

# Window 3: Frontend connection status
docker compose logs -f frontend | grep -i "websocket\|connection"
```

---

## 🔍 Common Error Messages & Solutions

### Error: "Device or resource busy"
```bash
# Port already in use
sudo lsof -i :8000  # Find process
kill -9 <PID>       # Kill it
docker compose restart backend
```

### Error: "Connection refused"
```bash
# Service not running
docker compose ps  # Check status
docker compose logs mongodb  # Check why it failed to start
docker compose up -d mongodb --remove-orphans
```

### Error: "NotImplementedError: Database objects do not implement truth value testing"
```bash
# Fixed in db.py line 23: use `if _db is not None:` not `if _db:`
grep -n "if _db:" backend/app/db.py  # Should be empty
grep -n "if _db is not None:" backend/app/db.py  # Should show line 23
```

### Error: "No document found for GPS event"
```bash
# Data not reaching MongoDB
docker compose exec mongodb mongosh shiptrack
db.tracking_events.countDocuments()  # Should be > 0

# If 0: problem is before Step 6 (MongoDB save)
# Add logging at Step 1, 3, 5, 6 to isolate
```

---

## 📈 Expected Metrics After Fix

| Metric | Value | How to Verify |
|--------|-------|---------------|
| Shippers in DB | 100 | `db.shippers.countDocuments()` |
| Tracking events/min | ~6000 | `db.tracking_events.countDocuments()` after 1 min |
| WebSocket connections | 1+ | `curl http://localhost:8000/health` → `ws_connections` |
| GPS processing latency | <200ms | Backend logs: timestamp delta |
| Frontend online count | 100/100 | Frontend UI top bar |

---

## 🎯 Next Steps

1. Run **Phase 1** (Service Health Check) → Verify all containers running
2. Run **Phase 2, Layer 1** (Simulator → Backend) → Check for connection logs
3. If no connection logs → Check **Layer-by-Layer Debugging → Layer A**
4. If connection works → Check **Layer B** (GPS Validation) for STEP 1 failures
5. If validation passes → Check **Layer C** (MongoDB writes)
6. If writes succeed → Check **Layer D** (WebSocket broadcasting)

---

## 📝 Logging Output Expected

### ✅ When Everything Works
```
🔌 [WebSocket] New GPS ingest connection
[GPS] SHP-001 processed: lat=10.8231, lon=106.6297, speed=0.0km/h
[GPS] SHP-002 processed: lat=10.8245, lon=106.6310, speed=1.5km/h
[GPS] SHP-003 processed: lat=10.8260, lon=106.6325, speed=2.1km/h
...
[tick=10] Sent 100 GPS | online=100/100
```

### ❌ When Simulator Not Connecting
```
(No logs appear for [WebSocket] or [GPS])
(Only frontend /ws broadcasts show up)
```

### ❌ When Step Fails
```
[GPS Step 3] Speed/heading calc failed: ...
[GPS Step 6] Event save failed: ...
[GPS Step 8] Broadcast failed: ...
```

---

## ⚙️ Configuration Verification

```bash
# Verify .env variables are loaded
docker compose exec backend python -c "from app.config import settings; print(f'MongoDB: {settings.mongodb_url}'); print(f'CORS: {settings.cors_origins}')"

# Verify simulator config
docker compose --profile simulator config | grep -A 10 "simulator:"

# Verify requirements versions
docker compose exec backend pip show motor pymongo
```

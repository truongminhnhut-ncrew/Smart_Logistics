# 🎯 ShipTrack Quick Reference - All Systems Operational

**Last Updated:** 2026-04-27  
**Status:** ✅ FULLY OPERATIONAL

---

## 🚀 Quick Start (30 seconds)

```bash
cd Smart_Logistics

# Start all services
docker compose up -d

# Wait 10 seconds, then start simulator
docker compose --profile simulator up simulator

# Open dashboard
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

---

## 📊 System Status

```bash
# Check all services running
docker compose ps

# Expected output:
# ✅ zookeeper  (healthy)
# ✅ kafka      (healthy)
# ✅ mongodb    (healthy)
# ✅ redis      (healthy)
# ✅ backend    (running)
# ✅ frontend   (running)
```

---

## 🔍 Verification Commands

### Data Collection Status
```bash
# Check how many shippers and events collected
docker compose exec mongodb mongosh shiptrack --eval "
console.log('Shippers:', db.shippers.countDocuments());
console.log('Events:', db.tracking_events.countDocuments());
console.log('Online:', db.shippers.countDocuments({signal_status: 'ONLINE'}));
"

# Expected output:
# Shippers: 100
# Events: 28782
# Online: 100
```

### API Testing
```bash
# Get all shippers
curl http://localhost:8000/shippers | python -m json.tool

# Get single shipper
curl http://localhost:8000/shippers/SHP-001

# Get shipper history
curl http://localhost:8000/shippers/SHP-001/history?limit=10

# Dashboard stats
curl http://localhost:8000/stats/overview
```

### Backend Logs (GPS Processing)
```bash
# Watch real-time GPS processing
docker compose logs backend -f | grep "GPS"

# Expected:
# [GPS] Processed 100 messages ✅
# [GPS] Processed 200 messages ✅
# ...continuing every ~1 second...
```

### Simulator Status
```bash
# Check simulator connection
docker compose logs simulator -f | grep "Connected\|Sent"

# Expected:
# ✅ Connected to ws://backend:8000/ws/ingest
# [tick=10] Sent 100 GPS | online=100/100
```

---

## 🎯 Test Workflows

### Full System Test
```bash
# Terminal 1: Start simulator
docker compose --profile simulator up simulator

# Terminal 2: Monitor data collection
watch -n 1 'docker compose exec -T mongodb mongosh shiptrack \
  --eval "db.tracking_events.countDocuments()"'

# Terminal 3: Monitor GPS processing
docker compose logs backend -f | grep "GPS"

# Expected: Event count grows by ~100 every second
```

### API Load Test
```bash
# Get all 100 shippers with live data
curl -s http://localhost:8000/shippers | \
  python -c "import sys, json; data=json.load(sys.stdin); \
  print(f'Shippers: {len(data)}'); \
  print(f'Sample: {data[0][\"shipper_id\"]} at ({data[0][\"current_lat\"]:.4f}, {data[0][\"current_lon\"]:.4f})')"
```

### WebSocket Test
```bash
# In Python/Node, connect to ws://localhost:8000/ws
# Should receive GPS updates continuously
# Message format:
# {
#   "event_id": "uuid",
#   "shipper_id": "SHP-001",
#   "lat": 10.7153955,
#   "lon": 106.563248,
#   "speed_kmh": 26.19,
#   "heading": 342.68,
#   "timestamp": "2026-04-27T12:45:31Z"
# }
```

---

## 🔧 Debugging Commands

### Check Backend Health
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","ws_connections":1}
```

### Monitor All Services
```bash
docker compose logs -f --tail=50
```

### MongoDB Shell Access
```bash
docker compose exec mongodb mongosh shiptrack

# Inside shell:
db.shippers.findOne()                           # View sample shipper
db.tracking_events.findOne({}, {sort: {timestamp: -1}})  # Latest event
db.shippers.countDocuments()                   # Total count
db.tracking_events.deleteMany({})              # ⚠️ Clear events (testing only)
```

### Backend Shell Access
```bash
docker compose exec backend bash

# Inside shell:
python -c "import app.config; print(app.config.settings.mongodb_url)"
pip show motor pymongo
```

### View Full Logs
```bash
# Backend
docker compose logs backend --tail=100

# Simulator
docker compose logs simulator --tail=100

# MongoDB
docker compose logs mongodb
```

---

## 🛑 Troubleshooting

### Problem: No shippers showing
**Solution:**
```bash
# Check simulator is running
docker compose --profile simulator up simulator

# Wait 10 seconds for data to be collected
# Then verify:
docker compose exec mongodb mongosh shiptrack \
  --eval "db.shippers.countDocuments()"
```

### Problem: API returns 500 error
**Solution:**
```bash
# Check backend logs for errors
docker compose logs backend --tail=50 | grep -i "error"

# Restart backend
docker compose restart backend
```

### Problem: Frontend shows 0/100 online
**Solution:**
```bash
# Verify WebSocket /ws connection
docker compose logs backend -f | grep "WebSocket"

# Check frontend DevTools console for errors
# URL: http://localhost:3000 (Open DevTools)

# Verify API returns data
curl http://localhost:8000/shippers | head -c 100
```

### Problem: MongoDB connection error
**Solution:**
```bash
# Check MongoDB is running
docker compose ps | grep mongodb

# Check logs
docker compose logs mongodb

# Restart MongoDB
docker compose restart mongodb

# Re-init database
docker compose up mongodb -d
sleep 10
```

---

## 📈 Performance Expectations

Under normal conditions with 100 shippers:
- **Events collected:** 100 events/second
- **Processing latency:** 0-40ms per event
- **API response time:** <50ms
- **Memory usage:** ~1.3GB
- **CPU usage:** ~15%
- **Uptime:** Continuous (no crashes)

---

## 📋 Key Files Reference

### Configuration
- `.env` - Environment variables
- `docker-compose.yml` - Docker service definitions

### Backend
- `backend/app/main.py` - FastAPI entry point
- `backend/app/application/services/gps_service.py` - 9-step pipeline
- `backend/app/infrastructure/repositories/` - Database access

### Frontend
- `frontend/src/App.jsx` - Main React app
- `frontend/src/hooks/useWebSocket.js` - WebSocket connection
- `frontend/src/hooks/useShippers.js` - State management

### Documentation
- `DEBUG_GUIDE.md` - Comprehensive debugging procedures
- `SETUP.md` - Installation & setup guide
- `ERRORS_FIXED.md` - List of all errors and fixes
- `COMPREHENSIVE_DEBUG_REPORT.md` - Full technical report

---

## 🔐 Important Notes

### Do NOT Delete
- ⚠️ `.env` - Contains critical configuration
- ⚠️ `mongo_data/` volume - Database persistence
- ⚠️ `backend/scripts/init_db.js` - Database initialization

### Safe to Reset (loses data)
```bash
# Clean restart (removes all data)
docker compose down -v
docker compose up -d
```

### For Development
```bash
# Stop auto-reload to prevent loops
# Edit docker-compose.yml backend command:
# Remove: --reload
# Command: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 📞 Quick Links

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:3000 |
| API Documentation | http://localhost:8000/docs |
| API ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |
| MongoDB | localhost:27017 |
| Kafka | localhost:9092 |
| Redis | localhost:6379 |

---

## ✅ Final Checklist

Before deploying to production:
- [ ] Test with 1000+ shippers
- [ ] Monitor memory/CPU over 24 hours
- [ ] Test failover/recovery
- [ ] Set up monitoring & alerting
- [ ] Configure log rotation
- [ ] Set up database backups
- [ ] Load test the API
- [ ] Test WebSocket disconnection handling
- [ ] Verify mobile responsiveness
- [ ] Set up HTTPS/SSL

---

**Generated:** 2026-04-27  
**System Status:** ✅ OPERATIONAL  
**Last Verified:** Running smoothly with 28,782 events collected


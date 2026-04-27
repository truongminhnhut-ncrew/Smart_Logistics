# 🚀 ShipTrack - Getting Started Guide

**Real-time Shipper Tracking System**  
Last Updated: 2026-04-27

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start with Docker](#quick-start-with-docker)
3. [Local Development Setup](#local-development-setup)
4. [Accessing the Application](#accessing-the-application)
5. [Troubleshooting](#troubleshooting)
6. [Common Commands](#common-commands)

---

## Prerequisites

### For Docker (Recommended)
- ✅ Docker Desktop installed
- ✅ Docker Compose v2.0+
- ✅ 4GB RAM minimum
- ✅ Port availability: 3000, 8000, 27017, 9092, 6379

### For Local Development
- ✅ Python 3.11+
- ✅ Node.js 18+
- ✅ MongoDB 7.0 (local or Docker)
- ✅ Kafka (local or Docker)
- ✅ Redis (local or Docker)

---

## Quick Start with Docker

### Step 1: Navigate to Project Directory

```bash
cd Smart_Logistics
```

### Step 2: Configure Environment (if needed)

```bash
cp .env.example .env
```

The `.env` file is already created with default settings.

### Step 3: Start All Services

```bash
docker compose up -d
```

**What it does:**
- Starts Zookeeper (Kafka dependency)
- Starts Kafka (message queue)
- Starts MongoDB (database)
- Starts Redis (cache)
- Starts Backend (FastAPI)
- Starts Frontend (React)

**Expected output:**
```
[+] Running 6/6
 ✔ Container smart_logistics-zookeeper-1   Running
 ✔ Container smart_logistics-kafka-1       Running
 ✔ Container smart_logistics-mongodb-1     Running
 ✔ Container smart_logistics-redis-1       Running
 ✔ Container smart_logistics-backend-1     Running
 ✔ Container smart_logistics-frontend-1    Running
```

### Step 4: Verify All Services are Healthy

```bash
docker compose ps
```

All containers should show status: **Healthy** or **Running** ✅

### Step 5: Start Virtual Shipper Simulator

**In a new terminal:**

```bash
docker compose --profile simulator up simulator
```

**Expected output:**
```
simulator-1 | 🛵 Initialized 100 virtual shippers
simulator-1 | ✅ Connected to ws://backend:8000/ws/ingest
simulator-1 | [tick=10] Sent 100 GPS | online=100/100
simulator-1 | [tick=20] Sent 100 GPS | online=100/100
```

### Step 6: Access the Application

Open your browser:

| Service | URL |
|---------|-----|
| **Frontend Dashboard** | http://localhost:3000 |
| **API Documentation** | http://localhost:8000/docs |
| **API ReDoc** | http://localhost:8000/redoc |
| **WebSocket** | ws://localhost:8000/ws |

---

## Local Development Setup

### Backend Setup

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements-local.txt

# 4. Start MongoDB, Kafka, Redis (using Docker)
docker compose up -d mongodb kafka redis zookeeper

# 5. Start Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend should be running at: http://localhost:8000

### Frontend Setup

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Start development server
npm run dev
```

Frontend should be running at: http://localhost:3000

### Simulator Setup

```bash
# In another terminal
cd backend
python -m data_generator.simulate
```

---

## Accessing the Application

### Dashboard (Frontend)

Navigate to: **http://localhost:3000**

**Features:**
- 3-panel layout: Shipper list | Map | Details
- Real-time GPS tracking for 100 shippers
- Dark theme with green accent
- Status indicators (DELIVERING, IDLE, OFFLINE, AVAILABLE)
- Dashboard stats (active shippers, total km, top performers)

### API Documentation

Navigate to: **http://localhost:8000/docs**

**Available Endpoints:**

#### Shippers
- `GET /shippers` - List all shippers
- `GET /shippers/{id}` - Get shipper details
- `GET /shippers/{id}/history` - Get shipper GPS history

#### Orders
- `GET /orders` - List all orders
- `GET /orders/pending` - Get pending orders
- `POST /orders` - Create new order
- `PATCH /orders/{id}/assign` - Assign to shipper
- `PATCH /orders/{id}/complete` - Mark delivered

#### Dashboard
- `GET /stats/overview` - Fleet overview
- `GET /stats/fleet` - Fleet statistics
- `GET /stats/tracking-events` - Tracking stats

#### WebSocket
- `WS /ws` - Real-time GPS updates (frontend)
- `WS /ws/ingest` - GPS stream input (simulator)

---

## Troubleshooting

### Issue: Containers not starting

**Solution:**
```bash
docker compose down -v
docker compose up -d
```

### Issue: MongoDB connection error

```bash
docker compose logs mongodb
```

If TTL index conflict, the init script will fix it automatically on fresh start.

### Issue: Frontend shows "0/100 online"

**Check:**
1. Simulator is running: `docker compose logs simulator`
2. Backend is healthy: `docker compose ps`
3. WebSocket connection: Open DevTools → Network → WS
4. Frontend console: Check for errors

**Solution:**
```bash
# Restart backend
docker compose restart backend
docker compose restart frontend
```

### Issue: API returns 500 error

```bash
docker compose logs backend
```

Check logs for specific error messages.

### Issue: High CPU usage

- Simulator generates 100 shippers × 1 GPS/sec = 100 msg/sec
- This is normal during operation
- Stop simulator if not needed: `Ctrl+C`

---

## Common Commands

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f mongodb
docker compose logs -f simulator

# Last 100 lines
docker compose logs --tail=100 backend
```

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "ws_connections": 5
}
```

### Stop Services

```bash
# Stop without removing
docker compose stop

# Stop and remove containers
docker compose down

# Remove volumes (database data)
docker compose down -v
```

### Rebuild Images

```bash
docker compose build --no-cache backend
docker compose up -d
```

### Execute Commands in Container

```bash
# MongoDB
docker compose exec mongodb mongosh shiptrack

# Backend shell
docker compose exec backend bash

# Frontend
docker compose exec frontend sh
```

---

## Performance Expectations

| Metric | Value |
|--------|-------|
| GPS Stream | 100 shippers × 1 msg/sec = 100 msg/sec |
| Processing Latency | < 200ms (GPS → Dashboard) |
| Database Writes | ~300 ops/sec |
| WebSocket Connections | 1000+ concurrent |
| Memory Usage | ~1.5GB (all services) |
| CPU Usage | 10-20% under load |

---

## Project Structure

```
Smart_Logistics/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── domain/       # Business entities
│   │   ├── application/  # Services
│   │   ├── infrastructure/ # Repositories
│   │   ├── presentation/ # API routers
│   │   └── main.py       # FastAPI app
│   ├── data_generator/   # Simulator
│   └── requirements.txt
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   ├── services/     # API client
│   │   └── App.jsx
│   └── package.json
├── docker-compose.yml    # Service definitions
├── .env                  # Environment config
└── README.md
```

---

## Next Steps

1. ✅ Start Docker Compose
2. ✅ Start Simulator
3. ✅ Open http://localhost:3000
4. ✅ Click on a shipper to see details
5. ✅ View API docs at http://localhost:8000/docs
6. ✅ Check dashboard stats

---

## Support

### Documentation Files

- **CLAUDE.md** - Original specification
- **project.md** - Implementation log
- **README.md** - Project overview

### Logs for Debugging

```bash
docker compose logs -f [service-name]
```

Available services: backend, frontend, mongodb, kafka, redis, zookeeper, simulator

### Common Issues

**Q: Frontend is blank**  
A: Simulator may not be running. Check `docker compose logs simulator`

**Q: API returns 500**  
A: Check backend logs: `docker compose logs backend`

**Q: WebSocket connection fails**  
A: Verify backend is running and CORS is configured correctly

---

## 🚀 You're All Set!

The ShipTrack system is now ready to use. Enjoy real-time shipper tracking! 

For more information, see the API documentation at http://localhost:8000/docs

---

**Created:** 2026-04-27  
**Last Updated:** 2026-04-27  
**Version:** 1.0.0

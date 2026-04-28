"""
main.py — FastAPI application entry point.

Wires together:
- Database connections
- WebSocket servers (frontend clients only)
- API routers
- Background simulation engine
"""

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import connect_to_mongo, close_mongo_connection, get_database
from app.infrastructure.repositories import ShipperRepository
from app.presentation.websocket.manager import ws_manager
from app.presentation.api.routers import shippers, orders, dashboard
from app.presentation.api.routers.simulation import router as simulation_router
from app.presentation.api.routers.incidents import router as incidents_router
from app.application.services.simulation_engine import simulation_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


# ── LIFESPAN ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect DB + launch simulation engine."""
    logger.info("Starting Smart Logistics Backend...")

    # Connect to MongoDB
    await connect_to_mongo()

    # Start simulation engine as background task
    task = asyncio.create_task(simulation_engine.run())
    logger.info("Simulation engine started (30 shippers)")

    yield

    # Shutdown
    task.cancel()
    logger.info("Shutting down...")
    await close_mongo_connection()


# ── FASTAPI APP ──────────────────────────────────────────
app = FastAPI(
    title="Smart Logistics API",
    description="Real-time Shipper Tracking & Simulation System",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API ROUTERS ───────────────────────────────────────────
app.include_router(shippers.router)
app.include_router(orders.router)
app.include_router(dashboard.router)
app.include_router(simulation_router)
app.include_router(incidents_router)


# ── HEALTH CHECK ──────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ws_clients": ws_manager.get_connection_count(),
        "simulation_phase": simulation_engine.phase,
        "shipper_count": len(simulation_engine.shippers),
    }


# ── WEBSOCKET — FRONTEND CLIENTS ──────────────────────────
@app.websocket("/ws")
async def websocket_client(websocket: WebSocket):
    """
    WebSocket endpoint for frontend browsers.

    Clients receive:
    - bulk_gps_update: all 30 shipper positions every second
    - shipper_arrived: when a dispatched shipper reaches warehouse
    - all_arrived_at_warehouse: trigger for delivery modal
    - delivery_assigned: when order is assigned
    - delivery_completed: when shipper reaches customer
    - simulation_completed: end of simulation
    - incident_created: new incident notification
    - incident_resolved: incident resolved
    """
    await ws_manager.connect_client(websocket)
    try:
        db = get_database()
        shipper_repo = ShipperRepository(db) if db is not None else None
        initial_shippers = await shipper_repo.find_all_frontend() if shipper_repo else []

        initial_state = {
            "type": "initial_state",
            "shippers": initial_shippers,
            "phase": simulation_engine.phase,
            "warehouse": {"lat": 10.8051, "lon": 106.7144},
        }
        import json
        await websocket.send_text(json.dumps(initial_state))

        # Keep connection alive — just listen
        while True:
            await websocket.receive_text()
    except Exception as e:
        logger.debug(f"[WS] Client disconnected: {e}")
    finally:
        await ws_manager.disconnect_client(websocket)


# ── ROOT ──────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "message": "Smart Logistics Real-time API v2.0",
        "docs": "/docs",
        "ws": "ws://localhost:8000/ws",
        "simulation": "/simulation/start",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )

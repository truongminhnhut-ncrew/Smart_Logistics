"""
main.py — FastAPI application entry point.

Wires together:
- Database connections
- WebSocket servers
- API routers
- Startup/shutdown events
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import connect_to_mongo, close_mongo_connection, get_db
from app.presentation.websocket.manager import ws_manager
from app.presentation.api.routers import shippers, orders, dashboard
from app.application.services import GPSService
from app.domain import GPSStreamPayload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


# ── LIFESPAN EVENTS ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting ShipTrack Backend...")
    await connect_to_mongo()
    yield
    # Shutdown
    logger.info("🛑 Shutting down...")
    await close_mongo_connection()


# ── FASTAPI APP ────────────────────────────────────────
app = FastAPI(
    title="ShipTrack API",
    description="Real-time Shipper Tracking System",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API ROUTERS ────────────────────────────────────────
app.include_router(shippers.router)
app.include_router(orders.router)
app.include_router(dashboard.router)


# ── HEALTH CHECK ───────────────────────────────────────
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "ws_connections": ws_manager.get_connection_count()}


# ── WEBSOCKET ENDPOINTS ────────────────────────────────

@app.websocket("/ws/ingest")
async def websocket_gps_ingest(websocket: WebSocket, db=Depends(get_db)):
    """
    WebSocket endpoint for GPS stream ingest.

    Receives GPS data from simulator/field devices.
    Processes through 9-step pipeline.

    Message format: {"shipper_id", "lat", "lon", "timestamp"}
    """
    await ws_manager.connect(websocket)

    try:
        gps_service = GPSService(db)

        while True:
            # Receive GPS data from simulator
            data = await websocket.receive_json()

            # Parse as GPS payload
            try:
                gps_payload = GPSStreamPayload(**data)
                # Process through 9-step pipeline
                await gps_service.process_gps_stream(gps_payload)
            except Exception as e:
                logger.error(f"[GPS Processing] Error: {e}")
                continue

    except Exception as e:
        logger.warning(f"[WebSocket] Connection error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


@app.websocket("/ws")
async def websocket_client(websocket: WebSocket):
    """
    WebSocket endpoint for frontend clients.

    Broadcast channel for all GPS updates.
    Clients receive real-time location updates.

    Message format:
    {
        "event_id", "shipper_id", "lat", "lon", "speed_kmh", "heading",
        "eta_minutes", "order_id", "order_status", "delay_minutes", "timestamp"
    }
    """
    await ws_manager.connect(websocket)

    try:
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Frontend just listens, doesn't send
            pass

    except Exception as e:
        logger.debug(f"[Frontend WebSocket] Client disconnected: {e}")
    finally:
        await ws_manager.disconnect(websocket)


# ── ROOT ───────────────────────────────────────────────
@app.get("/")
async def root():
    """API documentation."""
    return {
        "message": "ShipTrack Real-time Shipper Tracking API",
        "docs": "/docs",
        "ws_ingest": "ws://localhost:8000/ws/ingest",
        "ws_client": "ws://localhost:8000/ws",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )

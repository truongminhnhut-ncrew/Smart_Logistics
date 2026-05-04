"""
Simulation control endpoints.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.application.services.simulation_engine import (
    WAREHOUSE_ID,
    WAREHOUSE_LAT,
    WAREHOUSE_LON,
    simulation_engine,
)
from app.db import get_db
from app.infrastructure.repositories import OrderRepository, ShipperRepository
from app.presentation.websocket.manager import ws_manager

router = APIRouter(prefix="/simulation", tags=["simulation"])


class DispatchRequest(BaseModel):
    shipper_ids: List[str]


class DeliveryRequest(BaseModel):
    shipper_id: str
    dest_lat: float
    dest_lon: float
    destination_text: str
    order_id: Optional[str] = None
    items_count: int = 1
    weight_kg: Optional[float] = None
    note: Optional[str] = None


class IncidentRequest(BaseModel):
    shipper_id: str
    incident_type: str
    rain_level: str = "MEDIUM"


@router.post("/start")
async def start_simulation():
    """Start simulation and auto-dispatch nearest idle shippers."""
    simulation_engine.phase = "STARTED"

    nearest = simulation_engine.get_nearest_to_warehouse(top_n=3)
    auto_shipper_ids = [item["shipper_id"] for item in nearest]

    if auto_shipper_ids:
        await simulation_engine.dispatch_to_warehouse(auto_shipper_ids)
        await ws_manager.broadcast_clients(
            {
                "type": "dispatch_started",
                "shipper_ids": auto_shipper_ids,
                "warehouse_lat": WAREHOUSE_LAT,
                "warehouse_lon": WAREHOUSE_LON,
                "auto": True,
            }
        )

    return {
        "status": "started",
        "phase": simulation_engine.phase,
        "shipper_count": len(simulation_engine.shippers),
        "auto_dispatched_ids": auto_shipper_ids,
        "warehouse": {
            "id": WAREHOUSE_ID,
            "lat": WAREHOUSE_LAT,
            "lon": WAREHOUSE_LON,
            "address": "02 Vo Oanh, Binh Thanh, TP.HCM",
        },
    }


@router.get("/state")
async def get_simulation_state():
    """Get the current simulation state."""
    return {
        "phase": simulation_engine.phase,
        "tick": simulation_engine._tick,
        "dispatched_ids": simulation_engine.dispatched_ids,
        "arrived_at_warehouse": simulation_engine._arrived_at_warehouse,
        "shipper_count": len(simulation_engine.shippers),
        "warehouse": {"lat": WAREHOUSE_LAT, "lon": WAREHOUSE_LON},
    }


@router.get("/shippers")
async def get_all_shippers(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Return current shippers from MongoDB for compatibility."""
    repo = ShipperRepository(db)
    return await repo.find_all_frontend()


@router.get("/nearest")
async def get_nearest_shippers(top_n: int = 3):
    """Return the top nearest idle shippers to the warehouse."""
    nearest = simulation_engine.get_nearest_to_warehouse(top_n)
    return {
        "warehouse": {"lat": WAREHOUSE_LAT, "lon": WAREHOUSE_LON},
        "nearest": nearest,
    }


@router.post("/dispatch")
async def dispatch_to_warehouse(req: DispatchRequest):
    """Dispatch selected shippers to the warehouse."""
    if simulation_engine.phase not in ("STARTED", "IDLE"):
        raise HTTPException(400, f"Cannot dispatch in phase: {simulation_engine.phase}")

    await simulation_engine.dispatch_to_warehouse(req.shipper_ids)

    await ws_manager.broadcast_clients(
        {
            "type": "dispatch_started",
            "shipper_ids": req.shipper_ids,
            "warehouse_lat": WAREHOUSE_LAT,
            "warehouse_lon": WAREHOUSE_LON,
        }
    )

    return {
        "status": "dispatched",
        "shipper_ids": req.shipper_ids,
        "destination": "02 Vo Oanh, Binh Thanh, TP.HCM",
    }


@router.post("/assign-delivery")
async def assign_delivery(req: DeliveryRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Assign a delivery to a shipper waiting at the warehouse."""
    if req.shipper_id not in simulation_engine.shippers:
        raise HTTPException(404, f"Shipper {req.shipper_id} not found")

    order_id = req.order_id or f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

    order_repo = OrderRepository(db)
    await order_repo.create_order(
        order_id=order_id,
        warehouse_id=WAREHOUSE_ID,
        dest_lat=req.dest_lat,
        dest_lon=req.dest_lon,
        destination_text=req.destination_text,
        priority="MEDIUM",
    )
    await order_repo.assign_shipper(order_id, req.shipper_id)

    await simulation_engine.set_delivery_target(
        shipper_id=req.shipper_id,
        dest_lat=req.dest_lat,
        dest_lon=req.dest_lon,
        order_id=order_id,
    )

    shipper_repo = ShipperRepository(db)
    await shipper_repo.update_status(req.shipper_id, "DELIVERING")
    await shipper_repo.set_active_order(req.shipper_id, order_id)

    await ws_manager.broadcast_clients(
        {
            "type": "delivery_assigned",
            "shipper_id": req.shipper_id,
            "order_id": order_id,
            "dest_lat": req.dest_lat,
            "dest_lon": req.dest_lon,
            "destination_text": req.destination_text,
        }
    )

    return {
        "status": "delivering",
        "shipper_id": req.shipper_id,
        "order_id": order_id,
        "destination": req.destination_text,
    }


@router.post("/complete")
async def complete_simulation():
    """Mark the simulation as completed."""
    simulation_engine.complete_simulation()
    await ws_manager.broadcast_clients({"type": "simulation_completed"})
    return {"status": "completed"}


@router.post("/reset")
async def reset_simulation():
    """Reset the simulation and reseed Mongo from memory."""
    simulation_engine._init_shippers()
    simulation_engine.phase = "IDLE"
    simulation_engine.dispatched_ids = []
    simulation_engine._arrived_at_warehouse = []
    simulation_engine._delivery_targets = {}
    simulation_engine._tick = 0
    await simulation_engine.sync_all_to_mongo(clear_existing=True)
    await ws_manager.broadcast_clients({"type": "simulation_reset"})
    return {"status": "reset", "shipper_count": len(simulation_engine.shippers)}


@router.post("/incident/apply")
async def apply_incident(req: IncidentRequest):
    """Apply incident to a shipper."""
    if req.shipper_id not in simulation_engine.shippers:
        raise HTTPException(404, f"Shipper {req.shipper_id} not found")

    result = simulation_engine.apply_incident(
        req.shipper_id,
        req.incident_type,
        rain_level=req.rain_level
    )

    await ws_manager.broadcast_clients({
        "type": "incident_created",
        "shipper_id": req.shipper_id,
        "incident_type": req.incident_type,
        "result": result,
    })

    return result


@router.post("/incident/resolve/{shipper_id}")
async def resolve_incident(shipper_id: str):
    """Resolve incident for a shipper."""
    if shipper_id not in simulation_engine.shippers:
        raise HTTPException(404, f"Shipper {shipper_id} not found")

    result = simulation_engine.resolve_incident(shipper_id)

    await ws_manager.broadcast_clients({
        "type": "incident_resolved",
        "shipper_id": shipper_id,
        "result": result,
    })

    return result

@router.get("/stats/fleet")
async def get_fleet_stats():
    """GET /simulation/stats/fleet — Fleet statistics theo TONGQUAN.md."""
    return simulation_engine.get_fleet_stats()


class IncidentApplyRequest(BaseModel):
    shipper_id: str
    incident_type: str  # TRAFFIC_JAM | HEAVY_RAIN | CUSTOMER_ABSENT | VEHICLE_BREAKDOWN | LOST_CONNECTION
    rain_level: Optional[str] = "MEDIUM"  # Fix #6: LIGHT | MEDIUM | HEAVY (for HEAVY_RAIN)


@router.post("/incident/apply")
async def apply_incident(req: IncidentApplyRequest):
    """Apply an incident to a shipper in-memory and broadcast."""
    result = simulation_engine.apply_incident(req.shipper_id, req.incident_type, req.rain_level or "MEDIUM")
    if "error" in result:
        raise HTTPException(404, result["error"])

    # Broadcast incident_applied
    ws_payload = {
        "type": "incident_applied",
        "shipper_id": req.shipper_id,
        "incident_type": req.incident_type,
        "severity": result["severity"],
        "estimated_delay": result["estimated_delay"],
        "recommended_action": result["recommended_action"],
        "location": result["location"],
    }
    if "rain_level" in result:
        ws_payload["rain_level"] = result["rain_level"]
    await ws_manager.broadcast_clients(ws_payload)

    # Section 23: customer_notification WS event
    shipper = simulation_engine.shippers.get(req.shipper_id)
    if shipper and shipper.order_id:
        reason_map = {
            "TRAFFIC_JAM": "kẹt xe",
            "HEAVY_RAIN": "mưa lớn",
            "CUSTOMER_ABSENT": "khách vắng",
            "VEHICLE_BREAKDOWN": "hư xe",
            "LOST_CONNECTION": "mất kết nối",
        }
        eta = shipper.calculate_eta() or 0
        await ws_manager.broadcast_clients({
            "type": "customer_notification",
            "order_id": shipper.order_id,
            "shipper_id": req.shipper_id,
            "message": f"Đơn hàng của bạn bị delay ~{result['estimated_delay']} phút do {reason_map.get(req.incident_type, req.incident_type)}",
            "new_eta_minutes": round(eta + result["estimated_delay"], 1),
            "reason": req.incident_type,
        })

    # Fix #10: route_updated WS event (for rerouting incidents)
    if req.incident_type in ("TRAFFIC_JAM", "HEAVY_RAIN"):
        await ws_manager.broadcast_clients({
            "type": "route_updated",
            "shipper_id": req.shipper_id,
            "reason": req.incident_type,
            "message": f"Route cập nhật cho {req.shipper_id} do {req.incident_type}",
        })

    return result


@router.post("/incident/resolve/{shipper_id}")
async def resolve_incident(shipper_id: str):
    """Resolve an active incident for a shipper."""
    result = simulation_engine.resolve_incident(shipper_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    await ws_manager.broadcast_clients({"type": "incident_resolved", "shipper_id": shipper_id})
    return result

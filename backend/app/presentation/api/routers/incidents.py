"""
presentation/api/routers/incidents.py — Incident management endpoints.

POST /incidents                    — Tạo sự cố mới
GET  /incidents                    — Lấy tất cả sự cố
GET  /incidents/active             — Lấy sự cố đang xảy ra
PATCH /incidents/{id}/resolve      — Đánh dấu hết sự cố
"""

import uuid
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.db import get_db
from app.domain import CreateIncidentRequest
from app.infrastructure.repositories import IncidentRepository
from app.presentation.websocket.manager import ws_manager

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", status_code=201)
async def create_incident(
    req: CreateIncidentRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Tạo sự cố mới và broadcast realtime lên tất cả clients.
    """
    incident_id = f"INC-{str(uuid.uuid4())[:6].upper()}"
    repo = IncidentRepository(db)

    await repo.create_incident(
        incident_id=incident_id,
        shipper_id=req.shipper_id,
        incident_type=req.incident_type.value,
        description=req.description,
        order_id=req.order_id,
    )

    # Broadcast realtime notification
    incident_data = {
        "type": "incident_created",
        "incident_id": incident_id,
        "shipper_id": req.shipper_id,
        "order_id": req.order_id,
        "incident_type": req.incident_type.value,
        "description": req.description,
        "status": "ACTIVE",
    }
    await ws_manager.broadcast_clients(incident_data)

    return {
        "incident_id": incident_id,
        "status": "created",
        "shipper_id": req.shipper_id,
        "incident_type": req.incident_type.value,
    }


@router.get("")
async def list_incidents(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Lấy tất cả sự cố (gần đây nhất trước)."""
    repo = IncidentRepository(db)
    return await repo.find_all_recent(limit=100)


@router.get("/active")
async def get_active_incidents(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Lấy sự cố đang xảy ra (chưa resolved)."""
    repo = IncidentRepository(db)
    return await repo.find_active()


@router.patch("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Đánh dấu sự cố đã kết thúc."""
    repo = IncidentRepository(db)
    success = await repo.resolve_incident(incident_id)
    if not success:
        raise HTTPException(404, f"Incident {incident_id} not found")

    # Broadcast resolution
    await ws_manager.broadcast_clients({
        "type": "incident_resolved",
        "incident_id": incident_id,
    })

    return {"status": "resolved", "incident_id": incident_id}


@router.get("/shipper/{shipper_id}")
async def get_shipper_incidents(
    shipper_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Lấy sự cố của một shipper cụ thể."""
    repo = IncidentRepository(db)
    return await repo.find_by_shipper(shipper_id)

"""
presentation/api/routers/shippers.py — Shipper endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.db import get_db
from app.domain import Shipper
from app.infrastructure.repositories import ShipperRepository, TrackingEventRepository

router = APIRouter(prefix="/shippers", tags=["shippers"])


@router.get("", response_model=List[dict])
async def list_shippers(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Get all shippers with current GPS state.

    Returns 100 shippers with live coordinates, speed, status.
    """
    repo = ShipperRepository(db)
    shippers = await repo.find_all_shippers()
    return shippers


@router.get("/{shipper_id}", response_model=dict)
async def get_shipper(shipper_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get shipper details by ID."""
    repo = ShipperRepository(db)
    shipper = await repo.find_by_id(shipper_id)
    if not shipper:
        raise HTTPException(status_code=404, detail="Shipper not found")
    return shipper


@router.get("/{shipper_id}/history", response_model=List[dict])
async def get_shipper_history(
    shipper_id: str,
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get last N tracking events for shipper.

    Shows GPS history, speed, heading, ETA updates.
    """
    repo = TrackingEventRepository(db)
    events = await repo.find_by_shipper(shipper_id, limit=limit)
    if not events:
        raise HTTPException(status_code=404, detail="No events found")
    return events


@router.get("/{shipper_id}/online-status", response_model=dict)
async def check_shipper_status(shipper_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Check shipper online/signal status."""
    repo = ShipperRepository(db)
    shipper = await repo.find_by_id(shipper_id)
    if not shipper:
        raise HTTPException(status_code=404, detail="Shipper not found")

    return {
        "shipper_id": shipper_id,
        "signal_status": shipper.get("signal_status"),
        "current_status": shipper.get("current_status"),
        "last_ping_at": shipper.get("last_ping_at"),
    }

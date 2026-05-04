"""
Shipper management endpoints backed by simulation engine (realtime) + MongoDB (history).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.infrastructure.repositories import ShipperRepository, TrackingEventRepository
from app.application.services.simulation_engine import simulation_engine

router = APIRouter(prefix="/shippers", tags=["shippers"])


@router.get("", response_model=List[dict])
async def list_shippers(db: AsyncIOMotorDatabase = Depends(get_db)):
    """List all shippers — realtime from simulation_engine, not MongoDB."""
    # Return in-memory shipper state from simulation engine for realtime updates
    return simulation_engine.get_all_shippers_state()


@router.get("/{shipper_id}", response_model=dict)
async def get_shipper(shipper_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get single shipper details — realtime from simulation_engine."""
    shipper = simulation_engine.shippers.get(shipper_id)
    if not shipper:
        raise HTTPException(status_code=404, detail=f"Shipper {shipper_id} not found")
    # Return in-memory shipper payload for realtime state
    return shipper.to_ws_payload()


@router.get("/{shipper_id}/history", response_model=List[dict])
async def get_shipper_history(
    shipper_id: str,
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return recent tracking events for a shipper from MongoDB."""
    shipper_repo = ShipperRepository(db)
    if not await shipper_repo.find_by_id(shipper_id):
        raise HTTPException(status_code=404, detail=f"Shipper {shipper_id} not found")

    tracking_repo = TrackingEventRepository(db)
    return await tracking_repo.find_by_shipper(shipper_id, limit=limit)

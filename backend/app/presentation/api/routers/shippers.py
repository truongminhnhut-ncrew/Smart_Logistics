"""
Shipper management endpoints backed by MongoDB.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.infrastructure.repositories import ShipperRepository, TrackingEventRepository

router = APIRouter(prefix="/shippers", tags=["shippers"])


@router.get("", response_model=List[dict])
async def list_shippers(db: AsyncIOMotorDatabase = Depends(get_db)):
    """List all shippers from MongoDB in the UI-friendly shape."""
    repo = ShipperRepository(db)
    return await repo.find_all_frontend()


@router.get("/{shipper_id}", response_model=dict)
async def get_shipper(shipper_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get single shipper details from MongoDB."""
    repo = ShipperRepository(db)
    shipper = await repo.find_by_id(shipper_id)
    if not shipper:
        raise HTTPException(status_code=404, detail=f"Shipper {shipper_id} not found")
    return ShipperRepository.to_frontend_payload(shipper)


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

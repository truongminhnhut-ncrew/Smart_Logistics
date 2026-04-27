"""
presentation/api/routers/dashboard.py — Dashboard statistics endpoints.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.infrastructure.repositories import ShipperRepository, OrderRepository, TrackingEventRepository

router = APIRouter(prefix="/stats", tags=["dashboard"])


@router.get("/overview", response_model=dict)
async def get_overview(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Get dashboard overview stats.

    Returns:
    - Active shipper count
    - Total distance traveled
    - Pending orders
    - Top shippers
    """
    shipper_repo = ShipperRepository(db)
    order_repo = OrderRepository(db)

    # Fleet stats
    fleet_stats = await shipper_repo.get_stats()

    # Orders stats
    total_orders = await order_repo.count()
    pending_orders = await order_repo.count({"current_status": "PENDING"})
    in_transit = await order_repo.count({"current_status": "IN_TRANSIT"})
    delivered = await order_repo.count({"current_status": "DELIVERED"})

    # Top shippers
    top_shippers = await shipper_repo.get_top_shippers(limit=5)

    return {
        "timestamp": "2025-01-01T12:00:00Z",
        "fleet": fleet_stats,
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "in_transit": in_transit,
            "delivered": delivered,
        },
        "top_shippers": [
            {
                "shipper_id": s.get("shipper_id"),
                "name": s.get("name"),
                "completed_count": s.get("completed_count"),
                "total_distance_km": s.get("total_distance_km"),
            }
            for s in top_shippers
        ],
    }


@router.get("/fleet", response_model=dict)
async def get_fleet_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get detailed fleet statistics."""
    repo = ShipperRepository(db)
    return await repo.get_stats()


@router.get("/tracking-events", response_model=dict)
async def get_tracking_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get tracking event collection statistics."""
    repo = TrackingEventRepository(db)
    return await repo.get_collection_stats()


@router.get("/recent-events", response_model=list)
async def get_recent_events(
    minutes: int = 5,
    limit: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get recent GPS events from last N minutes."""
    repo = TrackingEventRepository(db)
    events = await repo.find_recent_events(minutes=minutes, limit=limit)
    return events

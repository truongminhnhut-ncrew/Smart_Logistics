"""
infrastructure/repositories/shipper_repository.py — Shipper data access.
"""

from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain import Shipper
from app.config import settings
from .base_repository import BaseRepository


class ShipperRepository(BaseRepository):
    """Repository for Shipper data access."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.shippers, Shipper)

    def _active_shipper_filter(self) -> dict:
        count = max(1, settings.simulator_shipper_count)
        shipper_ids = [f"SHP-{i:03d}" for i in range(1, count + 1)]
        return {"shipper_id": {"$in": shipper_ids}}

    async def find_by_id(self, shipper_id: str) -> Optional[dict]:
        """Find shipper by shipper_id (PK)."""
        return await self.find_one({"shipper_id": shipper_id})

    async def find_all_shippers(self) -> List[dict]:
        """Get all shippers with current GPS state."""
        cursor = self.collection.find(self._active_shipper_filter(), projection={"_id": 0}).sort("shipper_id", 1)
        return await cursor.to_list(length=settings.simulator_shipper_count)

    async def find_online_shippers(self) -> List[dict]:
        """Get all online shippers."""
        return await self.find_many({
            **self._active_shipper_filter(),
            "signal_status": "ONLINE",
        })

    async def find_available_shippers(self) -> List[dict]:
        """Get all available (IDLE) shippers."""
        return await self.find_many({
            **self._active_shipper_filter(),
            "current_status": "IDLE",
        })

    async def find_delivering_shippers(self) -> List[dict]:
        """Get all shippers currently delivering."""
        return await self.find_many({
            **self._active_shipper_filter(),
            "current_status": "DELIVERING",
        })

    async def find_by_status(self, status: str) -> List[dict]:
        """Find all shippers with given status."""
        return await self.find_many({
            **self._active_shipper_filter(),
            "current_status": status,
        })

    async def update_gps_state(
        self,
        shipper_id: str,
        lat: float,
        lon: float,
        speed_kmh: float,
        heading: float,
        timestamp: datetime,
    ) -> None:
        """
        Update GPS state for shipper.
        🔴 Called on every GPS update (~1 sec).
        """
        await self.update_one(
            {"shipper_id": shipper_id},
            {
                "current_lat": lat,
                "current_lon": lon,
                "current_speed_kmh": speed_kmh,
                "heading": heading,
                "last_ping_at": timestamp,
                "signal_status": "ONLINE",
                "updated_at": datetime.utcnow(),
            },
            upsert=True,
        )

    async def update_status(self, shipper_id: str, status: str) -> None:
        """Update shipper operational status."""
        await self.update_one(
            {"shipper_id": shipper_id},
            {
                "current_status": status,
                "updated_at": datetime.utcnow(),
            },
            upsert=True,
        )

    async def mark_offline(self, shipper_id: str) -> None:
        """Mark shipper as OFFLINE (no GPS for 30+ sec)."""
        await self.update_one(
            {"shipper_id": shipper_id},
            {
                "signal_status": "OFFLINE",
                "updated_at": datetime.utcnow(),
            },
        )

    async def increment_completed_orders(self, shipper_id: str, distance_km: float) -> None:
        """Increment completed order count + total distance."""
        await self.collection.update_one(
            {"shipper_id": shipper_id},
            {
                "$inc": {
                    "completed_count": 1,
                    "total_distance_km": distance_km,
                }
            },
        )

    async def get_top_shippers(self, limit: int = 10) -> List[dict]:
        """Get top shippers by completed orders."""
        cursor = self.collection.find(
            self._active_shipper_filter(), projection={"_id": 0}
        ).sort([("completed_count", -1), ("shipper_id", 1)]).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_stats(self) -> dict:
        """Get shipper fleet statistics."""
        shipper_filter = self._active_shipper_filter()
        total = await self.count(shipper_filter)
        online = await self.count({**shipper_filter, "signal_status": "ONLINE"})
        delivering = await self.count({**shipper_filter, "current_status": "DELIVERING"})

        # Total distance (sum all shippers)
        result = await self.collection.aggregate([
            {"$match": shipper_filter},
            {"$group": {"_id": None, "total_km": {"$sum": "$total_distance_km"}}}
        ]).to_list(length=1)

        total_km = result[0]["total_km"] if result else 0.0

        return {
            "total_shippers": total,
            "online_count": online,
            "delivering_count": delivering,
            "total_distance_km": round(total_km, 2),
        }

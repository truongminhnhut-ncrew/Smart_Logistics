"""
Repository helpers for shipper data access.
"""

from datetime import datetime
from typing import Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain import Shipper
from .base_repository import BaseRepository


class ShipperRepository(BaseRepository):
    """Repository for shipper data access."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.shippers, Shipper)

    @staticmethod
    def to_frontend_payload(shipper: Optional[dict]) -> Optional[dict]:
        """Normalize a Mongo document to the frontend shipper shape."""
        if not shipper:
            return None

        return {
            "shipper_id": shipper.get("shipper_id"),
            "name": shipper.get("name"),
            "phone_number": shipper.get("phone_number"),
            "vehicle_type": shipper.get("vehicle_type", "motorcycle"),
            "vehicle_plate": shipper.get("vehicle_plate"),
            "lat": shipper.get("current_lat"),
            "lon": shipper.get("current_lon"),
            "speed_kmh": shipper.get("current_speed_kmh", 0.0),
            "heading": shipper.get("heading", 0.0),
            "status": shipper.get("current_status", "IDLE"),
            "signal_status": shipper.get("signal_status", "OFFLINE"),
            "completed_count": shipper.get("completed_count", 0),
            "total_distance_km": shipper.get("total_distance_km", 0.0),
            "last_ping_at": shipper.get("last_ping_at"),
            "order_id": shipper.get("active_order_id"),
            "updated_at": shipper.get("updated_at"),
        }

    async def find_by_id(self, shipper_id: str) -> Optional[dict]:
        """Find shipper by shipper_id (PK)."""
        return await self.find_one({"shipper_id": shipper_id})

    async def find_all_shippers(self) -> List[dict]:
        """Get all shippers with current GPS state."""
        return await self.find_all()

    async def find_all_frontend(self) -> List[dict]:
        """Return all shippers normalized for frontend consumption."""
        shippers = await self.find_all()
        return [
            payload
            for shipper in shippers
            if (payload := self.to_frontend_payload(shipper)) is not None
        ]

    async def find_online_shippers(self) -> List[dict]:
        """Get all online shippers."""
        return await self.find_many({"signal_status": "ONLINE"})

    async def find_available_shippers(self) -> List[dict]:
        """Get all available (IDLE) shippers."""
        return await self.find_many({"current_status": "IDLE"})

    async def find_delivering_shippers(self) -> List[dict]:
        """Get all shippers currently delivering."""
        return await self.find_many({"current_status": "DELIVERING"})

    async def find_by_status(self, status: str) -> List[dict]:
        """Find all shippers with given status."""
        return await self.find_many({"current_status": status})

    async def update_gps_state(
        self,
        shipper_id: str,
        lat: float,
        lon: float,
        speed_kmh: float,
        heading: float,
        timestamp: datetime,
    ) -> None:
        """Update GPS state for shipper."""
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

    async def set_active_order(self, shipper_id: str, order_id: Optional[str]) -> None:
        """Persist the shipper's current active order."""
        await self.update_one(
            {"shipper_id": shipper_id},
            {
                "active_order_id": order_id,
                "updated_at": datetime.utcnow(),
            },
            upsert=True,
        )

    async def mark_offline(self, shipper_id: str) -> None:
        """Mark shipper as OFFLINE."""
        await self.update_one(
            {"shipper_id": shipper_id},
            {
                "signal_status": "OFFLINE",
                "updated_at": datetime.utcnow(),
            },
        )

    async def upsert_shipper_snapshot(self, shipper: Dict) -> None:
        """Persist the current simulator snapshot into MongoDB."""
        timestamp = shipper.get("timestamp") or datetime.utcnow()
        await self.update_one(
            {"shipper_id": shipper["shipper_id"]},
            {
                "name": shipper.get("name", shipper["shipper_id"]),
                "phone_number": shipper.get("phone_number", "N/A"),
                "vehicle_type": shipper.get("vehicle_type", "motorcycle"),
                "vehicle_plate": shipper.get("vehicle_plate", f"SIM-{shipper['shipper_id'][-3:]}"),
                "current_lat": shipper["lat"],
                "current_lon": shipper["lon"],
                "current_speed_kmh": shipper.get("speed_kmh", 0.0),
                "heading": shipper.get("heading", 0.0),
                "current_status": shipper.get("status", "IDLE"),
                "signal_status": shipper.get("signal_status", "ONLINE"),
                "active_order_id": shipper.get("order_id"),
                "last_ping_at": timestamp,
                "updated_at": datetime.utcnow(),
            },
            upsert=True,
        )

    async def increment_completed_orders(self, shipper_id: str, distance_km: float) -> None:
        """Increment completed order count and total distance."""
        await self.collection.update_one(
            {"shipper_id": shipper_id},
            {
                "$inc": {
                    "completed_count": 1,
                    "total_distance_km": distance_km,
                },
                "$set": {
                    "active_order_id": None,
                    "updated_at": datetime.utcnow(),
                },
            },
        )

    async def get_top_shippers(self, limit: int = 10) -> List[dict]:
        """Get top shippers by completed orders."""
        cursor = self.collection.find({}, {"_id": 0}).sort("completed_count", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_stats(self) -> dict:
        """Get shipper fleet statistics."""
        total = await self.count()
        online = await self.count({"signal_status": "ONLINE"})
        delivering = await self.count({"current_status": "DELIVERING"})

        result = await self.collection.aggregate(
            [{"$group": {"_id": None, "total_km": {"$sum": "$total_distance_km"}}}]
        ).to_list(length=1)

        total_km = result[0]["total_km"] if result else 0.0

        return {
            "total_shippers": total,
            "online_count": online,
            "delivering_count": delivering,
            "total_distance_km": round(total_km, 2),
        }

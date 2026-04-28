"""
infrastructure/repositories/incident_repository.py — Incident data access.
"""

from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from .base_repository import BaseRepository


class IncidentRepository(BaseRepository):
    """Repository for Incident data access."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.incidents)

    async def find_by_id(self, incident_id: str) -> Optional[dict]:
        return await self.find_one({"incident_id": incident_id})

    async def find_active(self) -> List[dict]:
        """Get all unresolved incidents."""
        return await self.find_many({"status": "ACTIVE"})

    async def find_by_shipper(self, shipper_id: str) -> List[dict]:
        """Get all incidents for a shipper."""
        return await self.find_many({"shipper_id": shipper_id})

    async def find_all_recent(self, limit: int = 50) -> List[dict]:
        """Get most recent incidents."""
        cursor = self.collection.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def create_incident(
        self,
        incident_id: str,
        shipper_id: str,
        incident_type: str,
        description: str,
        order_id: Optional[str] = None,
    ) -> str:
        """Create a new incident."""
        now = datetime.utcnow()
        doc = {
            "incident_id": incident_id,
            "shipper_id": shipper_id,
            "order_id": order_id,
            "incident_type": incident_type,
            "description": description,
            "status": "ACTIVE",
            "created_at": now,
            "resolved_at": None,
        }
        return await self.create(doc)

    async def resolve_incident(self, incident_id: str) -> bool:
        """Mark incident as resolved."""
        count = await self.update_one(
            {"incident_id": incident_id},
            {
                "status": "RESOLVED",
                "resolved_at": datetime.utcnow(),
            },
        )
        return count > 0

    async def count_active(self) -> int:
        """Count active (unresolved) incidents."""
        return await self.count({"status": "ACTIVE"})

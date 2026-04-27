"""
infrastructure/repositories/incident_repository.py — Incident data access.
"""

from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain import Incident
from .base_repository import BaseRepository


class IncidentRepository(BaseRepository):
    """Repository for Incident data access."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.incidents, Incident)

    async def create_incident(
        self,
        incident_id: str,
        shipper_id: str,
        incident_type: str,
        severity: str,
        description: str,
        order_id: Optional[str] = None,
    ) -> str:
        """Create new incident."""
        now = datetime.utcnow()
        incident_doc = {
            "incident_id": incident_id,
            "shipper_id": shipper_id,
            "order_id": order_id,
            "incident_type": incident_type,
            "severity": severity,
            "description": description,
            "resolved": False,
            "created_at": now,
            "resolved_at": None,
            "updated_at": now,
        }
        return await self.create(incident_doc)

    async def find_by_id(self, incident_id: str) -> Optional[dict]:
        """Find incident by incident_id (PK)."""
        return await self.find_one({"incident_id": incident_id})

    async def find_by_shipper(self, shipper_id: str, limit: int = 100) -> List[dict]:
        """Get all incidents for a shipper."""
        return await self.find_many(
            {"shipper_id": shipper_id},
            limit=limit,
        )

    async def find_recent_by_shipper(self, shipper_id: str, limit: int = 5) -> List[dict]:
        """Get recent incidents for a shipper (most recent first)."""
        cursor = self.collection.find(
            {"shipper_id": shipper_id}, projection={"_id": 0}
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def find_unresolved(self) -> List[dict]:
        """Get all unresolved incidents."""
        return await self.find_many({"resolved": False})

    async def find_unresolved_by_shipper(self, shipper_id: str) -> List[dict]:
        """Get unresolved incidents for a shipper."""
        return await self.find_many({
            "shipper_id": shipper_id,
            "resolved": False,
        })

    async def resolve(self, incident_id: str) -> None:
        """Mark incident as resolved."""
        await self.update_one(
            {"incident_id": incident_id},
            {
                "resolved": True,
                "resolved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )

    async def count_unresolved(self) -> int:
        """Count total unresolved incidents."""
        return await self.count({"resolved": False})

    async def count_unresolved_by_shipper(self, shipper_id: str) -> int:
        """Count unresolved incidents for shipper."""
        return await self.count({
            "shipper_id": shipper_id,
            "resolved": False,
        })

    async def find_by_type(self, incident_type: str, limit: int = 100) -> List[dict]:
        """Get incidents of specific type."""
        return await self.find_many(
            {"incident_type": incident_type},
            limit=limit,
        )

    async def find_by_severity(self, severity: str, limit: int = 100) -> List[dict]:
        """Get incidents with specific severity."""
        return await self.find_many(
            {"severity": severity},
            limit=limit,
        )

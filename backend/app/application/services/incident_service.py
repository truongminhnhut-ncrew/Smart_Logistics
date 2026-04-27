"""
application/services/incident_service.py — Incident business logic.
"""

from datetime import datetime, timezone
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.infrastructure.repositories import IncidentRepository


class IncidentService:
    """Service for incident operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.repo = IncidentRepository(db)

    def _generate_incident_id(self) -> str:
        """
        Generate incident ID in format: INC-YYYYMMDD-XXXX

        Note: In production, this should be atomic with the database insert.
        For now, we use a simple counter approach.
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y%m%d")
        # Simple counter - in production, use a separate counter collection
        import uuid
        seq = str(uuid.uuid4().int % 10000).zfill(4)
        return f"INC-{date_str}-{seq}"

    async def create_incident(
        self,
        shipper_id: str,
        incident_type: str,
        severity: str,
        description: str,
        order_id: Optional[str] = None,
    ) -> str:
        """
        Create new incident.

        Returns incident_id.
        """
        incident_id = self._generate_incident_id()
        await self.repo.create_incident(
            incident_id=incident_id,
            shipper_id=shipper_id,
            incident_type=incident_type,
            severity=severity,
            description=description,
            order_id=order_id,
        )
        return incident_id

    async def resolve_incident(self, incident_id: str) -> None:
        """Mark incident as resolved."""
        await self.repo.resolve(incident_id)

    async def get_incident(self, incident_id: str) -> Optional[dict]:
        """Get incident by ID."""
        return await self.repo.find_by_id(incident_id)

    async def get_shipper_incidents(self, shipper_id: str, limit: int = 100) -> List[dict]:
        """Get all incidents for shipper."""
        return await self.repo.find_by_shipper(shipper_id, limit=limit)

    async def get_shipper_recent_incidents(self, shipper_id: str, limit: int = 5) -> List[dict]:
        """Get recent incidents for shipper."""
        return await self.repo.find_recent_by_shipper(shipper_id, limit=limit)

    async def get_unresolved_incidents(self) -> List[dict]:
        """Get all unresolved incidents."""
        return await self.repo.find_unresolved()

    async def get_unresolved_count(self) -> int:
        """Get count of unresolved incidents."""
        return await self.repo.count_unresolved()

    async def get_shipper_unresolved_count(self, shipper_id: str) -> int:
        """Get count of unresolved incidents for shipper."""
        return await self.repo.count_unresolved_by_shipper(shipper_id)

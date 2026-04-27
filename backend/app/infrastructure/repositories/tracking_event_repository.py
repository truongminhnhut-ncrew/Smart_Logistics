"""
infrastructure/repositories/tracking_event_repository.py — Tracking events (append-only).

⚠️ CRITICAL: tracking_events collection is APPEND-ONLY.
NEVER update() or delete() records from this collection.
Only insert new events.
"""

from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain import TrackingEvent
from .base_repository import BaseRepository


class TrackingEventRepository(BaseRepository):
    """
    Repository for TrackingEvent data access.

    🚨 APPEND-ONLY COLLECTION — NEVER UPDATE/DELETE
    Each GPS point generates exactly 1 event.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.tracking_events, TrackingEvent)

    async def append_event(self, event: dict) -> str:
        """
        Append (insert) new tracking event.

        This is the ONLY write operation allowed on this collection.
        """
        result = await self.collection.insert_one(event)
        return str(result.inserted_id)

    async def find_by_id(self, event_id: str) -> Optional[dict]:
        """Find event by event_id."""
        return await self.find_one({"event_id": event_id})

    async def find_by_shipper(self, shipper_id: str, limit: int = 100) -> List[dict]:
        """Get last N events for shipper (ordered by timestamp DESC)."""
        cursor = self.collection.find(
            {"shipper_id": shipper_id}, projection={"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def find_by_order(self, order_id: str, limit: int = 50) -> List[dict]:
        """Get events for specific order."""
        cursor = self.collection.find(
            {"order_id": order_id}, projection={"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def find_shipper_last_location(self, shipper_id: str) -> Optional[dict]:
        """
        Get the MOST RECENT location event for shipper.
        Used in stream processor to compute speed/heading.
        """
        cursor = self.collection.find(
            {
                "shipper_id": shipper_id,
                "event_type": "LOCATION_UPDATE",
            },
            projection={"_id": 0},
        ).sort("timestamp", -1).limit(1)
        results = await cursor.to_list(length=1)
        return results[0] if results else None

    async def find_in_time_range(
        self,
        shipper_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[dict]:
        """Get events for shipper within time range."""
        return await self.find_many({
            "shipper_id": shipper_id,
            "timestamp": {
                "$gte": start_time,
                "$lte": end_time,
            }
        })

    async def find_recent_events(self, minutes: int = 5, limit: int = 1000) -> List[dict]:
        """Get all events from last N minutes (for dashboard)."""
        cutoff = datetime.utcnow()
        cutoff = cutoff.replace(second=0, microsecond=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(minutes=minutes)

        cursor = self.collection.find({
            "timestamp": {"$gte": cutoff}
        }, projection={"_id": 0}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def count_by_shipper(self, shipper_id: str) -> int:
        """Count total events for shipper."""
        return await self.count({"shipper_id": shipper_id})

    async def get_delivery_history(self, shipper_id: str) -> List[dict]:
        """Get all DELIVERY_COMPLETE events for shipper."""
        return await self.find_many(
            {
                "shipper_id": shipper_id,
                "event_type": "DELIVERY_COMPLETE",
            },
            limit=100,
        )

    async def find_alerts(self, alert_type: str) -> List[dict]:
        """Get all alert events of specific type."""
        return await self.find_many(
            {"exception_code": alert_type},
            limit=100,
        )

    async def get_shipper_timeline(self, shipper_id: str, limit: int = 50) -> List[dict]:
        """
        Get chronological timeline of shipper events.
        Returns events ordered by timestamp ASC (oldest first).
        """
        cursor = self.collection.find(
            {"shipper_id": shipper_id}, projection={"_id": 0}
        ).sort("timestamp", 1).limit(limit)
        return await cursor.to_list(length=limit)

    async def setup_ttl_index(self) -> None:
        """
        Create TTL index on tracking_events.
        Records expire automatically after 7 days.

        Run once during initialization.
        """
        await self.collection.create_index(
            "timestamp",
            expireAfterSeconds=7 * 24 * 60 * 60,  # 7 days
        )

    async def get_collection_stats(self) -> dict:
        """Get collection statistics."""
        total_count = await self.count()

        # Count by event type
        location_count = await self.count({"event_type": "LOCATION_UPDATE"})
        alert_count = await self.count({"event_type": "STATUS_CHANGE"})

        # Count with exceptions
        exception_count = await self.count({"exception_code": {"$ne": None}})

        return {
            "total_events": total_count,
            "location_updates": location_count,
            "status_changes": alert_count,
            "alerts_triggered": exception_count,
        }

"""
infrastructure/repositories/order_repository.py — Order data access.
"""

from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain import Order
from .base_repository import BaseRepository


class OrderRepository(BaseRepository):
    """Repository for Order data access."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.orders, Order)

    async def find_by_id(self, order_id: str) -> Optional[dict]:
        """Find order by order_id (PK)."""
        return await self.find_one({"order_id": order_id})

    async def find_all_orders(self) -> List[dict]:
        """Get all orders."""
        return await self.find_all()

    async def find_pending_orders(self) -> List[dict]:
        """Get all pending orders (not yet assigned)."""
        return await self.find_many({"current_status": "PENDING"})

    async def find_by_shipper(self, shipper_id: str) -> List[dict]:
        """Get all orders assigned to a shipper."""
        return await self.find_many({
            "assigned_shipper_id": shipper_id,
            "current_status": {"$in": ["IN_TRANSIT", "PICKED_UP"]},
        })

    async def find_active_order(self, shipper_id: str) -> Optional[dict]:
        """
        Get currently active (IN_TRANSIT or PICKED_UP) order for shipper.
        Used during GPS stream processing.
        """
        return await self.find_one({
            "assigned_shipper_id": shipper_id,
            "current_status": {"$in": ["IN_TRANSIT", "PICKED_UP"]},
        })

    async def find_by_status(self, status: str) -> List[dict]:
        """Find all orders with given status."""
        return await self.find_many({"current_status": status})

    async def create_order(
        self,
        order_id: str,
        warehouse_id: str,
        dest_lat: float,
        dest_lon: float,
        destination_text: str,
        priority: str = "MEDIUM",
        promised_delivery_at: Optional[datetime] = None,
    ) -> str:
        """Create new order."""
        now = datetime.utcnow()
        order_doc = {
            "order_id": order_id,
            "warehouse_id": warehouse_id,
            "assigned_shipper_id": None,
            "dest_lat": dest_lat,
            "dest_lon": dest_lon,
            "destination_text": destination_text,
            "current_status": "PENDING",
            "eta_minutes": None,
            "priority": priority,
            "promised_delivery_at": promised_delivery_at,
            "created_at": now,
            "updated_at": now,
        }
        return await self.create(order_doc)

    async def assign_shipper(self, order_id: str, shipper_id: str) -> None:
        """Assign order to shipper."""
        await self.update_one(
            {"order_id": order_id},
            {
                "assigned_shipper_id": shipper_id,
                "current_status": "PICKED_UP",
                "updated_at": datetime.utcnow(),
            },
        )

    async def update_eta(self, order_id: str, eta_minutes: int) -> None:
        """
        Update ETA for order.
        🔴 Called on every GPS update (~1 sec).
        """
        await self.update_one(
            {"order_id": order_id},
            {
                "eta_minutes": eta_minutes,
                "updated_at": datetime.utcnow(),
            },
        )

    async def update_status(self, order_id: str, status: str) -> None:
        """Update order status."""
        update_data = {
            "current_status": status,
            "updated_at": datetime.utcnow(),
        }
        if status == "DELIVERED":
            update_data["completed_at"] = datetime.utcnow()
        elif status == "PICKED_UP":
            update_data["picked_up_at"] = datetime.utcnow()

        await self.update_one({"order_id": order_id}, update_data)

    async def mark_delivered(self, order_id: str) -> None:
        """Mark order as DELIVERED."""
        await self.update_status(order_id, "DELIVERED")

    async def mark_failed(self, order_id: str) -> None:
        """Mark order as FAILED."""
        await self.update_status(order_id, "FAILED")

    async def get_orders_by_warehouse(self, warehouse_id: str) -> List[dict]:
        """Get all orders from given warehouse."""
        return await self.find_many({"warehouse_id": warehouse_id})

    async def get_overdue_orders(self, current_time: datetime) -> List[dict]:
        """Get orders past promised delivery time."""
        return await self.find_many({
            "promised_delivery_at": {"$lt": current_time},
            "current_status": {"$ne": "DELIVERED"},
        })

    async def get_high_priority_pending(self) -> List[dict]:
        """Get pending high-priority orders."""
        return await self.find_many({
            "current_status": "PENDING",
            "priority": "HIGH",
        })

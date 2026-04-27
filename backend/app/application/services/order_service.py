"""
application/services/order_service.py — Order management service.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain import Order, OrderStatus
from app.infrastructure.repositories import OrderRepository, ShipperRepository

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order management operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.shipper_repo = ShipperRepository(db)

    async def create_order(
        self,
        warehouse_id: str,
        dest_lat: float,
        dest_lon: float,
        destination_text: str,
        priority: str = "MEDIUM",
        promised_delivery_minutes: Optional[int] = None,
    ) -> str:
        """Create new delivery order."""
        order_id = self._generate_order_id()

        promised_at = None
        if promised_delivery_minutes:
            promised_at = datetime.now(timezone.utc) + timedelta(minutes=promised_delivery_minutes)

        return await self.order_repo.create_order(
            order_id=order_id,
            warehouse_id=warehouse_id,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            destination_text=destination_text,
            priority=priority,
            promised_delivery_at=promised_at,
        )

    async def assign_shipper(self, order_id: str, shipper_id: str) -> bool:
        """Assign order to shipper."""
        order = await self.order_repo.find_by_id(order_id)
        if not order:
            logger.warning(f"[Order] Not found: {order_id}")
            return False

        shipper = await self.shipper_repo.find_by_id(shipper_id)
        if not shipper:
            logger.warning(f"[Shipper] Not found: {shipper_id}")
            return False

        await self.order_repo.assign_shipper(order_id, shipper_id)
        await self.shipper_repo.update_status(shipper_id, "ASSIGNED")

        logger.info(f"[Order] Assigned {order_id} to {shipper_id}")
        return True

    async def complete_order(self, order_id: str) -> bool:
        """Mark order as delivered."""
        order = await self.order_repo.find_by_id(order_id)
        if not order:
            return False

        await self.order_repo.mark_delivered(order_id)

        # Update shipper stats
        if order.get("assigned_shipper_id"):
            from app.utils import haversine_km
            # Calculate distance from warehouse to destination
            warehouse = await self.db.warehouses.find_one({"warehouse_id": order["warehouse_id"]})
            if warehouse:
                distance = haversine_km(
                    warehouse["lat"], warehouse["lon"],
                    order["dest_lat"], order["dest_lon"],
                )
                await self.shipper_repo.increment_completed_orders(order["assigned_shipper_id"], distance)

        logger.info(f"[Order] Completed: {order_id}")
        return True

    async def get_pending_orders(self) -> List[dict]:
        """Get all pending orders waiting for assignment."""
        return await self.order_repo.find_pending_orders()

    async def get_high_priority_orders(self) -> List[dict]:
        """Get high-priority pending orders."""
        return await self.order_repo.get_high_priority_pending()

    async def get_shipper_orders(self, shipper_id: str) -> List[dict]:
        """Get all active orders for a shipper."""
        return await self.order_repo.find_by_shipper(shipper_id)

    async def get_overdue_orders(self) -> List[dict]:
        """Get orders past SLA deadline."""
        return await self.order_repo.get_overdue_orders(datetime.now(timezone.utc))

    def _generate_order_id(self) -> str:
        """Generate unique order ID: ORD-YYYYMMDD-XXXX"""
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        import random
        seq = random.randint(1000, 9999)
        return f"ORD-{date_str}-{seq:04d}"

"""
presentation/api/routers/orders.py — Order endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from pydantic import BaseModel

from app.db import get_db
from app.application.services import OrderService
from app.infrastructure.repositories import OrderRepository

router = APIRouter(prefix="/orders", tags=["orders"])


class CreateOrderRequest(BaseModel):
    """Request to create new order."""
    warehouse_id: str
    dest_lat: float
    dest_lon: float
    destination_text: str
    priority: str = "MEDIUM"
    promised_delivery_minutes: int = None


class AssignOrderRequest(BaseModel):
    """Request to assign order to shipper."""
    shipper_id: str


class CompleteOrderRequest(BaseModel):
    """Request to mark order as completed."""
    completed: bool = True


@router.get("", response_model=List[dict])
async def list_orders(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get all orders with current status and ETA."""
    repo = OrderRepository(db)
    orders = await repo.find_all_orders()
    return orders


@router.get("/pending", response_model=List[dict])
async def get_pending_orders(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get pending orders waiting for shipper assignment."""
    repo = OrderRepository(db)
    orders = await repo.find_pending_orders()
    return orders


@router.post("", status_code=201)
async def create_order(
    req: CreateOrderRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create new delivery order."""
    service = OrderService(db)
    order_id = await service.create_order(
        warehouse_id=req.warehouse_id,
        dest_lat=req.dest_lat,
        dest_lon=req.dest_lon,
        destination_text=req.destination_text,
        priority=req.priority,
        promised_delivery_minutes=req.promised_delivery_minutes,
    )
    return {
        "order_id": order_id,
        "status": "created",
    }


@router.get("/{order_id}", response_model=dict)
async def get_order(order_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get order details by ID."""
    repo = OrderRepository(db)
    order = await repo.find_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/assign")
async def assign_shipper(
    order_id: str,
    req: AssignOrderRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Assign order to shipper."""
    service = OrderService(db)
    success = await service.assign_shipper(order_id, req.shipper_id)
    if not success:
        raise HTTPException(status_code=400, detail="Assignment failed")
    return {"status": "assigned", "order_id": order_id, "shipper_id": req.shipper_id}


@router.patch("/{order_id}/complete")
async def complete_order(
    order_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Mark order as delivered."""
    service = OrderService(db)
    success = await service.complete_order(order_id)
    if not success:
        raise HTTPException(status_code=400, detail="Completion failed")
    return {"status": "completed", "order_id": order_id}

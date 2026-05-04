"""
domain/entities.py — Domain models for ShipTrack system.

Pydantic models representing core business entities:
- Shipper: 30 virtual shippers on real-time tracking
- Order: Delivery orders
- TrackingEvent: GPS stream events (append-only)
- Incident: Exception events during delivery
- Warehouse: Pickup/delivery points
"""

from datetime import datetime, timezone
from typing import Optional, Literal, List
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# ── ENUMS ──────────────────────────────────────────────
class ShipperStatus(str, Enum):
    """Shipper operational status — 9 trạng thái theo TONGQUAN.md."""
    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    AVAILABLE = "AVAILABLE"
    HEADING_TO_WAREHOUSE = "HEADING_TO_WAREHOUSE"
    AT_WAREHOUSE = "AT_WAREHOUSE"
    OFFLINE = "OFFLINE"
    VEHICLE_BREAKDOWN = "VEHICLE_BREAKDOWN"
    LOST_CONNECTION = "LOST_CONNECTION"
    DELAYED = "DELAYED"


class IncidentSeverity(str, Enum):
    """Severity levels for incidents."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SignalStatus(str, Enum):
    """GPS signal status."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class OrderStatus(str, Enum):
    """Order delivery status."""
    PENDING = "PENDING"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    DELIVERY_FAILED_ATTEMPT_1 = "DELIVERY_FAILED_ATTEMPT_1"  # Lần 1 khách vắng
    DELIVERY_FAILED_ATTEMPT_2 = "DELIVERY_FAILED_ATTEMPT_2"  # Lần 2 khách vắng
    FAILED = "FAILED"  # Hoàn toàn không giao được


class EventType(str, Enum):
    """Tracking event types."""
    LOCATION_UPDATE = "LOCATION_UPDATE"
    STATUS_CHANGE = "STATUS_CHANGE"
    DELIVERY_COMPLETE = "DELIVERY_COMPLETE"


class IncidentType(str, Enum):
    """Incident / exception types — 5 loại theo TONGQUAN.md."""
    TRAFFIC_JAM = "TRAFFIC_JAM"              # 🚗 Kẹt xe
    HEAVY_RAIN = "HEAVY_RAIN"                # 🌧️ Mưa lớn
    CUSTOMER_ABSENT = "CUSTOMER_ABSENT"      # 👤 Khách vắng
    VEHICLE_BREAKDOWN = "VEHICLE_BREAKDOWN"  # 🔧 Hư xe
    LOST_CONNECTION = "LOST_CONNECTION"      # 🔋 Mất kết nối
    # Legacy types for backward compatibility
    GPS_LOST = "GPS_LOST"
    SHIPPER_LATE = "SHIPPER_LATE"
    CUSTOMER_NOT_AVAILABLE = "CUSTOMER_NOT_AVAILABLE"
    DELIVERY_REFUSED = "DELIVERY_REFUSED"
    ACCIDENT = "ACCIDENT"
    CUSTOMER_REFUSED = "CUSTOMER_REFUSED"


class SimulationPhase(str, Enum):
    """Overall simulation state machine."""
    IDLE = "IDLE"
    STARTED = "STARTED"
    DISPATCHING = "DISPATCHING"     # top 3 heading to warehouse
    WAITING_FOR_ORDER = "WAITING_FOR_ORDER"  # shipper arrived, waiting for order input
    DELIVERING = "DELIVERING"       # shipper en route to customer
    COMPLETED = "COMPLETED"


# ── DOMAIN ENTITIES ────────────────────────────────────

class Shipper(BaseModel):
    """
    Shipper domain entity.

    Represents a virtual shipper with real-time GPS tracking.
    🔴 Live GPS updated every 1 second.
    """
    shipper_id: str = Field(..., description="Unique shipper ID: SHP-001")
    name: str = Field(..., description="Shipper name")
    phone_number: str = Field(..., description="Contact phone")
    vehicle_type: str = Field(default="motorcycle", description="Vehicle type")
    vehicle_plate: str = Field(..., description="License plate")

    # 🔴 LIVE GPS STATE
    current_lat: float = Field(..., description="Current latitude")
    current_lon: float = Field(..., description="Current longitude")
    current_speed_kmh: float = Field(default=0.0)
    heading: float = Field(default=0.0)

    # STATUS
    current_status: ShipperStatus = Field(default=ShipperStatus.IDLE)
    signal_status: SignalStatus = Field(default=SignalStatus.ONLINE)

    # METRICS
    completed_count: int = Field(default=0)
    total_distance_km: float = Field(default=0.0)

    # TIMESTAMPS
    last_ping_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Order(BaseModel):
    """Order domain entity."""
    order_id: str = Field(...)
    warehouse_id: str = Field(...)
    assigned_shipper_id: Optional[str] = None

    # DESTINATION
    dest_lat: float = Field(...)
    dest_lon: float = Field(...)
    destination_text: str = Field(...)

    # 🔴 LIVE STATUS
    current_status: OrderStatus = Field(default=OrderStatus.PENDING)
    eta_minutes: Optional[int] = None

    # SLA
    promised_delivery_at: Optional[datetime] = None
    priority: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"

    # TRACKING
    items_count: int = Field(default=1)
    weight_kg: Optional[float] = None
    note: Optional[str] = None

    # TIMESTAMPS
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    picked_up_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Incident(BaseModel):
    """
    Incident / exception event during delivery — 8 fields theo TONGQUAN.md.

    Created manually by dispatcher or auto-detected by system.
    Broadcast immediately to all WebSocket clients.
    """
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    shipper_id: str = Field(...)
    order_id: Optional[str] = None
    incident_type: IncidentType = Field(...)
    severity: str = Field(default="MEDIUM")  # LOW | MEDIUM | HIGH
    location: Optional[dict] = None  # { lat, lon }
    description: str = Field(default="")
    estimated_delay: int = Field(default=0)  # minutes
    recommended_action: str = Field(default="")
    status: str = Field(default="ACTIVE")  # ACTIVE | RESOLVED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None


class TrackingEvent(BaseModel):
    """
    Tracking event domain entity.

    🚨 APPEND-ONLY.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    shipper_id: str = Field(...)
    lat: float = Field(...)
    lon: float = Field(...)
    smooth_lat: float = Field(...)
    smooth_lon: float = Field(...)

    speed_kmh: float = Field(default=0.0)
    heading: float = Field(default=0.0)
    distance_moved_km: float = Field(default=0.0)

    order_id: Optional[str] = None
    eta_minutes: Optional[int] = None
    delay_minutes: int = Field(default=0)

    event_type: EventType = Field(default=EventType.LOCATION_UPDATE)
    status_code: Optional[str] = None
    exception_code: Optional[str] = None
    note: Optional[str] = None


class Warehouse(BaseModel):
    """Warehouse domain entity."""
    warehouse_id: str = Field(...)
    name: str = Field(...)
    lat: float = Field(...)
    lon: float = Field(...)
    address: str = Field(...)
    phone_number: str = Field(...)
    active_orders: int = Field(default=0)
    max_orders_pending: int = Field(default=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── REQUEST/RESPONSE SCHEMAS ────────────────────────

class CreateOrderRequest(BaseModel):
    """Request to create new order."""
    warehouse_id: str
    dest_lat: float
    dest_lon: float
    destination_text: str
    priority: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    promised_delivery_minutes: Optional[int] = None
    note: Optional[str] = None


class CreateIncidentRequest(BaseModel):
    """Request to create incident — theo TONGQUAN.md mục 19.3."""
    shipper_id: str
    order_id: Optional[str] = None
    incident_type: IncidentType
    severity: str = "MEDIUM"  # AUTO theo loại sự cố
    description: str = ""
    estimated_delay: int = 0  # phút, LSTM tự điền
    recommended_action: str = ""


class GPSStreamPayload(BaseModel):
    """Incoming GPS data from simulator or field."""
    shipper_id: str
    lat: float
    lon: float
    timestamp: Optional[datetime] = None


class RealtimeGPSUpdate(BaseModel):
    """WebSocket broadcast payload to frontend."""
    type: str = "gps_update"
    event_id: str
    shipper_id: str
    lat: float
    lon: float
    speed_kmh: float
    heading: float
    status: str
    eta_minutes: Optional[int]
    order_id: Optional[str]
    order_status: Optional[str]
    delay_minutes: int
    timestamp: str


class AlertPayload(BaseModel):
    """Alert broadcast to frontend."""
    type: Literal["ALERT"]
    alert_type: str
    shipper_id: str
    order_id: Optional[str]
    message: str

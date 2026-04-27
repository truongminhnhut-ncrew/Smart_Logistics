"""
domain/entities.py — Domain models for ShipTrack system.

Pydantic models representing core business entities:
- Shipper: 100 virtual shippers on real-time tracking
- Order: Delivery orders
- TrackingEvent: GPS stream events (append-only)
- Warehouse: Pickup/delivery points
"""

from datetime import datetime, timezone
from typing import Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# ── ENUMS ──────────────────────────────────────────────
class ShipperStatus(str, Enum):
    """Shipper operational status."""
    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    DELIVERING = "DELIVERING"
    AVAILABLE = "AVAILABLE"


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
    FAILED = "FAILED"


class EventType(str, Enum):
    """Tracking event types."""
    LOCATION_UPDATE = "LOCATION_UPDATE"
    STATUS_CHANGE = "STATUS_CHANGE"
    DELIVERY_COMPLETE = "DELIVERY_COMPLETE"


class IncidentType(str, Enum):
    """Incident/exception types."""
    GPS_LOST = "GPS_LOST"
    SHIPPER_LATE = "SHIPPER_LATE"
    CUSTOMER_NOT_AVAILABLE = "CUSTOMER_NOT_AVAILABLE"
    DELIVERY_REFUSED = "DELIVERY_REFUSED"
    ACCIDENT = "ACCIDENT"
    CUSTOMER_REFUSED = "CUSTOMER_REFUSED"


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# ── DOMAIN ENTITIES ────────────────────────────────────

class Shipper(BaseModel):
    """
    Shipper domain entity.

    Represents a 100 virtual shipper with real-time GPS tracking.
    🔴 Live GPS updated every 1 second.
    """
    shipper_id: str = Field(..., description="Unique shipper ID: SHP-001")
    name: str = Field(..., description="Shipper name")
    phone_number: str = Field(..., description="Contact phone")
    vehicle_type: str = Field(default="motorcycle", description="Vehicle type: motorcycle, car")
    vehicle_plate: str = Field(..., description="License plate")

    # 🔴 LIVE GPS STATE
    current_lat: float = Field(..., description="Current latitude")
    current_lon: float = Field(..., description="Current longitude")
    current_speed_kmh: float = Field(default=0.0, description="Current speed in km/h")
    heading: float = Field(default=0.0, description="Direction in degrees (0-360)")

    # STATUS
    current_status: ShipperStatus = Field(default=ShipperStatus.IDLE)
    signal_status: SignalStatus = Field(default=SignalStatus.ONLINE)

    # METRICS
    completed_count: int = Field(default=0, description="Orders completed")
    total_distance_km: float = Field(default=0.0, description="Cumulative distance")

    # TIMESTAMPS
    last_ping_at: Optional[datetime] = Field(default=None, description="Last GPS timestamp")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_schema_extra = {
            "example": {
                "shipper_id": "SHP-001",
                "name": "Nguyễn Văn A",
                "phone_number": "0901234567",
                "vehicle_plate": "51C1-12345",
                "current_lat": 10.77695,
                "current_lon": 106.70095,
                "current_speed_kmh": 32.5,
                "heading": 45.0,
                "current_status": "DELIVERING",
                "signal_status": "ONLINE",
            }
        }


class Order(BaseModel):
    """
    Order domain entity.

    Represents a delivery order assigned to a shipper.
    🔴 ETA recalculated every ~5 seconds.
    """
    order_id: str = Field(..., description="Unique order ID: ORD-20250101-001")
    warehouse_id: str = Field(..., description="Origin warehouse")
    assigned_shipper_id: Optional[str] = Field(default=None)

    # DESTINATION
    dest_lat: float = Field(..., description="Destination latitude")
    dest_lon: float = Field(..., description="Destination longitude")
    destination_text: str = Field(..., description="Human-readable address")

    # 🔴 LIVE STATUS
    current_status: OrderStatus = Field(default=OrderStatus.PENDING)
    eta_minutes: Optional[int] = Field(default=None, description="Live ETA in minutes")

    # SLA
    promised_delivery_at: Optional[datetime] = Field(default=None)
    priority: Literal["LOW", "MEDIUM", "HIGH"] = Field(default="MEDIUM")

    # TRACKING
    items_count: int = Field(default=1, description="Number of items")
    weight_kg: Optional[float] = Field(default=None)

    # TIMESTAMPS
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    picked_up_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "ORD-20250101-001",
                "warehouse_id": "WH-HCMC",
                "assigned_shipper_id": "SHP-001",
                "dest_lat": 10.8109,
                "dest_lon": 106.6566,
                "destination_text": "123 Nguyen Hue Blvd, HCM",
                "current_status": "IN_TRANSIT",
                "eta_minutes": 15,
                "priority": "HIGH",
            }
        }


class TrackingEvent(BaseModel):
    """
    Tracking event domain entity.

    🚨 APPEND-ONLY: NEVER update or delete records.
    Each GPS point generates exactly ONE event.
    Automatic TTL pruning after 7 days.

    Represents the 9-step processing result of a single GPS update.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # GPS DATA
    shipper_id: str = Field(..., description="SHP-XXX")
    lat: float = Field(..., description="Raw latitude")
    lon: float = Field(..., description="Raw longitude")

    # SMOOTHING
    smooth_lat: float = Field(..., description="Interpolated latitude")
    smooth_lon: float = Field(..., description="Interpolated longitude")

    # COMPUTED METRICS
    speed_kmh: float = Field(default=0.0)
    heading: float = Field(default=0.0)
    distance_moved_km: float = Field(default=0.0)

    # ORDER CONTEXT
    order_id: Optional[str] = Field(default=None)
    eta_minutes: Optional[int] = Field(default=None)
    delay_minutes: int = Field(default=0, description="Minutes behind SLA")

    # EVENT TYPE
    event_type: EventType = Field(default=EventType.LOCATION_UPDATE)
    status_code: Optional[str] = Field(default=None)

    # ALERTS/EXCEPTIONS
    exception_code: Optional[str] = Field(default=None, description="Alert code if triggered")
    note: Optional[str] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-01-01T12:00:00Z",
                "shipper_id": "SHP-001",
                "lat": 10.77695,
                "lon": 106.70095,
                "smooth_lat": 10.77700,
                "smooth_lon": 106.70100,
                "speed_kmh": 32.5,
                "heading": 45.0,
                "distance_moved_km": 0.082,
                "order_id": "ORD-20250101-001",
                "eta_minutes": 15,
                "delay_minutes": 0,
                "event_type": "LOCATION_UPDATE",
            }
        }


class Warehouse(BaseModel):
    """
    Warehouse domain entity.

    Represents pickup/delivery points.
    """
    warehouse_id: str = Field(..., description="WH-HCMC, WH-HN, etc.")
    name: str = Field(...)
    lat: float = Field(...)
    lon: float = Field(...)
    address: str = Field(...)
    phone_number: str = Field(...)

    # CAPACITY
    active_orders: int = Field(default=0)
    max_orders_pending: int = Field(default=100)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_schema_extra = {
            "example": {
                "warehouse_id": "WH-HCMC",
                "name": "HCMC Central Warehouse",
                "lat": 10.776930,
                "lon": 106.700981,
                "address": "123 Landmark 81, HCM",
                "phone_number": "0283827899",
            }
        }


# ── REQUEST/RESPONSE SCHEMAS ────────────────────────

class CreateOrderRequest(BaseModel):
    """Request to create new order."""
    warehouse_id: str
    dest_lat: float
    dest_lon: float
    destination_text: str
    priority: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    promised_delivery_minutes: Optional[int] = None


class GPSStreamPayload(BaseModel):
    """Incoming GPS data from simulator or field."""
    shipper_id: str
    lat: float
    lon: float
    timestamp: Optional[datetime] = None


class RealtimeGPSUpdate(BaseModel):
    """WebSocket broadcast payload to frontend."""
    event_id: str
    shipper_id: str
    lat: float
    lon: float
    speed_kmh: float
    heading: float
    eta_minutes: Optional[int]
    order_id: Optional[str]
    order_status: Optional[str]
    delay_minutes: int
    timestamp: str  # ISO format


class AlertPayload(BaseModel):
    """Alert broadcast to frontend."""
    type: Literal["ALERT"]
    alert_type: str  # DELIVERY_DELAY, GPS_DROPOUT, IDLE, etc.
    shipper_id: str
    order_id: Optional[str]
    message: str


class Incident(BaseModel):
    """
    Incident/Exception domain entity.

    Tracks special cases like GPS loss, delivery delays, accidents, etc.
    """
    incident_id: str = Field(..., description="Unique ID: INC-YYYYMMDD-XXXX")
    shipper_id: str = Field(..., description="SHP-XXX")
    order_id: Optional[str] = Field(default=None, description="Associated order if applicable")
    incident_type: IncidentType = Field(...)
    severity: IncidentSeverity = Field(default=IncidentSeverity.INFO)
    description: str = Field(..., description="Human-readable incident description")
    resolved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_schema_extra = {
            "example": {
                "incident_id": "INC-20250427-0001",
                "shipper_id": "SHP-001",
                "order_id": "ORD-20250427-001",
                "incident_type": "GPS_LOST",
                "severity": "CRITICAL",
                "description": "Shipper GPS signal lost for 5 minutes",
                "resolved": False,
                "created_at": "2025-04-27T12:30:00Z",
            }
        }


class CreateIncidentRequest(BaseModel):
    """Request to create incident."""
    shipper_id: str
    order_id: Optional[str] = None
    incident_type: IncidentType
    severity: IncidentSeverity = IncidentSeverity.INFO
    description: str

"""
presentation/api/routers/incidents.py — Incident endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.db import get_db
from app.domain import CreateIncidentRequest
from app.application.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=dict)
async def create_incident(
    request: CreateIncidentRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create new incident."""
    service = IncidentService(db)
    incident_id = await service.create_incident(
        shipper_id=request.shipper_id,
        incident_type=request.incident_type,
        severity=request.severity,
        description=request.description,
        order_id=request.order_id,
    )
    return {
        "incident_id": incident_id,
        "status": "created",
    }


@router.get("/{incident_id}", response_model=dict)
async def get_incident(
    incident_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get incident by ID."""
    service = IncidentService(db)
    incident = await service.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("/shipper/{shipper_id}", response_model=List[dict])
async def get_shipper_incidents(
    shipper_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all incidents for a shipper."""
    service = IncidentService(db)
    incidents = await service.get_shipper_incidents(shipper_id, limit=limit)
    return incidents


@router.get("/shipper/{shipper_id}/recent", response_model=List[dict])
async def get_shipper_recent_incidents(
    shipper_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get recent incidents for a shipper (most recent first)."""
    service = IncidentService(db)
    incidents = await service.get_shipper_recent_incidents(shipper_id, limit=limit)
    return incidents


@router.get("", response_model=List[dict])
async def list_unresolved_incidents(
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all unresolved incidents."""
    service = IncidentService(db)
    incidents = await service.get_unresolved_incidents()
    return incidents


@router.patch("/{incident_id}/resolve", response_model=dict)
async def resolve_incident(
    incident_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Mark incident as resolved."""
    service = IncidentService(db)
    incident = await service.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    await service.resolve_incident(incident_id)
    return {
        "incident_id": incident_id,
        "status": "resolved",
    }


@router.get("/stats/unresolved-count", response_model=dict)
async def get_unresolved_count(
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get count of unresolved incidents (for dashboard)."""
    service = IncidentService(db)
    count = await service.get_unresolved_count()
    return {
        "unresolved_count": count,
    }


@router.post("/bulk", response_model=dict)
async def bulk_import_incidents(
    payload: dict,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Bulk import incidents from JSON array.

    Request body:
    {
        "incidents": [
            {
                "shipper_id": "SHP-001",
                "incident_type": "GPS_LOST",
                "severity": "CRITICAL",
                "description": "...",
                "order_id": "ORD-001" (optional)
            },
            ...
        ]
    }
    """
    incidents = payload.get("incidents", [])
    if not incidents:
        raise HTTPException(status_code=400, detail="No incidents provided")

    service = IncidentService(db)
    imported = 0
    errors = []

    for idx, inc in enumerate(incidents):
        try:
            await service.create_incident(
                shipper_id=inc.get("shipper_id"),
                incident_type=inc.get("incident_type"),
                severity=inc.get("severity", "INFO"),
                description=inc.get("description"),
                order_id=inc.get("order_id"),
            )
            imported += 1
        except Exception as e:
            errors.append(f"Record {idx}: {str(e)}")

    return {
        "imported": imported,
        "failed": len(errors),
        "errors": errors,
    }

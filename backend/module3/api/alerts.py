"""
Shortage Alerts API Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.alerts import AlertLevel, AlertType, AlertStatus
from services.shortage_service import ShortageAlertingService
from schemas.alerts import (
    ShortageAlertCreate, ShortageAlertUpdate, ShortageAlertResponse,
    AlertSubscriptionCreate, AlertSubscriptionUpdate, AlertSubscriptionResponse,
    AlertActionCreate, AlertActionUpdate, AlertActionResponse,
    AlertDashboard, PredictedShortage, ShortageRiskAssessment, AlertSummary
)
from schemas.common import PaginatedResponse

router = APIRouter()


# ==================== Alerts ====================

@router.post("/", response_model=ShortageAlertResponse)
async def create_alert(
    data: ShortageAlertCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new shortage alert."""
    service = ShortageAlertingService(db)
    alert = await service.create_alert(data)
    return alert


@router.get("/", response_model=PaginatedResponse[ShortageAlertResponse])
async def list_alerts(
    region_id: Optional[int] = None,
    alert_type: Optional[AlertType] = None,
    alert_level: Optional[AlertLevel] = None,
    status: Optional[AlertStatus] = None,
    is_active: Optional[bool] = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List shortage alerts."""
    service = ShortageAlertingService(db)
    offset = (page - 1) * page_size
    alerts, total = await service.list_alerts(
        region_id=region_id,
        alert_type=alert_type,
        alert_level=alert_level,
        status=status,
        is_active=is_active,
        limit=page_size,
        offset=offset
    )
    return PaginatedResponse(
        items=alerts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/critical", response_model=List[ShortageAlertResponse])
async def get_critical_alerts(
    region_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all critical active alerts."""
    service = ShortageAlertingService(db)
    alerts = await service.get_critical_alerts(region_id=region_id)
    return alerts


@router.get("/dashboard", response_model=AlertDashboard)
async def get_alert_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """Get alert dashboard data."""
    service = ShortageAlertingService(db)
    dashboard = await service.get_dashboard()
    return dashboard


@router.get("/{alert_id}", response_model=ShortageAlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific alert."""
    service = ShortageAlertingService(db)
    alert = await service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}", response_model=ShortageAlertResponse)
async def update_alert(
    alert_id: int,
    data: ShortageAlertUpdate,
    changed_by: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update an alert."""
    service = ShortageAlertingService(db)
    alert = await service.update_alert(alert_id, data, changed_by)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=ShortageAlertResponse)
async def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str,
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge an alert."""
    service = ShortageAlertingService(db)
    alert = await service.acknowledge_alert(alert_id, acknowledged_by)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/escalate", response_model=ShortageAlertResponse)
async def escalate_alert(
    alert_id: int,
    escalate_to: List[str],
    escalated_by: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Escalate an alert."""
    service = ShortageAlertingService(db)
    alert = await service.escalate_alert(alert_id, escalate_to, escalated_by, reason)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/resolve", response_model=ShortageAlertResponse)
async def resolve_alert(
    alert_id: int,
    resolved_by: str,
    resolution_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Resolve an alert."""
    service = ShortageAlertingService(db)
    alert = await service.resolve_alert(alert_id, resolved_by, resolution_notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/{alert_id}/history")
async def get_alert_history(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get alert history."""
    service = ShortageAlertingService(db)
    history = await service.get_alert_history(alert_id)
    return history


# ==================== Predictions ====================

@router.get("/predictions/shortages", response_model=List[PredictedShortage])
async def detect_shortages(
    region_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Detect potential shortages across regions."""
    service = ShortageAlertingService(db)
    predictions = await service.detect_shortages(region_id=region_id)
    return predictions


@router.post("/predictions/auto-generate", response_model=List[ShortageAlertResponse])
async def auto_generate_alerts(
    db: AsyncSession = Depends(get_db)
):
    """Automatically generate alerts based on shortage predictions."""
    service = ShortageAlertingService(db)
    alerts = await service.auto_generate_alerts()
    return alerts


@router.get("/predictions/risk-assessment/{region_id}", response_model=ShortageRiskAssessment)
async def get_risk_assessment(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive shortage risk assessment for a region."""
    service = ShortageAlertingService(db)
    assessment = await service.get_risk_assessment(region_id)
    return assessment


# ==================== Subscriptions ====================

@router.post("/subscriptions", response_model=AlertSubscriptionResponse)
async def create_subscription(
    data: AlertSubscriptionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create an alert subscription."""
    service = ShortageAlertingService(db)
    subscription = await service.create_subscription(data)
    return subscription


@router.get("/subscriptions", response_model=List[AlertSubscriptionResponse])
async def list_subscriptions(
    is_active: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List alert subscriptions."""
    service = ShortageAlertingService(db)
    subscriptions = await service.list_subscriptions(is_active=is_active)
    return subscriptions

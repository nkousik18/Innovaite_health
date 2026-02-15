"""
Shortage alerting schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .common import BaseSchema, TimestampMixin


class AlertLevel(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    IMMINENT = "imminent"
    CRITICAL = "critical"


class AlertType(str, Enum):
    SHORTAGE = "shortage"
    PRODUCTION = "production"
    DISTRIBUTION = "distribution"
    PRICE = "price"
    QUALITY = "quality"
    IMPORT = "import"
    WEATHER = "weather"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESPONDING = "responding"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    FALSE_ALARM = "false_alarm"


# Shortage Alert Schemas
class ShortageAlertBase(BaseModel):
    region_id: int
    alert_type: AlertType
    alert_level: AlertLevel
    title: str = Field(..., max_length=255)


class ShortageAlertCreate(ShortageAlertBase):
    category_id: Optional[int] = None
    description: Optional[str] = None
    food_items_affected: Optional[List[str]] = None
    predicted_shortage_date: Optional[datetime] = None
    days_until_shortage: Optional[int] = None
    current_inventory_tonnes: Optional[float] = None
    current_days_supply: Optional[float] = None
    consumption_rate_tonnes_day: Optional[float] = None
    population_affected: Optional[int] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    model_name: Optional[str] = None
    recommended_actions: Optional[List[Dict[str, Any]]] = None


class ShortageAlertUpdate(BaseModel):
    alert_level: Optional[AlertLevel] = None
    status: Optional[AlertStatus] = None
    description: Optional[str] = None
    predicted_shortage_date: Optional[datetime] = None
    recommended_actions: Optional[List[Dict[str, Any]]] = None
    response_status: Optional[str] = None
    response_lead: Optional[str] = None
    is_active: Optional[bool] = None


class ShortageAlertResponse(ShortageAlertBase, TimestampMixin, BaseSchema):
    id: int
    alert_code: str
    category_id: Optional[int] = None
    status: AlertStatus = AlertStatus.ACTIVE
    description: Optional[str] = None
    food_items_affected: Optional[List[str]] = None
    predicted_shortage_date: Optional[datetime] = None
    days_until_shortage: Optional[int] = None
    current_inventory_tonnes: Optional[float] = None
    current_days_supply: Optional[float] = None
    population_affected: Optional[int] = None
    confidence_score: Optional[float] = None
    recommended_actions: Optional[List[Dict[str, Any]]] = None
    is_active: bool = True


class AlertSummary(BaseSchema):
    id: int
    alert_code: str
    region_id: int
    region_name: str
    alert_type: AlertType
    alert_level: AlertLevel
    status: AlertStatus
    title: str
    days_until_shortage: Optional[int] = None
    created_at: datetime


# Alert History Schemas
class AlertHistoryCreate(BaseModel):
    alert_id: int
    changed_by: Optional[str] = None
    previous_level: Optional[AlertLevel] = None
    new_level: Optional[AlertLevel] = None
    previous_status: Optional[AlertStatus] = None
    new_status: Optional[AlertStatus] = None
    change_reason: Optional[str] = None
    notes: Optional[str] = None


class AlertHistoryResponse(BaseSchema):
    id: int
    alert_id: int
    changed_at: datetime
    changed_by: Optional[str] = None
    previous_level: Optional[AlertLevel] = None
    new_level: Optional[AlertLevel] = None
    previous_status: Optional[AlertStatus] = None
    new_status: Optional[AlertStatus] = None
    change_reason: Optional[str] = None


# Alert Subscription Schemas
class AlertSubscriptionCreate(BaseModel):
    subscriber_name: str = Field(..., max_length=100)
    subscriber_email: Optional[str] = None
    subscriber_phone: Optional[str] = None
    subscriber_organization: Optional[str] = None
    region_ids: Optional[List[int]] = None
    category_ids: Optional[List[int]] = None
    alert_types: Optional[List[AlertType]] = None
    minimum_alert_level: AlertLevel = AlertLevel.WARNING
    notify_email: bool = True
    notify_sms: bool = False
    notify_webhook: bool = False
    webhook_url: Optional[str] = None
    immediate_notifications: bool = True


class AlertSubscriptionUpdate(BaseModel):
    region_ids: Optional[List[int]] = None
    category_ids: Optional[List[int]] = None
    minimum_alert_level: Optional[AlertLevel] = None
    notify_email: Optional[bool] = None
    notify_sms: Optional[bool] = None
    is_active: Optional[bool] = None


class AlertSubscriptionResponse(BaseSchema, TimestampMixin):
    id: int
    subscriber_name: str
    subscriber_email: Optional[str] = None
    subscriber_organization: Optional[str] = None
    region_ids: Optional[List[int]] = None
    minimum_alert_level: AlertLevel
    notify_email: bool
    notify_sms: bool
    is_active: bool = True
    notifications_sent: int = 0


# Alert Action Schemas
class AlertActionCreate(BaseModel):
    alert_id: int
    action_type: str = Field(..., max_length=50)
    action_title: str = Field(..., max_length=255)
    action_description: Optional[str] = None
    priority: Optional[int] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_cost_usd: Optional[float] = None
    resources_needed: Optional[List[Dict[str, Any]]] = None


class AlertActionUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_cost_usd: Optional[float] = None
    outcome: Optional[str] = None


class AlertActionResponse(BaseSchema, TimestampMixin):
    id: int
    alert_id: int
    action_type: str
    action_title: str
    action_description: Optional[str] = None
    priority: Optional[int] = None
    status: str = "recommended"
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Dashboard and Analytics Schemas
class AlertDashboard(BaseSchema):
    total_active_alerts: int
    alerts_by_level: Dict[str, int]
    alerts_by_type: Dict[str, int]
    alerts_by_region: Dict[str, int]
    critical_alerts: List[AlertSummary]
    recent_alerts: List[AlertSummary]
    trend_7_days: Dict[str, int]


class AlertAnalytics(BaseSchema):
    period_start: datetime
    period_end: datetime
    total_alerts: int
    alerts_by_level: Dict[str, int]
    alerts_by_type: Dict[str, int]
    avg_resolution_time_hours: float
    false_alarm_rate: float
    escalation_rate: float
    top_affected_regions: List[Dict[str, Any]]


class PredictedShortage(BaseSchema):
    region_id: int
    region_name: str
    category_id: int
    category_name: str
    current_inventory_tonnes: float
    days_of_supply: float
    predicted_shortage_date: datetime
    confidence_score: float
    risk_factors: List[str]
    recommended_actions: List[str]


class ShortageRiskAssessment(BaseSchema):
    region_id: int
    assessment_date: datetime
    overall_risk: float
    categories_at_risk: List[Dict[str, Any]]
    contributing_factors: List[Dict[str, Any]]
    mitigation_recommendations: List[Dict[str, Any]]
    monitoring_indicators: List[str]

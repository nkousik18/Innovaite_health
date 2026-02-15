"""
Distribution network schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .common import BaseSchema, GeoLocation, TimestampMixin


class CorridorType(str, Enum):
    HIGHWAY = "highway"
    RAIL = "rail"
    WATERWAY = "waterway"
    AIR = "air"
    PIPELINE = "pipeline"


class DisruptionType(str, Enum):
    LOCKDOWN = "lockdown"
    INFRASTRUCTURE = "infrastructure"
    WEATHER = "weather"
    CONFLICT = "conflict"
    FUEL_SHORTAGE = "fuel_shortage"
    BORDER_CLOSURE = "border_closure"
    CIVIL_UNREST = "civil_unrest"
    ACCIDENT = "accident"
    MAINTENANCE = "maintenance"


class DisruptionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Transportation Corridor Schemas
class CorridorBase(BaseModel):
    name: str = Field(..., max_length=255)
    corridor_code: str = Field(..., max_length=50)
    corridor_type: CorridorType


class CorridorCreate(CorridorBase):
    start_region_id: Optional[int] = None
    end_region_id: Optional[int] = None
    length_km: Optional[float] = None
    daily_capacity_tonnes: Optional[float] = None
    cold_chain_capable: bool = False
    path_geometry: Optional[Dict[str, Any]] = None


class CorridorUpdate(BaseModel):
    name: Optional[str] = None
    daily_capacity_tonnes: Optional[float] = None
    current_utilization: Optional[float] = Field(None, ge=0, le=100)
    operational_status: Optional[str] = None
    cold_chain_capable: Optional[bool] = None


class CorridorResponse(CorridorBase, TimestampMixin, BaseSchema):
    id: int
    start_region_id: Optional[int] = None
    end_region_id: Optional[int] = None
    length_km: Optional[float] = None
    daily_capacity_tonnes: Optional[float] = None
    current_utilization: Optional[float] = None
    cold_chain_capable: bool = False
    operational_status: str = "operational"
    is_active: bool = True


# Distribution Center Schemas
class DistributionCenterBase(BaseModel):
    name: str = Field(..., max_length=255)
    center_code: str = Field(..., max_length=50)
    region_id: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class DistributionCenterCreate(DistributionCenterBase):
    address: Optional[str] = None
    total_capacity_tonnes: Optional[float] = None
    cold_storage_capacity_tonnes: Optional[float] = None
    staff_count: Optional[int] = None
    vehicles_available: Optional[int] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class DistributionCenterUpdate(BaseModel):
    name: Optional[str] = None
    current_inventory_tonnes: Optional[float] = None
    cold_storage_current_tonnes: Optional[float] = None
    staff_count: Optional[int] = None
    vehicles_available: Optional[int] = None
    operational_status: Optional[str] = None


class DistributionCenterResponse(DistributionCenterBase, TimestampMixin, BaseSchema):
    id: int
    address: Optional[str] = None
    total_capacity_tonnes: Optional[float] = None
    current_inventory_tonnes: Optional[float] = None
    utilization_percentage: Optional[float] = None
    cold_storage_capacity_tonnes: Optional[float] = None
    staff_count: Optional[int] = None
    vehicles_available: Optional[int] = None
    operational_status: str = "operational"
    is_active: bool = True


class DistributionCenterSummary(BaseSchema):
    id: int
    name: str
    center_code: str
    region_id: int
    utilization_percentage: Optional[float] = None
    operational_status: str


# Transport Route Schemas
class RouteBase(BaseModel):
    name: str = Field(..., max_length=255)
    route_code: str = Field(..., max_length=50)


class RouteCreate(RouteBase):
    corridor_id: Optional[int] = None
    origin_center_id: Optional[int] = None
    destination_center_id: Optional[int] = None
    origin_region_id: Optional[int] = None
    destination_region_id: Optional[int] = None
    distance_km: Optional[float] = None
    estimated_time_hours: Optional[float] = None
    daily_capacity_tonnes: Optional[float] = None
    cold_chain_capable: bool = False
    is_primary_route: bool = False
    path_geometry: Optional[Dict[str, Any]] = None


class RouteUpdate(BaseModel):
    estimated_time_hours: Optional[float] = None
    daily_capacity_tonnes: Optional[float] = None
    operational_status: Optional[str] = None
    current_traffic_level: Optional[str] = None


class RouteResponse(RouteBase, TimestampMixin, BaseSchema):
    id: int
    corridor_id: Optional[int] = None
    origin_region_id: Optional[int] = None
    destination_region_id: Optional[int] = None
    distance_km: Optional[float] = None
    estimated_time_hours: Optional[float] = None
    daily_capacity_tonnes: Optional[float] = None
    cold_chain_capable: bool = False
    operational_status: str = "operational"
    is_primary_route: bool = False
    is_active: bool = True


# Route Disruption Schemas
class DisruptionBase(BaseModel):
    disruption_type: DisruptionType
    severity: DisruptionSeverity
    title: str = Field(..., max_length=255)


class DisruptionCreate(DisruptionBase):
    corridor_id: Optional[int] = None
    route_id: Optional[int] = None
    region_id: Optional[int] = None
    description: Optional[str] = None
    expected_end_at: Optional[datetime] = None
    capacity_reduction_percentage: Optional[float] = Field(None, ge=0, le=100)
    delay_hours: Optional[float] = None
    alternative_routes: Optional[List[int]] = None


class DisruptionUpdate(BaseModel):
    severity: Optional[DisruptionSeverity] = None
    description: Optional[str] = None
    expected_end_at: Optional[datetime] = None
    actual_end_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class DisruptionResponse(DisruptionBase, TimestampMixin, BaseSchema):
    id: int
    corridor_id: Optional[int] = None
    route_id: Optional[int] = None
    region_id: Optional[int] = None
    description: Optional[str] = None
    started_at: datetime
    expected_end_at: Optional[datetime] = None
    actual_end_at: Optional[datetime] = None
    capacity_reduction_percentage: Optional[float] = None
    delay_hours: Optional[float] = None
    is_active: bool = True


class ActiveDisruptionSummary(BaseSchema):
    total_active: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    affected_regions: List[int]
    total_capacity_reduction: float


# Cold Chain Facility Schemas
class ColdChainFacilityCreate(BaseModel):
    name: str = Field(..., max_length=255)
    facility_code: str = Field(..., max_length=50)
    region_id: int
    latitude: float
    longitude: float
    total_capacity_tonnes: Optional[float] = None
    freezer_capacity_tonnes: Optional[float] = None
    chiller_capacity_tonnes: Optional[float] = None
    power_source: Optional[str] = None
    backup_power_hours: Optional[float] = None


class ColdChainFacilityResponse(BaseSchema, TimestampMixin):
    id: int
    name: str
    facility_code: str
    region_id: int
    latitude: float
    longitude: float
    total_capacity_tonnes: Optional[float] = None
    current_inventory_tonnes: Optional[float] = None
    utilization_percentage: Optional[float] = None
    operational_status: str = "operational"
    temperature_alert: bool = False
    is_active: bool = True


# Network Analysis Schemas
class RouteOptimizationRequest(BaseModel):
    origin_region_id: int
    destination_region_id: int
    cargo_tonnes: float
    requires_cold_chain: bool = False
    max_alternatives: int = Field(default=3, ge=1, le=10)
    avoid_disruptions: bool = True


class OptimizedRoute(BaseSchema):
    route_id: int
    route_name: str
    distance_km: float
    estimated_time_hours: float
    estimated_cost: float
    cold_chain_capable: bool
    disruption_risk: float
    waypoints: List[Dict[str, Any]]


class RouteOptimizationResponse(BaseSchema):
    origin: str
    destination: str
    cargo_tonnes: float
    recommended_route: OptimizedRoute
    alternative_routes: List[OptimizedRoute]
    analysis_timestamp: datetime


class NetworkStatusResponse(BaseSchema):
    total_corridors: int
    operational_corridors: int
    total_routes: int
    operational_routes: int
    active_disruptions: int
    network_capacity_utilization: float
    cold_chain_capacity_utilization: float

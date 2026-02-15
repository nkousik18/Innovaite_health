"""
Food distribution planning schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .common import BaseSchema, TimestampMixin, GeoLocation


class PlanStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PopulationType(str, Enum):
    ELDERLY = "elderly"
    CHILDREN = "children"
    PREGNANT = "pregnant"
    IMMUNOCOMPROMISED = "immunocompromised"
    HEALTHCARE_WORKER = "healthcare_worker"
    ESSENTIAL_WORKER = "essential_worker"
    DISABLED = "disabled"
    LOW_INCOME = "low_income"
    GENERAL = "general"


# Distribution Plan Schemas
class DistributionPlanBase(BaseModel):
    plan_name: str = Field(..., max_length=255)
    region_id: int


class DistributionPlanCreate(DistributionPlanBase):
    alert_id: Optional[int] = None
    trigger_reason: Optional[str] = None
    activation_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: Optional[int] = None
    population_covered: Optional[int] = None
    households_covered: Optional[int] = None
    total_food_tonnes: Optional[float] = None
    total_budget_usd: Optional[float] = None
    food_allocation: Optional[Dict[int, float]] = None
    priority_weights: Optional[Dict[str, float]] = None
    distribution_schedule: Optional[Dict[str, Any]] = None


class DistributionPlanUpdate(BaseModel):
    status: Optional[PlanStatus] = None
    activation_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_food_tonnes: Optional[float] = None
    total_budget_usd: Optional[float] = None
    food_allocation: Optional[Dict[int, float]] = None
    completion_pct: Optional[float] = Field(None, ge=0, le=100)
    food_distributed_tonnes: Optional[float] = None
    beneficiaries_served: Optional[int] = None


class DistributionPlanResponse(DistributionPlanBase, TimestampMixin, BaseSchema):
    id: int
    plan_code: str
    alert_id: Optional[int] = None
    status: PlanStatus = PlanStatus.DRAFT
    activation_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: Optional[int] = None
    population_covered: Optional[int] = None
    total_food_tonnes: Optional[float] = None
    total_budget_usd: Optional[float] = None
    distribution_centers_count: Optional[int] = None
    distribution_points_count: Optional[int] = None
    completion_pct: float = 0
    food_distributed_tonnes: float = 0
    beneficiaries_served: int = 0


class PlanSummary(BaseSchema):
    id: int
    plan_code: str
    plan_name: str
    region_id: int
    region_name: str
    status: PlanStatus
    population_covered: int
    completion_pct: float


# Distribution Point Schemas
class DistributionPointBase(BaseModel):
    point_name: str = Field(..., max_length=255)
    region_id: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class DistributionPointCreate(DistributionPointBase):
    plan_id: int
    center_id: Optional[int] = None
    address: Optional[str] = None
    point_type: str = "fixed"
    facility_type: Optional[str] = None
    assigned_population: Optional[int] = None
    assigned_households: Optional[int] = None
    coverage_radius_km: Optional[float] = None
    daily_capacity_beneficiaries: Optional[int] = None
    storage_capacity_tonnes: Optional[float] = None
    operating_hours: Optional[Dict[str, Any]] = None
    coordinator_name: Optional[str] = None
    coordinator_phone: Optional[str] = None


class DistributionPointUpdate(BaseModel):
    operational_status: Optional[str] = None
    current_inventory_tonnes: Optional[float] = None
    staff_count: Optional[int] = None
    total_beneficiaries_served: Optional[int] = None
    total_food_distributed_tonnes: Optional[float] = None
    is_active: Optional[bool] = None


class DistributionPointResponse(DistributionPointBase, TimestampMixin, BaseSchema):
    id: int
    point_code: str
    plan_id: int
    center_id: Optional[int] = None
    point_type: str
    assigned_population: Optional[int] = None
    daily_capacity_beneficiaries: Optional[int] = None
    current_inventory_tonnes: Optional[float] = None
    operational_status: str = "planned"
    total_beneficiaries_served: int = 0
    total_food_distributed_tonnes: float = 0
    is_active: bool = True


# Ration Allocation Schemas
class RationAllocationBase(BaseModel):
    plan_id: int
    population_type: PopulationType


class RationAllocationCreate(RationAllocationBase):
    distribution_point_id: Optional[int] = None
    allocation_date: datetime
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    population_count: Optional[int] = None
    households_count: Optional[int] = None
    ration_composition: Dict[str, float]
    total_ration_kg: float
    calories_per_ration: int
    daily_caloric_target: int = 2000
    cost_per_ration_usd: Optional[float] = None


class RationAllocationUpdate(BaseModel):
    rations_distributed: Optional[int] = None
    food_distributed_tonnes: Optional[float] = None
    status: Optional[str] = None


class RationAllocationResponse(RationAllocationBase, TimestampMixin, BaseSchema):
    id: int
    distribution_point_id: Optional[int] = None
    allocation_date: datetime
    population_count: Optional[int] = None
    ration_composition: Dict[str, float]
    total_ration_kg: float
    calories_per_ration: int
    rations_planned: Optional[int] = None
    rations_distributed: int = 0
    distribution_pct: float = 0
    status: str = "planned"


# Vulnerable Population Schemas
class VulnerablePopulationCreate(BaseModel):
    region_id: int
    population_type: PopulationType
    total_count: int
    households_count: Optional[int] = None
    registered_count: Optional[int] = None
    daily_caloric_need: int = 2000
    special_dietary_needs: Optional[List[str]] = None
    priority_level: int = Field(..., ge=1, le=5)
    mobility_limited_pct: Optional[float] = Field(None, ge=0, le=100)
    requires_home_delivery_pct: Optional[float] = Field(None, ge=0, le=100)


class VulnerablePopulationUpdate(BaseModel):
    total_count: Optional[int] = None
    registered_count: Optional[int] = None
    priority_level: Optional[int] = Field(None, ge=1, le=5)


class VulnerablePopulationResponse(BaseSchema, TimestampMixin):
    id: int
    region_id: int
    population_type: PopulationType
    total_count: int
    households_count: Optional[int] = None
    registered_count: Optional[int] = None
    daily_caloric_need: int
    priority_level: int
    mobility_limited_pct: Optional[float] = None


# Distribution Record Schemas
class DistributionRecordCreate(BaseModel):
    plan_id: int
    distribution_point_id: int
    allocation_id: Optional[int] = None
    beneficiary_id_hash: Optional[str] = None
    household_size: Optional[int] = None
    population_type: Optional[PopulationType] = None
    items_distributed: Dict[str, float]
    total_weight_kg: float


class DistributionRecordResponse(BaseSchema, TimestampMixin):
    id: int
    plan_id: int
    distribution_point_id: int
    distribution_date: datetime
    transaction_code: str
    household_size: Optional[int] = None
    population_type: Optional[PopulationType] = None
    items_distributed: Dict[str, float]
    total_weight_kg: float
    total_calories: Optional[int] = None


# Optimization Schemas
class DistributionOptimizationRequest(BaseModel):
    region_id: int
    population_data: Dict[str, int]
    available_food: Dict[str, float]
    distribution_centers: List[int]
    max_distribution_points: int = 50
    optimization_goal: str = "coverage"


class OptimizedDistributionPoint(BaseSchema):
    location: GeoLocation
    assigned_population: int
    coverage_radius_km: float
    food_allocation: Dict[str, float]
    priority_groups: List[str]


class DistributionOptimizationResponse(BaseSchema):
    region_id: int
    optimization_date: datetime
    recommended_points: List[OptimizedDistributionPoint]
    total_coverage: float
    efficiency_score: float
    estimated_distribution_days: int


# Analytics Schemas
class DistributionAnalytics(BaseSchema):
    plan_id: int
    period_start: datetime
    period_end: datetime
    total_beneficiaries: int
    total_food_distributed_tonnes: float
    by_population_type: Dict[str, Dict[str, Any]]
    by_distribution_point: List[Dict[str, Any]]
    daily_distribution_rate: List[Dict[str, Any]]
    efficiency_metrics: Dict[str, float]


class CoverageAnalysis(BaseSchema):
    region_id: int
    total_population: int
    covered_population: int
    coverage_percentage: float
    coverage_by_type: Dict[str, float]
    underserved_areas: List[Dict[str, Any]]
    recommendations: List[str]

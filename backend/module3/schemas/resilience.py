"""
Agricultural resilience planning schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .common import BaseSchema, TimestampMixin, GeoLocation


class SiteType(str, Enum):
    ROOFTOP_GARDEN = "rooftop_garden"
    VERTICAL_FARM = "vertical_farm"
    COMMUNITY_GARDEN = "community_garden"
    HYDROPONICS = "hydroponics"
    AQUAPONICS = "aquaponics"
    GREENHOUSE = "greenhouse"
    VACANT_LOT = "vacant_lot"
    PERI_URBAN = "peri_urban"


class ProjectStatus(str, Enum):
    PROPOSED = "proposed"
    PLANNING = "planning"
    APPROVED = "approved"
    UNDER_CONSTRUCTION = "under_construction"
    OPERATIONAL = "operational"
    SUSPENDED = "suspended"
    CLOSED = "closed"


# Urban Agriculture Site Schemas
class UrbanAgricultureSiteBase(BaseModel):
    site_name: str = Field(..., max_length=255)
    region_id: int
    site_type: SiteType
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class UrbanAgricultureSiteCreate(UrbanAgricultureSiteBase):
    address: Optional[str] = None
    total_area_sqm: Optional[float] = None
    cultivable_area_sqm: Optional[float] = None
    land_owner: Optional[str] = None
    land_ownership_type: Optional[str] = None
    water_source: Optional[str] = None
    power_source: Optional[str] = None
    has_greenhouse: bool = False
    has_irrigation: bool = False
    crops_grown: Optional[List[str]] = None
    production_capacity_tonnes_year: Optional[float] = None
    setup_cost_usd: Optional[float] = None
    operating_cost_annual_usd: Optional[float] = None
    operator_name: Optional[str] = None


class UrbanAgricultureSiteUpdate(BaseModel):
    status: Optional[ProjectStatus] = None
    current_production_tonnes_year: Optional[float] = None
    crops_grown: Optional[List[str]] = None
    jobs_created: Optional[int] = None
    households_supplied: Optional[int] = None
    is_active: Optional[bool] = None


class UrbanAgricultureSiteResponse(UrbanAgricultureSiteBase, TimestampMixin, BaseSchema):
    id: int
    site_code: str
    address: Optional[str] = None
    total_area_sqm: Optional[float] = None
    cultivable_area_sqm: Optional[float] = None
    crops_grown: Optional[List[str]] = None
    production_capacity_tonnes_year: Optional[float] = None
    current_production_tonnes_year: Optional[float] = None
    households_supplied: Optional[int] = None
    status: ProjectStatus = ProjectStatus.PROPOSED
    is_active: bool = True


class UrbanAgSummary(BaseSchema):
    region_id: int
    total_sites: int
    operational_sites: int
    total_area_sqm: float
    total_production_tonnes_year: float
    households_served: int
    by_type: Dict[str, int]


# Crop Diversification Plan Schemas
class CropDiversificationPlanCreate(BaseModel):
    region_id: int
    plan_name: str = Field(..., max_length=255)
    current_crop_mix: Dict[str, float]
    target_crop_mix: Dict[str, float]
    vulnerable_crops: Optional[List[str]] = None
    recommended_crops: Optional[List[str]] = None
    implementation_phases: Optional[List[Dict[str, Any]]] = None
    estimated_duration_years: Optional[int] = None
    investment_required_usd: Optional[float] = None


class CropDiversificationPlanUpdate(BaseModel):
    status: Optional[ProjectStatus] = None
    target_crop_mix: Optional[Dict[str, float]] = None
    implementation_start: Optional[datetime] = None


class CropDiversificationPlanResponse(BaseSchema, TimestampMixin):
    id: int
    plan_code: str
    plan_name: str
    region_id: int
    current_crop_mix: Dict[str, float]
    target_crop_mix: Dict[str, float]
    current_diversity_index: Optional[float] = None
    target_diversity_index: Optional[float] = None
    vulnerable_crops: Optional[List[str]] = None
    recommended_crops: Optional[List[str]] = None
    status: ProjectStatus = ProjectStatus.PROPOSED


# Resilience Recommendation Schemas
class ResilienceRecommendationCreate(BaseModel):
    region_id: int
    category: str = Field(..., max_length=100)
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    priority: int = Field(..., ge=1, le=5)
    urgency: str = Field(..., pattern="^(immediate|short_term|medium_term|long_term)$")
    impact_score: float = Field(..., ge=0, le=1)
    feasibility_score: float = Field(..., ge=0, le=1)
    current_situation: Optional[str] = None
    gap_identified: Optional[str] = None
    expected_outcome: Optional[str] = None
    implementation_steps: Optional[List[Dict[str, Any]]] = None
    estimated_cost_usd: Optional[float] = None
    expected_benefit_usd: Optional[float] = None
    model_name: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)


class ResilienceRecommendationUpdate(BaseModel):
    status: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    is_active: Optional[bool] = None


class ResilienceRecommendationResponse(BaseSchema, TimestampMixin):
    id: int
    recommendation_code: str
    region_id: int
    category: str
    title: str
    description: Optional[str] = None
    priority: int
    urgency: str
    impact_score: float
    feasibility_score: float
    estimated_cost_usd: Optional[float] = None
    expected_benefit_usd: Optional[float] = None
    confidence_score: Optional[float] = None
    status: str = "generated"
    is_active: bool = True


# Land Conversion Opportunity Schemas
class LandConversionOpportunityCreate(BaseModel):
    region_id: int
    location_name: Optional[str] = None
    latitude: float
    longitude: float
    current_use: str
    area_sqm: float
    soil_quality: Optional[str] = None
    water_access: bool = False
    power_access: bool = False
    recommended_use: Optional[str] = None
    recommended_crops: Optional[List[str]] = None
    production_potential_tonnes_year: Optional[float] = None
    conversion_cost_usd: Optional[float] = None
    feasibility_score: Optional[float] = Field(None, ge=0, le=1)


class LandConversionOpportunityResponse(BaseSchema, TimestampMixin):
    id: int
    region_id: int
    location_name: Optional[str] = None
    latitude: float
    longitude: float
    current_use: str
    area_sqm: float
    soil_quality: Optional[str] = None
    recommended_use: Optional[str] = None
    production_potential_tonnes_year: Optional[float] = None
    feasibility_score: Optional[float] = None
    status: str = "identified"
    is_active: bool = True


# Analysis Schemas
class ResilienceAssessment(BaseSchema):
    region_id: int
    assessment_date: datetime
    overall_resilience_score: float
    production_resilience: float
    distribution_resilience: float
    storage_resilience: float
    economic_resilience: float
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]
    priority_recommendations: List[Dict[str, Any]]


class FoodProductionPotential(BaseSchema):
    region_id: int
    current_production_tonnes: float
    potential_production_tonnes: float
    gap_tonnes: float
    urban_agriculture_potential: float
    land_conversion_potential: float
    recommended_interventions: List[Dict[str, Any]]
    investment_needed_usd: float
    timeline_years: int


class ClimateAdaptationPlan(BaseSchema):
    region_id: int
    climate_risks: List[Dict[str, Any]]
    vulnerable_crops: List[str]
    adaptation_strategies: List[Dict[str, Any]]
    recommended_crop_varieties: List[Dict[str, Any]]
    infrastructure_needs: List[Dict[str, Any]]
    estimated_cost_usd: float
    implementation_timeline: List[Dict[str, Any]]


class RegionalResilienceSummary(BaseSchema):
    region_id: int
    region_name: str
    resilience_score: float
    trend: str
    key_metrics: Dict[str, float]
    active_projects: int
    recommendations_pending: int
    recent_improvements: List[str]

"""
Regional food dependency schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .common import BaseSchema, TimestampMixin, RiskScore


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Regional Dependency Schemas
class RegionalDependencyBase(BaseModel):
    region_id: int


class RegionalDependencyCreate(RegionalDependencyBase):
    import_dependency_pct: Optional[float] = Field(None, ge=0, le=100)
    domestic_production_pct: Optional[float] = Field(None, ge=0, le=100)
    aid_dependency_pct: Optional[float] = Field(None, ge=0, le=100)
    strategic_reserve_days: Optional[float] = None
    minimum_reserve_days: Optional[float] = None
    num_import_sources: Optional[int] = None
    primary_port_name: Optional[str] = None
    cold_storage_days: Optional[float] = None
    population_at_risk: Optional[int] = None
    vulnerabilities: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None


class RegionalDependencyUpdate(BaseModel):
    import_dependency_pct: Optional[float] = Field(None, ge=0, le=100)
    strategic_reserve_days: Optional[float] = None
    risk_score: Optional[float] = Field(None, ge=0, le=100)
    overall_risk_level: Optional[RiskLevel] = None
    vulnerabilities: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None


class RegionalDependencyResponse(RegionalDependencyBase, TimestampMixin, BaseSchema):
    id: int
    import_dependency_pct: Optional[float] = None
    domestic_production_pct: Optional[float] = None
    aid_dependency_pct: Optional[float] = None
    strategic_reserve_days: Optional[float] = None
    reserve_status: Optional[str] = None
    num_import_sources: Optional[int] = None
    single_source_dependency: bool = False
    port_dependency: bool = False
    population_at_risk: Optional[int] = None
    overall_risk_level: Optional[RiskLevel] = None
    risk_score: Optional[float] = None
    vulnerabilities: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None


class DependencyProfile(BaseSchema):
    """Comprehensive dependency profile for a region."""
    region_id: int
    region_name: str
    population: int
    import_dependency_pct: float
    strategic_reserve_days: float
    risk_level: RiskLevel
    risk_score: float
    primary_import_sources: List[Dict[str, Any]]
    vulnerabilities: List[str]
    recommendations: List[str]
    last_assessment_date: Optional[datetime] = None


# Import Source Schemas
class ImportSourceBase(BaseModel):
    dependency_id: int
    source_country: str = Field(..., max_length=100)
    food_type: str = Field(..., max_length=100)


class ImportSourceCreate(ImportSourceBase):
    category_id: Optional[int] = None
    source_region: Optional[str] = None
    source_port: Optional[str] = None
    is_primary_source: bool = False
    annual_volume_tonnes: Optional[float] = None
    annual_value_usd: Optional[float] = None
    share_of_imports_pct: Optional[float] = Field(None, ge=0, le=100)
    reliability_score: Optional[float] = Field(None, ge=0, le=1)
    avg_lead_time_days: Optional[float] = None
    political_risk: Optional[float] = Field(None, ge=0, le=1)
    logistics_risk: Optional[float] = Field(None, ge=0, le=1)
    alternative_sources: Optional[List[Dict[str, Any]]] = None


class ImportSourceUpdate(BaseModel):
    annual_volume_tonnes: Optional[float] = None
    share_of_imports_pct: Optional[float] = Field(None, ge=0, le=100)
    reliability_score: Optional[float] = Field(None, ge=0, le=1)
    political_risk: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None


class ImportSourceResponse(ImportSourceBase, TimestampMixin, BaseSchema):
    id: int
    category_id: Optional[int] = None
    is_primary_source: bool = False
    annual_volume_tonnes: Optional[float] = None
    share_of_imports_pct: Optional[float] = None
    reliability_score: Optional[float] = None
    overall_risk: Optional[float] = None
    is_active: bool = True


# Food Import Schemas
class FoodImportCreate(BaseModel):
    region_id: int
    source_id: Optional[int] = None
    category_id: Optional[int] = None
    import_date: datetime
    food_type: str
    source_country: str
    quantity_tonnes: float = Field(..., gt=0)
    value_usd: Optional[float] = None
    port_of_entry: Optional[str] = None
    transport_mode: Optional[str] = None
    destination_center_id: Optional[int] = None


class FoodImportUpdate(BaseModel):
    shipment_status: Optional[str] = None
    customs_cleared: Optional[bool] = None
    quality_inspected: Optional[bool] = None
    quality_passed: Optional[bool] = None
    delay_days: Optional[int] = None
    delay_reason: Optional[str] = None


class FoodImportResponse(BaseSchema, TimestampMixin):
    id: int
    region_id: int
    import_date: datetime
    food_type: str
    source_country: str
    quantity_tonnes: float
    value_usd: Optional[float] = None
    shipment_status: Optional[str] = None
    customs_cleared: bool = False
    quality_passed: Optional[bool] = None
    delay_days: int = 0


class ImportSummary(BaseSchema):
    region_id: int
    period_start: datetime
    period_end: datetime
    total_imports_tonnes: float
    total_value_usd: float
    by_country: Dict[str, float]
    by_food_type: Dict[str, float]
    avg_lead_time_days: float
    on_time_percentage: float


# Vulnerability Assessment Schemas
class VulnerabilityAssessmentCreate(BaseModel):
    dependency_id: int
    region_id: int
    assessment_period: str = Field(..., pattern="^(quarterly|annual)$")
    overall_score: float = Field(..., ge=0, le=100)
    production_score: Optional[float] = Field(None, ge=0, le=100)
    import_score: Optional[float] = Field(None, ge=0, le=100)
    distribution_score: Optional[float] = Field(None, ge=0, le=100)
    storage_score: Optional[float] = Field(None, ge=0, le=100)
    economic_score: Optional[float] = Field(None, ge=0, le=100)
    climate_risk: Optional[float] = Field(None, ge=0, le=1)
    conflict_risk: Optional[float] = Field(None, ge=0, le=1)
    priority_actions: Optional[List[Dict[str, Any]]] = None
    resource_needs: Optional[List[Dict[str, Any]]] = None
    assessor: Optional[str] = None


class VulnerabilityAssessmentResponse(BaseSchema, TimestampMixin):
    id: int
    dependency_id: int
    region_id: int
    assessment_date: datetime
    assessment_period: str
    overall_score: float
    production_score: Optional[float] = None
    import_score: Optional[float] = None
    distribution_score: Optional[float] = None
    storage_score: Optional[float] = None
    score_change: Optional[float] = None
    trend_direction: Optional[str] = None
    priority_actions: Optional[List[Dict[str, Any]]] = None
    status: str = "draft"


class VulnerabilityTrend(BaseSchema):
    region_id: int
    assessments: List[Dict[str, Any]]
    overall_trend: str
    improving_areas: List[str]
    declining_areas: List[str]
    recommendations: List[str]


# Analysis Response Schemas
class DependencyRiskAnalysis(BaseSchema):
    region_id: int
    region_name: str
    risk_level: RiskLevel
    risk_score: float
    risk_breakdown: RiskScore
    critical_dependencies: List[Dict[str, Any]]
    mitigation_recommendations: List[str]
    scenario_analysis: Dict[str, Any]


class ImportDisruptionScenario(BaseSchema):
    scenario_name: str
    description: str
    affected_sources: List[str]
    impact_tonnes: float
    impact_days_supply: float
    mitigation_options: List[Dict[str, Any]]
    estimated_recovery_days: int

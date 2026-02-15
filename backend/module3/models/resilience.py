"""
Agricultural resilience and long-term food security planning models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Text, Boolean,
    ForeignKey, Enum as SQLEnum, JSON, Index
)
from sqlalchemy.orm import relationship
import enum

from .base import Base


class SiteType(enum.Enum):
    """Urban agriculture site types."""
    ROOFTOP_GARDEN = "rooftop_garden"
    VERTICAL_FARM = "vertical_farm"
    COMMUNITY_GARDEN = "community_garden"
    HYDROPONICS = "hydroponics"
    AQUAPONICS = "aquaponics"
    GREENHOUSE = "greenhouse"
    VACANT_LOT = "vacant_lot"
    PERI_URBAN = "peri_urban"


class ProjectStatus(enum.Enum):
    """Project implementation status."""
    PROPOSED = "proposed"
    PLANNING = "planning"
    APPROVED = "approved"
    UNDER_CONSTRUCTION = "under_construction"
    OPERATIONAL = "operational"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class UrbanAgricultureSite(Base):
    """Urban and peri-urban agriculture sites."""

    __tablename__ = "urban_agriculture_sites"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)

    # Site identification
    site_code = Column(String(50), unique=True, nullable=False)
    site_name = Column(String(255), nullable=False)
    site_type = Column(SQLEnum(SiteType), nullable=False)

    # Location
    address = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation_m = Column(Float)

    # Area
    total_area_sqm = Column(Float)
    cultivable_area_sqm = Column(Float)
    built_area_sqm = Column(Float)

    # Land ownership
    land_owner = Column(String(255))
    land_ownership_type = Column(String(50))  # public, private, community
    lease_end_date = Column(DateTime)

    # Infrastructure
    water_source = Column(String(100))
    water_availability_liters_day = Column(Float)
    power_source = Column(String(100))
    power_capacity_kw = Column(Float)
    has_greenhouse = Column(Boolean, default=False)
    has_irrigation = Column(Boolean, default=False)
    has_cold_storage = Column(Boolean, default=False)

    # Production
    crops_grown = Column(JSON)  # List of crops
    production_capacity_tonnes_year = Column(Float)
    current_production_tonnes_year = Column(Float)
    production_method = Column(String(100))  # organic, conventional, etc.

    # Economics
    setup_cost_usd = Column(Float)
    operating_cost_annual_usd = Column(Float)
    revenue_annual_usd = Column(Float)
    jobs_created = Column(Integer)
    volunteers_engaged = Column(Integer)

    # Impact
    households_supplied = Column(Integer)
    calories_produced_daily = Column(Float)
    food_security_contribution_pct = Column(Float)

    # Status
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PROPOSED)
    established_date = Column(DateTime)

    # Management
    operator_name = Column(String(255))
    operator_contact = Column(String(100))
    partnership_organizations = Column(JSON)

    notes = Column(Text)
    is_active = Column(Boolean, default=True)

    # Relationships
    region = relationship("Region")

    __table_args__ = (
        Index("idx_urban_ag_region", "region_id"),
        Index("idx_urban_ag_type", "site_type"),
        Index("idx_urban_ag_status", "status"),
    )


class CropDiversificationPlan(Base):
    """Crop diversification planning for resilience."""

    __tablename__ = "crop_diversification_plans"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)

    # Plan identification
    plan_code = Column(String(50), unique=True, nullable=False)
    plan_name = Column(String(255), nullable=False)

    # Current state
    current_crop_mix = Column(JSON)  # {crop: percentage}
    current_diversity_index = Column(Float)  # 0-1
    current_risk_score = Column(Float)

    # Target state
    target_crop_mix = Column(JSON)  # {crop: percentage}
    target_diversity_index = Column(Float)
    target_risk_score = Column(Float)

    # Analysis
    vulnerable_crops = Column(JSON)  # Crops at risk
    recommended_crops = Column(JSON)  # Recommended additions
    crops_to_reduce = Column(JSON)  # Recommended reductions

    # Climate considerations
    climate_projections = Column(JSON)
    drought_resistant_crops = Column(JSON)
    flood_resistant_crops = Column(JSON)
    heat_tolerant_crops = Column(JSON)

    # Nutritional considerations
    nutritional_gaps = Column(JSON)
    nutrient_dense_crops = Column(JSON)

    # Implementation
    implementation_phases = Column(JSON)
    estimated_duration_years = Column(Integer)
    land_conversion_hectares = Column(Float)

    # Economics
    investment_required_usd = Column(Float)
    expected_roi_pct = Column(Float)
    farmer_incentives = Column(JSON)

    # Support needed
    training_requirements = Column(JSON)
    input_supply_needs = Column(JSON)
    infrastructure_needs = Column(JSON)

    # Status
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PROPOSED)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    implementation_start = Column(DateTime)

    notes = Column(Text)

    # Relationships
    region = relationship("Region")

    __table_args__ = (
        Index("idx_diversification_region", "region_id"),
        Index("idx_diversification_status", "status"),
    )


class ResilienceRecommendation(Base):
    """AI-generated resilience recommendations."""

    __tablename__ = "resilience_recommendations"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)

    # Recommendation details
    recommendation_code = Column(String(50), unique=True, nullable=False)
    category = Column(String(100), nullable=False)  # production, storage, distribution, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Priority
    priority = Column(Integer)  # 1 = highest
    urgency = Column(String(20))  # immediate, short_term, medium_term, long_term
    impact_score = Column(Float)  # 0-1
    feasibility_score = Column(Float)  # 0-1

    # Context
    current_situation = Column(Text)
    gap_identified = Column(Text)
    expected_outcome = Column(Text)

    # Implementation
    implementation_steps = Column(JSON)
    required_resources = Column(JSON)
    stakeholders_involved = Column(JSON)
    timeline_months = Column(Integer)

    # Costs and benefits
    estimated_cost_usd = Column(Float)
    expected_benefit_usd = Column(Float)
    benefit_description = Column(Text)

    # Risk reduction
    risk_reduction_pct = Column(Float)
    resilience_improvement_pct = Column(Float)
    population_benefiting = Column(Integer)

    # Evidence
    supporting_evidence = Column(JSON)
    similar_implementations = Column(JSON)
    success_rate_similar = Column(Float)

    # AI model info
    model_name = Column(String(100))
    model_version = Column(String(50))
    confidence_score = Column(Float)
    generated_at = Column(DateTime, default=datetime.utcnow)

    # Status
    status = Column(String(50), default="generated")  # generated, reviewed, approved, implemented, rejected
    reviewed_by = Column(String(100))
    review_notes = Column(Text)

    notes = Column(Text)
    is_active = Column(Boolean, default=True)

    # Relationships
    region = relationship("Region")

    __table_args__ = (
        Index("idx_recommendation_region", "region_id"),
        Index("idx_recommendation_category", "category"),
        Index("idx_recommendation_priority", "priority"),
    )


class LandConversionOpportunity(Base):
    """Opportunities for converting underutilized land to food production."""

    __tablename__ = "land_conversion_opportunities"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)

    # Location
    location_name = Column(String(255))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geometry = Column(JSON)  # GeoJSON polygon

    # Land details
    current_use = Column(String(100))  # vacant, parking, brownfield, etc.
    area_sqm = Column(Float)
    soil_quality = Column(String(20))  # poor, fair, good, excellent
    soil_contamination_risk = Column(Float)  # 0-1

    # Infrastructure
    water_access = Column(Boolean)
    power_access = Column(Boolean)
    road_access = Column(Boolean)
    distance_to_market_km = Column(Float)

    # Ownership
    ownership_type = Column(String(50))
    owner_contact = Column(String(255))
    acquisition_difficulty = Column(String(20))  # easy, moderate, difficult

    # Potential
    recommended_use = Column(String(100))
    recommended_crops = Column(JSON)
    production_potential_tonnes_year = Column(Float)
    households_serviceable = Column(Integer)

    # Economics
    conversion_cost_usd = Column(Float)
    annual_production_value_usd = Column(Float)
    payback_period_years = Column(Float)

    # Feasibility
    feasibility_score = Column(Float)  # 0-1
    barriers = Column(JSON)
    enablers = Column(JSON)

    # Status
    status = Column(String(50), default="identified")
    identified_date = Column(DateTime, default=datetime.utcnow)
    assessment_date = Column(DateTime)

    notes = Column(Text)
    is_active = Column(Boolean, default=True)

    # Relationships
    region = relationship("Region")

    __table_args__ = (
        Index("idx_land_conv_region", "region_id"),
        Index("idx_land_conv_use", "current_use"),
    )

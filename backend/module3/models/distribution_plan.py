"""
Food distribution planning and allocation models.
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


class PlanStatus(enum.Enum):
    """Distribution plan status."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PopulationType(enum.Enum):
    """Population category types."""
    ELDERLY = "elderly"
    CHILDREN = "children"
    PREGNANT = "pregnant"
    IMMUNOCOMPROMISED = "immunocompromised"
    HEALTHCARE_WORKER = "healthcare_worker"
    ESSENTIAL_WORKER = "essential_worker"
    DISABLED = "disabled"
    LOW_INCOME = "low_income"
    GENERAL = "general"


class DistributionPlan(Base):
    """Food distribution plans during crisis."""

    __tablename__ = "distribution_plans"

    # Plan identification
    plan_code = Column(String(50), unique=True, nullable=False)
    plan_name = Column(String(255), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)

    # Trigger
    alert_id = Column(Integer, ForeignKey("shortage_alerts.id"))
    trigger_reason = Column(Text)

    # Status and timing
    status = Column(SQLEnum(PlanStatus), default=PlanStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    approved_by = Column(String(100))
    activation_date = Column(DateTime)
    end_date = Column(DateTime)
    duration_days = Column(Integer)

    # Coverage
    population_covered = Column(Integer)
    households_covered = Column(Integer)
    geographic_coverage_pct = Column(Float)

    # Resources
    total_food_tonnes = Column(Float)
    total_budget_usd = Column(Float)
    distribution_centers_count = Column(Integer)
    distribution_points_count = Column(Integer)
    vehicles_allocated = Column(Integer)
    staff_allocated = Column(Integer)

    # Food allocation by category
    food_allocation = Column(JSON)  # {category_id: tonnes}

    # Priority settings
    priority_weights = Column(JSON)  # {population_type: weight}

    # Logistics
    distribution_schedule = Column(JSON)  # Daily/weekly schedule
    vehicle_routes = Column(JSON)

    # Monitoring
    completion_pct = Column(Float, default=0)
    food_distributed_tonnes = Column(Float, default=0)
    beneficiaries_served = Column(Integer, default=0)

    # Effectiveness
    efficiency_score = Column(Float)
    coverage_score = Column(Float)
    timeliness_score = Column(Float)

    notes = Column(Text)

    # Relationships
    region = relationship("Region")
    alert = relationship("ShortageAlert")
    distribution_points = relationship("DistributionPoint", back_populates="plan")
    allocations = relationship("RationAllocation", back_populates="plan")

    __table_args__ = (
        Index("idx_plan_region_status", "region_id", "status"),
        Index("idx_plan_dates", "activation_date", "end_date"),
    )


class DistributionPoint(Base):
    """Physical food distribution points."""

    __tablename__ = "distribution_points"

    plan_id = Column(Integer, ForeignKey("distribution_plans.id"), nullable=False)
    center_id = Column(Integer, ForeignKey("distribution_centers.id"))
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)

    # Location
    point_code = Column(String(50), unique=True, nullable=False)
    point_name = Column(String(255), nullable=False)
    address = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Type
    point_type = Column(String(50))  # fixed, mobile, temporary
    facility_type = Column(String(100))  # school, community_center, etc.

    # Coverage
    assigned_population = Column(Integer)
    assigned_households = Column(Integer)
    coverage_radius_km = Column(Float)
    assigned_zones = Column(JSON)  # Geographic zones served

    # Capacity
    daily_capacity_beneficiaries = Column(Integer)
    storage_capacity_tonnes = Column(Float)
    current_inventory_tonnes = Column(Float)

    # Operations
    operating_hours = Column(JSON)
    staff_count = Column(Integer)
    volunteers_count = Column(Integer)

    # Contact
    coordinator_name = Column(String(100))
    coordinator_phone = Column(String(50))

    # Status
    operational_status = Column(String(50), default="planned")
    opened_at = Column(DateTime)
    closed_at = Column(DateTime)

    # Metrics
    total_beneficiaries_served = Column(Integer, default=0)
    total_food_distributed_tonnes = Column(Float, default=0)
    avg_wait_time_minutes = Column(Float)
    satisfaction_score = Column(Float)

    is_active = Column(Boolean, default=True)

    # Relationships
    plan = relationship("DistributionPlan", back_populates="distribution_points")
    center = relationship("DistributionCenter", back_populates="distribution_points")
    region = relationship("Region")

    __table_args__ = (
        Index("idx_dist_point_plan", "plan_id"),
        Index("idx_dist_point_location", "latitude", "longitude"),
    )


class RationAllocation(Base):
    """Ration allocation calculations and records."""

    __tablename__ = "ration_allocations"

    plan_id = Column(Integer, ForeignKey("distribution_plans.id"), nullable=False)
    distribution_point_id = Column(Integer, ForeignKey("distribution_points.id"))

    # Allocation period
    allocation_date = Column(DateTime, nullable=False)
    period_start = Column(DateTime)
    period_end = Column(DateTime)

    # Population segment
    population_type = Column(SQLEnum(PopulationType), nullable=False)
    population_count = Column(Integer)
    households_count = Column(Integer)

    # Ration composition
    ration_composition = Column(JSON)  # {food_item: quantity_kg}
    total_ration_kg = Column(Float)
    calories_per_ration = Column(Integer)
    protein_g_per_ration = Column(Float)

    # Distribution
    rations_planned = Column(Integer)
    rations_distributed = Column(Integer, default=0)
    distribution_pct = Column(Float, default=0)

    # Quantities
    food_allocated_tonnes = Column(Float)
    food_distributed_tonnes = Column(Float, default=0)

    # Nutritional targets
    daily_caloric_target = Column(Integer)
    daily_protein_target_g = Column(Float)
    nutritional_adequacy_pct = Column(Float)

    # Cost
    cost_per_ration_usd = Column(Float)
    total_cost_usd = Column(Float)

    # Status
    status = Column(String(50), default="planned")

    notes = Column(Text)

    # Relationships
    plan = relationship("DistributionPlan", back_populates="allocations")
    distribution_point = relationship("DistributionPoint")

    __table_args__ = (
        Index("idx_allocation_plan_date", "plan_id", "allocation_date"),
        Index("idx_allocation_type", "population_type"),
    )


class VulnerablePopulation(Base):
    """Vulnerable population tracking for priority distribution."""

    __tablename__ = "vulnerable_populations"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)

    # Population type
    population_type = Column(SQLEnum(PopulationType), nullable=False)

    # Demographics
    total_count = Column(Integer)
    households_count = Column(Integer)
    registered_count = Column(Integer)  # Registered for aid

    # Geographic distribution
    distribution_by_zone = Column(JSON)  # {zone_id: count}

    # Nutritional needs
    daily_caloric_need = Column(Integer)
    special_dietary_needs = Column(JSON)

    # Priority
    priority_level = Column(Integer)  # 1 = highest
    priority_weight = Column(Float)

    # Access
    mobility_limited_pct = Column(Float)
    requires_home_delivery_pct = Column(Float)
    avg_distance_to_distribution_km = Column(Float)

    # Contact
    community_contact_name = Column(String(100))
    community_contact_phone = Column(String(50))
    ngo_partners = Column(JSON)

    # Status
    last_updated = Column(DateTime, default=datetime.utcnow)
    data_source = Column(String(100))
    data_quality_score = Column(Float)  # 0-1

    notes = Column(Text)

    # Relationships
    region = relationship("Region")

    __table_args__ = (
        Index("idx_vulnerable_region_type", "region_id", "population_type"),
    )


class DistributionRecord(Base):
    """Individual distribution transaction records."""

    __tablename__ = "distribution_records"

    plan_id = Column(Integer, ForeignKey("distribution_plans.id"), nullable=False)
    distribution_point_id = Column(Integer, ForeignKey("distribution_points.id"), nullable=False)
    allocation_id = Column(Integer, ForeignKey("ration_allocations.id"))

    # Transaction details
    distribution_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    transaction_code = Column(String(50), unique=True)

    # Beneficiary (anonymized)
    beneficiary_id_hash = Column(String(64))  # Hashed for privacy
    household_size = Column(Integer)
    population_type = Column(SQLEnum(PopulationType))

    # Distribution
    items_distributed = Column(JSON)  # {item: quantity}
    total_weight_kg = Column(Float)
    total_calories = Column(Integer)

    # Verification
    id_verified = Column(Boolean, default=False)
    signature_collected = Column(Boolean, default=False)

    # Staff
    distributed_by = Column(String(100))

    notes = Column(Text)

    # Relationships
    plan = relationship("DistributionPlan")
    distribution_point = relationship("DistributionPoint")
    allocation = relationship("RationAllocation")

    __table_args__ = (
        Index("idx_record_point_date", "distribution_point_id", "distribution_date"),
    )

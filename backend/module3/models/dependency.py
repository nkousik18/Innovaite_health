"""
Regional food dependency and import tracking models.
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


class RiskLevel(enum.Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DependencyType(enum.Enum):
    """Type of food dependency."""
    IMPORT = "import"
    DOMESTIC = "domestic"
    AID = "aid"
    MIXED = "mixed"


class RegionalDependency(Base):
    """Regional food dependency profiles."""

    __tablename__ = "regional_dependencies"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, unique=True)

    # Overall dependency metrics
    import_dependency_pct = Column(Float)  # % of calories from imports
    domestic_production_pct = Column(Float)
    aid_dependency_pct = Column(Float)

    # Strategic reserves
    strategic_reserve_days = Column(Float)  # Days of food reserves
    minimum_reserve_days = Column(Float)  # Target minimum
    reserve_status = Column(String(20))  # critical, low, adequate, surplus

    # Supply diversity
    num_import_sources = Column(Integer)
    single_source_dependency = Column(Boolean, default=False)  # >50% from one source
    primary_source_pct = Column(Float)  # % from largest source

    # Infrastructure
    port_dependency = Column(Boolean, default=False)  # Single port for >80% imports
    primary_port_name = Column(String(100))
    cold_storage_days = Column(Float)  # Days of cold storage capacity

    # Population at risk
    population_at_risk = Column(Integer)  # If supply disrupted
    vulnerable_population = Column(Integer)  # Elderly, children, immunocompromised

    # Risk assessment
    overall_risk_level = Column(SQLEnum(RiskLevel))
    risk_score = Column(Float)  # 0-100
    last_assessment_date = Column(DateTime)

    # Vulnerabilities (JSON list)
    vulnerabilities = Column(JSON)
    recommendations = Column(JSON)

    # Relationships
    region = relationship("Region", back_populates="dependencies")
    import_sources = relationship("ImportSource", back_populates="dependency")
    assessments = relationship("VulnerabilityAssessment", back_populates="dependency")

    __table_args__ = (
        Index("idx_dependency_risk", "overall_risk_level"),
    )


class ImportSource(Base):
    """Food import sources for a region."""

    __tablename__ = "import_sources"

    dependency_id = Column(Integer, ForeignKey("regional_dependencies.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("food_categories.id"))

    # Source details
    source_country = Column(String(100), nullable=False)
    source_region = Column(String(100))
    source_port = Column(String(100))

    # Food type
    food_type = Column(String(100), nullable=False)  # e.g., "Rice", "Wheat"
    is_primary_source = Column(Boolean, default=False)

    # Volume and value
    annual_volume_tonnes = Column(Float)
    annual_value_usd = Column(Float)
    share_of_imports_pct = Column(Float)

    # Reliability metrics
    reliability_score = Column(Float)  # 0-1
    avg_lead_time_days = Column(Float)
    lead_time_variability_days = Column(Float)
    on_time_delivery_pct = Column(Float)

    # Risk factors
    political_risk = Column(Float)  # 0-1
    logistics_risk = Column(Float)  # 0-1
    price_volatility = Column(Float)  # 0-1
    overall_risk = Column(Float)  # 0-1

    # Trade relationship
    trade_agreement = Column(String(100))
    tariff_rate_pct = Column(Float)
    quota_tonnes = Column(Float)

    # Alternative sources
    alternative_sources = Column(JSON)  # List of backup suppliers

    is_active = Column(Boolean, default=True)

    # Relationships
    dependency = relationship("RegionalDependency", back_populates="import_sources")
    category = relationship("FoodCategory")

    __table_args__ = (
        Index("idx_import_source_country", "source_country"),
        Index("idx_import_food_type", "food_type"),
    )


class FoodImport(Base):
    """Individual food import records."""

    __tablename__ = "food_imports"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("import_sources.id"))
    category_id = Column(Integer, ForeignKey("food_categories.id"))

    # Import details
    import_date = Column(DateTime, nullable=False)
    food_type = Column(String(100), nullable=False)
    source_country = Column(String(100), nullable=False)

    # Quantity and value
    quantity_tonnes = Column(Float, nullable=False)
    value_usd = Column(Float)
    price_per_tonne = Column(Float)

    # Logistics
    port_of_entry = Column(String(100))
    transport_mode = Column(String(50))
    lead_time_days = Column(Integer)

    # Status
    shipment_status = Column(String(50))  # in_transit, arrived, cleared, delivered
    customs_cleared = Column(Boolean, default=False)
    quality_inspected = Column(Boolean, default=False)
    quality_passed = Column(Boolean)

    # Issues
    delay_days = Column(Integer, default=0)
    delay_reason = Column(String(255))
    quantity_rejected_tonnes = Column(Float)
    rejection_reason = Column(String(255))

    # Destination
    destination_center_id = Column(Integer, ForeignKey("distribution_centers.id"))

    data_source = Column(String(100))

    # Relationships
    region = relationship("Region")
    source = relationship("ImportSource")
    category = relationship("FoodCategory")
    destination_center = relationship("DistributionCenter")

    __table_args__ = (
        Index("idx_import_region_date", "region_id", "import_date"),
        Index("idx_import_source", "source_country", "import_date"),
    )


class VulnerabilityAssessment(Base):
    """Periodic vulnerability assessments for regions."""

    __tablename__ = "vulnerability_assessments"

    dependency_id = Column(Integer, ForeignKey("regional_dependencies.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)

    # Assessment details
    assessment_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    assessment_period = Column(String(20))  # quarterly, annual
    assessor = Column(String(100))
    methodology = Column(String(100))

    # Scores (0-100)
    overall_score = Column(Float, nullable=False)
    production_score = Column(Float)
    import_score = Column(Float)
    distribution_score = Column(Float)
    storage_score = Column(Float)
    economic_score = Column(Float)

    # Component analysis
    production_capacity = Column(Float)  # % of needs met locally
    import_reliability = Column(Float)  # 0-1
    distribution_coverage = Column(Float)  # % population covered
    storage_adequacy = Column(Float)  # Days of storage
    purchasing_power = Column(Float)  # Economic access

    # Risk factors
    climate_risk = Column(Float)
    conflict_risk = Column(Float)
    economic_risk = Column(Float)
    health_risk = Column(Float)
    infrastructure_risk = Column(Float)

    # Trend analysis
    score_change = Column(Float)  # vs previous assessment
    trend_direction = Column(String(20))  # improving, stable, declining

    # Recommendations
    priority_actions = Column(JSON)
    resource_needs = Column(JSON)
    estimated_cost_usd = Column(Float)

    # Status
    status = Column(String(20))  # draft, final, approved
    approved_by = Column(String(100))
    approved_at = Column(DateTime)

    notes = Column(Text)

    # Relationships
    dependency = relationship("RegionalDependency", back_populates="assessments")
    region = relationship("Region")

    __table_args__ = (
        Index("idx_assessment_region_date", "region_id", "assessment_date"),
        Index("idx_assessment_score", "overall_score"),
    )

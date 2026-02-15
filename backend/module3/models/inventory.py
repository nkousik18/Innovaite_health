"""
Food inventory and consumption tracking models.
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


class FoodCategoryType(enum.Enum):
    """Food category types."""
    STAPLE_GRAINS = "staple_grains"
    PROTEIN = "protein"
    VEGETABLES = "vegetables"
    FRUITS = "fruits"
    DAIRY = "dairy"
    OILS_FATS = "oils_fats"
    SHELF_STABLE = "shelf_stable"
    BEVERAGES = "beverages"
    INFANT_FOOD = "infant_food"
    MEDICAL_NUTRITION = "medical_nutrition"


class StorageType(enum.Enum):
    """Storage type requirements."""
    AMBIENT = "ambient"
    REFRIGERATED = "refrigerated"
    FROZEN = "frozen"
    CONTROLLED = "controlled"


class FoodCategory(Base):
    """Food categories for inventory management."""

    __tablename__ = "food_categories"

    name = Column(String(100), nullable=False, unique=True)
    category_type = Column(SQLEnum(FoodCategoryType), nullable=False)
    description = Column(Text)

    # Storage requirements
    storage_type = Column(SQLEnum(StorageType), default=StorageType.AMBIENT)
    min_storage_temp_c = Column(Float)
    max_storage_temp_c = Column(Float)
    avg_shelf_life_days = Column(Integer)

    # Nutritional importance
    caloric_density = Column(Float)  # kcal per kg
    nutritional_priority = Column(Integer)  # 1 = highest
    essential_nutrients = Column(JSON)  # List of key nutrients

    # Consumption
    daily_per_capita_kg = Column(Float)  # Average consumption
    minimum_per_capita_kg = Column(Float)  # Minimum for survival

    is_active = Column(Boolean, default=True)

    # Relationships
    inventories = relationship("FoodInventory", back_populates="category")


class FoodInventory(Base):
    """Regional food inventory levels."""

    __tablename__ = "food_inventory"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("food_categories.id"), nullable=False)

    # Inventory levels
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    quantity_tonnes = Column(Float, nullable=False)
    quantity_change_tonnes = Column(Float)  # Change from previous record

    # Days of supply
    days_of_supply = Column(Float)  # Based on consumption rate
    consumption_rate_tonnes_per_day = Column(Float)

    # Thresholds
    minimum_stock_tonnes = Column(Float)  # Trigger reorder
    target_stock_tonnes = Column(Float)  # Ideal level
    maximum_stock_tonnes = Column(Float)  # Storage limit

    # Status
    stock_status = Column(String(20))  # critical, low, adequate, surplus
    reorder_triggered = Column(Boolean, default=False)

    # Quality
    avg_days_to_expiry = Column(Float)
    expiring_soon_tonnes = Column(Float)  # Within 7 days
    expired_tonnes = Column(Float)

    # Source breakdown
    local_production_tonnes = Column(Float)
    imported_tonnes = Column(Float)
    aid_received_tonnes = Column(Float)

    data_source = Column(String(100))

    # Relationships
    region = relationship("Region", back_populates="inventories")
    category = relationship("FoodCategory", back_populates="inventories")

    __table_args__ = (
        Index("idx_inventory_region_category", "region_id", "category_id"),
        Index("idx_inventory_date", "recorded_at"),
    )


class WarehouseStock(Base):
    """Specific warehouse stock levels."""

    __tablename__ = "warehouse_stocks"

    distribution_center_id = Column(Integer, ForeignKey("distribution_centers.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("food_categories.id"), nullable=False)

    # Stock levels
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    quantity_tonnes = Column(Float, nullable=False)
    quantity_units = Column(Integer)  # Number of packages/pallets

    # Storage location
    storage_zone = Column(String(50))
    bin_locations = Column(JSON)

    # Quality tracking
    batch_numbers = Column(JSON)
    production_dates = Column(JSON)
    expiry_dates = Column(JSON)
    oldest_stock_days = Column(Integer)
    newest_stock_days = Column(Integer)

    # Temperature monitoring (for cold storage)
    current_temp_c = Column(Float)
    temp_in_range = Column(Boolean, default=True)
    temp_excursion_hours = Column(Float)  # Hours out of range

    # Movement
    inbound_today_tonnes = Column(Float)
    outbound_today_tonnes = Column(Float)
    pending_inbound_tonnes = Column(Float)
    pending_outbound_tonnes = Column(Float)

    # Status
    stock_status = Column(String(20))
    quality_hold = Column(Boolean, default=False)
    quality_hold_reason = Column(String(255))

    # Relationships
    distribution_center = relationship("DistributionCenter", back_populates="stocks")
    category = relationship("FoodCategory")

    __table_args__ = (
        Index("idx_warehouse_stock_center", "distribution_center_id"),
        Index("idx_warehouse_stock_date", "recorded_at"),
    )


class ConsumptionPattern(Base):
    """Food consumption patterns by region."""

    __tablename__ = "consumption_patterns"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("food_categories.id"), nullable=False)

    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(20))  # daily, weekly, monthly

    # Consumption data
    total_consumption_tonnes = Column(Float)
    per_capita_kg = Column(Float)
    households_covered = Column(Integer)

    # Trends
    consumption_trend = Column(String(20))  # increasing, stable, decreasing
    trend_percentage = Column(Float)
    seasonal_factor = Column(Float)  # Multiplier for seasonal variation

    # Panic buying detection
    anomaly_detected = Column(Boolean, default=False)
    anomaly_score = Column(Float)  # 0-1
    baseline_consumption_tonnes = Column(Float)
    deviation_percentage = Column(Float)

    # Demographics
    urban_consumption_pct = Column(Float)
    rural_consumption_pct = Column(Float)

    # Price impact
    avg_price_per_kg = Column(Float)
    price_change_pct = Column(Float)
    price_elasticity = Column(Float)

    data_source = Column(String(100))

    # Relationships
    region = relationship("Region")
    category = relationship("FoodCategory")

    __table_args__ = (
        Index("idx_consumption_region_category", "region_id", "category_id"),
        Index("idx_consumption_period", "period_start", "period_end"),
    )

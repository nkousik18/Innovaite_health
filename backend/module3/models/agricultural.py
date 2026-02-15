"""
Agricultural production and monitoring models.
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


class CropType(enum.Enum):
    """Crop type classification."""
    STAPLE_GRAIN = "staple_grain"
    PROTEIN = "protein"
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    LEGUME = "legume"
    TUBER = "tuber"
    OIL_SEED = "oil_seed"
    OTHER = "other"


class SeasonType(enum.Enum):
    """Agricultural season types."""
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    WET = "wet"
    DRY = "dry"
    YEAR_ROUND = "year_round"


class Region(Base):
    """Geographic region for food security monitoring."""

    __tablename__ = "regions"

    name = Column(String(255), nullable=False, index=True)
    country = Column(String(100), nullable=False, index=True)
    region_code = Column(String(50), unique=True, nullable=False)

    # Geographic data
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    area_sq_km = Column(Float)
    geometry = Column(JSON)  # GeoJSON polygon

    # Demographics
    population = Column(Integer)
    population_density = Column(Float)  # per sq km
    urban_percentage = Column(Float)

    # Agricultural capacity
    arable_land_sq_km = Column(Float)
    irrigation_coverage = Column(Float)  # percentage
    agricultural_workforce = Column(Integer)

    # Climate
    climate_zone = Column(String(50))
    avg_annual_rainfall_mm = Column(Float)
    avg_temperature_c = Column(Float)

    # Risk factors
    drought_risk = Column(Float)  # 0-1
    flood_risk = Column(Float)  # 0-1
    conflict_risk = Column(Float)  # 0-1

    is_active = Column(Boolean, default=True)

    # Relationships
    productions = relationship("AgriculturalProduction", back_populates="region")
    dependencies = relationship("RegionalDependency", back_populates="region")
    inventories = relationship("FoodInventory", back_populates="region")
    distribution_centers = relationship("DistributionCenter", back_populates="region")
    alerts = relationship("ShortageAlert", back_populates="region")

    __table_args__ = (
        Index("idx_region_country", "country"),
        Index("idx_region_location", "latitude", "longitude"),
    )


class Crop(Base):
    """Crop definitions and nutritional information."""

    __tablename__ = "crops"

    name = Column(String(100), nullable=False, unique=True)
    scientific_name = Column(String(200))
    crop_type = Column(SQLEnum(CropType), nullable=False)

    # Nutritional information (per 100g)
    calories_per_100g = Column(Float)
    protein_g = Column(Float)
    carbs_g = Column(Float)
    fat_g = Column(Float)
    fiber_g = Column(Float)

    # Storage
    shelf_life_days = Column(Integer)
    requires_cold_chain = Column(Boolean, default=False)
    optimal_storage_temp_c = Column(Float)

    # Growing conditions
    growing_season = Column(SQLEnum(SeasonType))
    days_to_harvest = Column(Integer)
    water_requirement_mm = Column(Float)  # mm per growing season
    min_temp_c = Column(Float)
    max_temp_c = Column(Float)

    # Yield information
    avg_yield_kg_per_hectare = Column(Float)

    is_active = Column(Boolean, default=True)

    # Relationships
    productions = relationship("AgriculturalProduction", back_populates="crop")
    forecasts = relationship("HarvestForecast", back_populates="crop")


class AgriculturalProduction(Base):
    """Agricultural production records."""

    __tablename__ = "agricultural_production"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)

    # Production data
    year = Column(Integer, nullable=False)
    season = Column(SQLEnum(SeasonType))
    planted_area_hectares = Column(Float)
    harvested_area_hectares = Column(Float)
    production_tonnes = Column(Float)
    yield_kg_per_hectare = Column(Float)

    # Quality metrics
    loss_percentage = Column(Float)  # Post-harvest losses
    quality_grade = Column(String(10))  # A, B, C grades

    # Labor
    workers_employed = Column(Integer)
    labor_availability_index = Column(Float)  # 0-1

    # Inputs
    fertilizer_usage_kg_per_ha = Column(Float)
    pesticide_usage_kg_per_ha = Column(Float)
    irrigation_percentage = Column(Float)

    # Weather impact
    weather_impact_score = Column(Float)  # -1 to 1 (negative = adverse)
    drought_affected = Column(Boolean, default=False)
    flood_affected = Column(Boolean, default=False)

    data_source = Column(String(100))
    notes = Column(Text)

    # Relationships
    region = relationship("Region", back_populates="productions")
    crop = relationship("Crop", back_populates="productions")

    __table_args__ = (
        Index("idx_production_region_year", "region_id", "year"),
        Index("idx_production_crop_year", "crop_id", "year"),
    )


class HarvestForecast(Base):
    """Harvest yield forecasts generated by AI models."""

    __tablename__ = "harvest_forecasts"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)

    # Forecast details
    forecast_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    target_date = Column(DateTime, nullable=False)  # Expected harvest date
    forecast_horizon_days = Column(Integer)

    # Predictions
    predicted_yield_tonnes = Column(Float, nullable=False)
    predicted_yield_lower = Column(Float)  # Lower confidence bound
    predicted_yield_upper = Column(Float)  # Upper confidence bound
    confidence_score = Column(Float)  # 0-1

    # Comparison to baseline
    baseline_yield_tonnes = Column(Float)
    deviation_percentage = Column(Float)  # vs historical average

    # Risk factors
    weather_risk = Column(Float)  # 0-1
    labor_risk = Column(Float)  # 0-1
    input_supply_risk = Column(Float)  # 0-1
    overall_risk = Column(Float)  # 0-1

    # Model info
    model_name = Column(String(100))
    model_version = Column(String(50))
    features_used = Column(JSON)

    is_active = Column(Boolean, default=True)

    # Relationships
    region = relationship("Region")
    crop = relationship("Crop", back_populates="forecasts")

    __table_args__ = (
        Index("idx_forecast_region_crop", "region_id", "crop_id"),
        Index("idx_forecast_target_date", "target_date"),
    )


class WeatherData(Base):
    """Weather data for agricultural monitoring."""

    __tablename__ = "weather_data"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    recorded_at = Column(DateTime, nullable=False)

    # Temperature
    temperature_c = Column(Float)
    temperature_min_c = Column(Float)
    temperature_max_c = Column(Float)
    feels_like_c = Column(Float)

    # Precipitation
    rainfall_mm = Column(Float)
    humidity_percentage = Column(Float)

    # Wind
    wind_speed_kmh = Column(Float)
    wind_direction = Column(String(10))

    # Other
    cloud_cover_percentage = Column(Float)
    uv_index = Column(Float)
    pressure_hpa = Column(Float)

    # Extreme events
    is_drought = Column(Boolean, default=False)
    is_flood = Column(Boolean, default=False)
    is_frost = Column(Boolean, default=False)
    is_heatwave = Column(Boolean, default=False)

    data_source = Column(String(100))

    # Relationships
    region = relationship("Region")

    __table_args__ = (
        Index("idx_weather_region_date", "region_id", "recorded_at"),
    )


class CropHealthIndicator(Base):
    """Crop health indicators from satellite imagery."""

    __tablename__ = "crop_health_indicators"

    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    recorded_at = Column(DateTime, nullable=False)

    # Vegetation indices
    ndvi = Column(Float)  # Normalized Difference Vegetation Index (-1 to 1)
    evi = Column(Float)   # Enhanced Vegetation Index
    lai = Column(Float)   # Leaf Area Index
    ndwi = Column(Float)  # Normalized Difference Water Index

    # Health metrics
    crop_stress_index = Column(Float)  # 0-1 (1 = high stress)
    disease_risk = Column(Float)  # 0-1
    pest_risk = Column(Float)  # 0-1

    # Coverage
    vegetation_coverage_percentage = Column(Float)
    crop_area_hectares = Column(Float)

    # Satellite data
    satellite_name = Column(String(50))
    image_quality = Column(Float)  # 0-1
    cloud_coverage_percentage = Column(Float)

    data_source = Column(String(100))

    # Relationships
    region = relationship("Region")

    __table_args__ = (
        Index("idx_crop_health_region_date", "region_id", "recorded_at"),
    )

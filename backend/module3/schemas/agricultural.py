"""
Agricultural production schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .common import BaseSchema, GeoLocation, TimestampMixin, NutritionalInfo, RiskScore


class CropType(str, Enum):
    STAPLE_GRAIN = "staple_grain"
    PROTEIN = "protein"
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    LEGUME = "legume"
    TUBER = "tuber"
    OIL_SEED = "oil_seed"
    OTHER = "other"


class SeasonType(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    WET = "wet"
    DRY = "dry"
    YEAR_ROUND = "year_round"


# Region Schemas
class RegionBase(BaseModel):
    name: str = Field(..., max_length=255)
    country: str = Field(..., max_length=100)
    region_code: str = Field(..., max_length=50)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    area_sq_km: Optional[float] = None
    population: Optional[int] = None
    climate_zone: Optional[str] = None


class RegionCreate(RegionBase):
    geometry: Optional[Dict[str, Any]] = None
    population_density: Optional[float] = None
    urban_percentage: Optional[float] = None
    arable_land_sq_km: Optional[float] = None
    irrigation_coverage: Optional[float] = None
    agricultural_workforce: Optional[int] = None
    drought_risk: Optional[float] = Field(None, ge=0, le=1)
    flood_risk: Optional[float] = Field(None, ge=0, le=1)


class RegionUpdate(BaseModel):
    name: Optional[str] = None
    population: Optional[int] = None
    population_density: Optional[float] = None
    arable_land_sq_km: Optional[float] = None
    drought_risk: Optional[float] = Field(None, ge=0, le=1)
    flood_risk: Optional[float] = Field(None, ge=0, le=1)


class RegionResponse(RegionBase, TimestampMixin, BaseSchema):
    id: int
    population_density: Optional[float] = None
    urban_percentage: Optional[float] = None
    arable_land_sq_km: Optional[float] = None
    drought_risk: Optional[float] = None
    flood_risk: Optional[float] = None
    is_active: bool = True


class RegionSummary(BaseSchema):
    id: int
    name: str
    country: str
    region_code: str
    population: Optional[int] = None


# Crop Schemas
class CropBase(BaseModel):
    name: str = Field(..., max_length=100)
    scientific_name: Optional[str] = None
    crop_type: CropType


class CropCreate(CropBase):
    calories_per_100g: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    shelf_life_days: Optional[int] = None
    requires_cold_chain: bool = False
    growing_season: Optional[SeasonType] = None
    days_to_harvest: Optional[int] = None
    avg_yield_kg_per_hectare: Optional[float] = None


class CropResponse(CropBase, TimestampMixin, BaseSchema):
    id: int
    calories_per_100g: Optional[float] = None
    protein_g: Optional[float] = None
    shelf_life_days: Optional[int] = None
    requires_cold_chain: bool = False
    growing_season: Optional[SeasonType] = None
    avg_yield_kg_per_hectare: Optional[float] = None
    is_active: bool = True


# Agricultural Production Schemas
class ProductionBase(BaseModel):
    region_id: int
    crop_id: int
    year: int = Field(..., ge=2000, le=2100)
    season: Optional[SeasonType] = None


class ProductionCreate(ProductionBase):
    planted_area_hectares: Optional[float] = None
    harvested_area_hectares: Optional[float] = None
    production_tonnes: Optional[float] = None
    yield_kg_per_hectare: Optional[float] = None
    loss_percentage: Optional[float] = Field(None, ge=0, le=100)
    workers_employed: Optional[int] = None
    drought_affected: bool = False
    flood_affected: bool = False
    data_source: Optional[str] = None


class ProductionUpdate(BaseModel):
    production_tonnes: Optional[float] = None
    yield_kg_per_hectare: Optional[float] = None
    loss_percentage: Optional[float] = Field(None, ge=0, le=100)
    weather_impact_score: Optional[float] = Field(None, ge=-1, le=1)


class ProductionResponse(ProductionBase, TimestampMixin, BaseSchema):
    id: int
    planted_area_hectares: Optional[float] = None
    harvested_area_hectares: Optional[float] = None
    production_tonnes: Optional[float] = None
    yield_kg_per_hectare: Optional[float] = None
    loss_percentage: Optional[float] = None
    drought_affected: bool = False
    flood_affected: bool = False


class ProductionSummary(BaseSchema):
    region_id: int
    region_name: str
    total_production_tonnes: float
    total_area_hectares: float
    avg_yield: float
    year: int


# Harvest Forecast Schemas
class HarvestForecastCreate(BaseModel):
    region_id: int
    crop_id: int
    target_date: datetime
    predicted_yield_tonnes: float
    predicted_yield_lower: Optional[float] = None
    predicted_yield_upper: Optional[float] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    weather_risk: Optional[float] = Field(None, ge=0, le=1)
    labor_risk: Optional[float] = Field(None, ge=0, le=1)
    model_name: Optional[str] = None


class HarvestForecastResponse(BaseSchema, TimestampMixin):
    id: int
    region_id: int
    crop_id: int
    forecast_date: datetime
    target_date: datetime
    predicted_yield_tonnes: float
    predicted_yield_lower: Optional[float] = None
    predicted_yield_upper: Optional[float] = None
    confidence_score: Optional[float] = None
    baseline_yield_tonnes: Optional[float] = None
    deviation_percentage: Optional[float] = None
    overall_risk: Optional[float] = None


class ForecastSummary(BaseSchema):
    region_id: int
    region_name: str
    crop_id: int
    crop_name: str
    predicted_yield_tonnes: float
    deviation_percentage: float
    risk_level: str


# Weather Data Schemas
class WeatherDataCreate(BaseModel):
    region_id: int
    recorded_at: datetime
    temperature_c: Optional[float] = None
    temperature_min_c: Optional[float] = None
    temperature_max_c: Optional[float] = None
    rainfall_mm: Optional[float] = None
    humidity_percentage: Optional[float] = Field(None, ge=0, le=100)
    wind_speed_kmh: Optional[float] = None
    is_drought: bool = False
    is_flood: bool = False
    is_frost: bool = False
    is_heatwave: bool = False


class WeatherDataResponse(BaseSchema):
    id: int
    region_id: int
    recorded_at: datetime
    temperature_c: Optional[float] = None
    rainfall_mm: Optional[float] = None
    humidity_percentage: Optional[float] = None
    is_drought: bool = False
    is_flood: bool = False


class WeatherSummary(BaseSchema):
    region_id: int
    period_start: datetime
    period_end: datetime
    avg_temperature_c: float
    total_rainfall_mm: float
    drought_days: int
    flood_days: int


# Crop Health Schemas
class CropHealthCreate(BaseModel):
    region_id: int
    recorded_at: datetime
    ndvi: Optional[float] = Field(None, ge=-1, le=1)
    evi: Optional[float] = None
    crop_stress_index: Optional[float] = Field(None, ge=0, le=1)
    disease_risk: Optional[float] = Field(None, ge=0, le=1)
    vegetation_coverage_percentage: Optional[float] = Field(None, ge=0, le=100)


class CropHealthResponse(BaseSchema):
    id: int
    region_id: int
    recorded_at: datetime
    ndvi: Optional[float] = None
    crop_stress_index: Optional[float] = None
    disease_risk: Optional[float] = None
    vegetation_coverage_percentage: Optional[float] = None


# Aggregation Schemas
class RegionalProductionAnalysis(BaseSchema):
    region_id: int
    region_name: str
    total_production_tonnes: float
    production_by_crop: Dict[str, float]
    year_over_year_change: float
    forecast_deviation: float
    risk_factors: List[str]


class CropProductionTrend(BaseSchema):
    crop_id: int
    crop_name: str
    historical_production: List[Dict[str, Any]]
    forecast: List[Dict[str, Any]]
    trend_direction: str
    seasonal_pattern: Optional[Dict[str, float]] = None

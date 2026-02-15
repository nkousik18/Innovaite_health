"""
Food inventory and consumption schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .common import BaseSchema, TimestampMixin


class FoodCategoryType(str, Enum):
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


class StorageType(str, Enum):
    AMBIENT = "ambient"
    REFRIGERATED = "refrigerated"
    FROZEN = "frozen"
    CONTROLLED = "controlled"


class StockStatus(str, Enum):
    CRITICAL = "critical"
    LOW = "low"
    ADEQUATE = "adequate"
    SURPLUS = "surplus"


# Food Category Schemas
class FoodCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    category_type: FoodCategoryType


class FoodCategoryCreate(FoodCategoryBase):
    description: Optional[str] = None
    storage_type: StorageType = StorageType.AMBIENT
    min_storage_temp_c: Optional[float] = None
    max_storage_temp_c: Optional[float] = None
    avg_shelf_life_days: Optional[int] = None
    caloric_density: Optional[float] = None
    nutritional_priority: Optional[int] = None
    daily_per_capita_kg: Optional[float] = None
    minimum_per_capita_kg: Optional[float] = None


class FoodCategoryResponse(FoodCategoryBase, TimestampMixin, BaseSchema):
    id: int
    description: Optional[str] = None
    storage_type: StorageType
    avg_shelf_life_days: Optional[int] = None
    caloric_density: Optional[float] = None
    daily_per_capita_kg: Optional[float] = None
    is_active: bool = True


# Food Inventory Schemas
class InventoryBase(BaseModel):
    region_id: int
    category_id: int


class InventoryCreate(InventoryBase):
    quantity_tonnes: float = Field(..., ge=0)
    consumption_rate_tonnes_per_day: Optional[float] = None
    minimum_stock_tonnes: Optional[float] = None
    target_stock_tonnes: Optional[float] = None
    local_production_tonnes: Optional[float] = None
    imported_tonnes: Optional[float] = None
    data_source: Optional[str] = None


class InventoryUpdate(BaseModel):
    quantity_tonnes: Optional[float] = Field(None, ge=0)
    quantity_change_tonnes: Optional[float] = None
    consumption_rate_tonnes_per_day: Optional[float] = None
    expiring_soon_tonnes: Optional[float] = None


class InventoryResponse(InventoryBase, TimestampMixin, BaseSchema):
    id: int
    recorded_at: datetime
    quantity_tonnes: float
    days_of_supply: Optional[float] = None
    consumption_rate_tonnes_per_day: Optional[float] = None
    stock_status: Optional[str] = None
    reorder_triggered: bool = False
    avg_days_to_expiry: Optional[float] = None


class InventorySummary(BaseSchema):
    region_id: int
    region_name: str
    total_inventory_tonnes: float
    days_of_supply: float
    stock_status: str
    categories_critical: int
    categories_low: int


class InventoryByCategory(BaseSchema):
    category_id: int
    category_name: str
    quantity_tonnes: float
    days_of_supply: float
    stock_status: str
    trend: str


# Warehouse Stock Schemas
class WarehouseStockCreate(BaseModel):
    distribution_center_id: int
    category_id: int
    quantity_tonnes: float = Field(..., ge=0)
    quantity_units: Optional[int] = None
    storage_zone: Optional[str] = None
    current_temp_c: Optional[float] = None


class WarehouseStockUpdate(BaseModel):
    quantity_tonnes: Optional[float] = Field(None, ge=0)
    inbound_today_tonnes: Optional[float] = None
    outbound_today_tonnes: Optional[float] = None
    current_temp_c: Optional[float] = None
    quality_hold: Optional[bool] = None
    quality_hold_reason: Optional[str] = None


class WarehouseStockResponse(BaseSchema, TimestampMixin):
    id: int
    distribution_center_id: int
    category_id: int
    recorded_at: datetime
    quantity_tonnes: float
    storage_zone: Optional[str] = None
    current_temp_c: Optional[float] = None
    temp_in_range: bool = True
    stock_status: Optional[str] = None
    quality_hold: bool = False


# Consumption Pattern Schemas
class ConsumptionPatternCreate(BaseModel):
    region_id: int
    category_id: int
    period_start: datetime
    period_end: datetime
    period_type: str = Field(..., pattern="^(daily|weekly|monthly)$")
    total_consumption_tonnes: float
    per_capita_kg: Optional[float] = None
    households_covered: Optional[int] = None


class ConsumptionPatternResponse(BaseSchema, TimestampMixin):
    id: int
    region_id: int
    category_id: int
    period_start: datetime
    period_end: datetime
    period_type: str
    total_consumption_tonnes: float
    per_capita_kg: Optional[float] = None
    consumption_trend: Optional[str] = None
    anomaly_detected: bool = False
    anomaly_score: Optional[float] = None


class ConsumptionAnalysis(BaseSchema):
    region_id: int
    category_id: int
    period: str
    total_consumption: float
    avg_daily_consumption: float
    trend: str
    trend_percentage: float
    anomalies_detected: int
    panic_buying_risk: float


# Aggregation Schemas
class RegionalInventoryStatus(BaseSchema):
    region_id: int
    region_name: str
    population: int
    inventory_status: Dict[str, InventoryByCategory]
    overall_days_supply: float
    overall_status: str
    alerts: List[str]


class InventoryForecast(BaseSchema):
    region_id: int
    category_id: int
    current_inventory: float
    forecast_days: List[Dict[str, Any]]
    projected_stockout_date: Optional[datetime] = None
    recommended_reorder_date: Optional[datetime] = None
    recommended_reorder_quantity: Optional[float] = None


class ExpiryReport(BaseSchema):
    region_id: int
    distribution_center_id: Optional[int] = None
    expiring_within_7_days: List[Dict[str, Any]]
    expiring_within_30_days: List[Dict[str, Any]]
    total_at_risk_tonnes: float
    recommended_actions: List[str]

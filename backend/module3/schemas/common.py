"""
Common schema definitions used across the module.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GeoLocation(BaseModel):
    """Geographic location."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class GeoPolygon(BaseModel):
    """GeoJSON polygon."""
    type: str = "Polygon"
    coordinates: List[List[List[float]]]


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatusResponse(BaseModel):
    """Generic status response."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    cache: str
    timestamp: datetime


class DateRangeFilter(BaseModel):
    """Date range filter."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class RiskScore(BaseModel):
    """Risk score with breakdown."""
    overall: float = Field(..., ge=0, le=1)
    climate: Optional[float] = Field(None, ge=0, le=1)
    logistics: Optional[float] = Field(None, ge=0, le=1)
    economic: Optional[float] = Field(None, ge=0, le=1)
    political: Optional[float] = Field(None, ge=0, le=1)
    infrastructure: Optional[float] = Field(None, ge=0, le=1)


class NutritionalInfo(BaseModel):
    """Nutritional information per 100g."""
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None


class TimeSeriesPoint(BaseModel):
    """Single point in a time series."""
    timestamp: datetime
    value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class TimeSeriesData(BaseModel):
    """Time series data."""
    metric_name: str
    unit: str
    data_points: List[TimeSeriesPoint]


class SummaryStatistics(BaseModel):
    """Summary statistics."""
    count: int
    min: float
    max: float
    mean: float
    median: float
    std_dev: Optional[float] = None
    sum: Optional[float] = None

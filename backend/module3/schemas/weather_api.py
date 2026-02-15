"""
Schemas for live weather fetching via OpenWeatherMap API.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from .common import BaseSchema


class LiveWeatherResponse(BaseSchema):
    """Response from fetching live weather for a region."""
    region_id: int
    region_name: str
    temperature_c: Optional[float] = None
    temperature_min_c: Optional[float] = None
    temperature_max_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    humidity_percentage: Optional[float] = None
    rainfall_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction: Optional[str] = None
    cloud_cover_percentage: Optional[float] = None
    pressure_hpa: Optional[float] = None
    description: str = ""
    is_drought: bool = False
    is_flood: bool = False
    is_frost: bool = False
    is_heatwave: bool = False
    saved_to_db: bool = False
    weather_record_id: Optional[int] = None
    fetched_at: datetime


class ForecastEntry(BaseSchema):
    """Single forecast time-step entry."""
    datetime_utc: str
    temperature_c: Optional[float] = None
    temperature_min_c: Optional[float] = None
    temperature_max_c: Optional[float] = None
    humidity_percentage: Optional[float] = None
    rainfall_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    description: str = ""
    icon: str = ""


class WeatherForecastResponse(BaseSchema):
    """5-day / 3-hour forecast response for a region."""
    region_id: int
    region_name: str
    entries: List[ForecastEntry]
    fetched_at: datetime

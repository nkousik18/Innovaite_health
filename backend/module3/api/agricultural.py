"""
Agricultural Production API Routes
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.agricultural import CropType, SeasonType
from services.agricultural_service import AgriculturalMonitoringService
from schemas.agricultural import (
    RegionCreate, RegionUpdate, RegionResponse, RegionSummary,
    CropCreate, CropResponse,
    ProductionCreate, ProductionUpdate, ProductionResponse,
    HarvestForecastCreate, HarvestForecastResponse,
    WeatherDataCreate, WeatherDataResponse,
    CropHealthCreate, CropHealthResponse
)
from schemas.weather_api import LiveWeatherResponse, WeatherForecastResponse
from schemas.common import PaginatedResponse, StatusResponse

router = APIRouter()


# ==================== Regions ====================

@router.post("/regions", response_model=RegionResponse)
async def create_region(
    data: RegionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new region."""
    service = AgriculturalMonitoringService(db)
    region = await service.create_region(data)
    return region


@router.get("/regions", response_model=PaginatedResponse[RegionResponse])
async def list_regions(
    country: Optional[str] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all regions with optional filtering."""
    service = AgriculturalMonitoringService(db)
    offset = (page - 1) * page_size
    regions, total = await service.list_regions(
        country=country,
        is_active=is_active,
        limit=page_size,
        offset=offset
    )
    return PaginatedResponse(
        items=regions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/regions/{region_id}", response_model=RegionResponse)
async def get_region(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific region."""
    service = AgriculturalMonitoringService(db)
    region = await service.get_region(region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return region


@router.patch("/regions/{region_id}", response_model=RegionResponse)
async def update_region(
    region_id: int,
    data: RegionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a region."""
    service = AgriculturalMonitoringService(db)
    region = await service.update_region(region_id, data)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return region


# ==================== Crops ====================

@router.post("/crops", response_model=CropResponse)
async def create_crop(
    data: CropCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new crop definition."""
    service = AgriculturalMonitoringService(db)
    crop = await service.create_crop(data)
    return crop


@router.get("/crops", response_model=List[CropResponse])
async def list_crops(
    crop_type: Optional[CropType] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List all crops."""
    service = AgriculturalMonitoringService(db)
    crops = await service.list_crops(crop_type=crop_type, is_active=is_active)
    return crops


@router.get("/crops/{crop_id}", response_model=CropResponse)
async def get_crop(
    crop_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific crop."""
    service = AgriculturalMonitoringService(db)
    crop = await service.get_crop(crop_id)
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    return crop


# ==================== Production ====================

@router.post("/production", response_model=ProductionResponse)
async def record_production(
    data: ProductionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record agricultural production data."""
    service = AgriculturalMonitoringService(db)
    production = await service.record_production(data)
    return production


@router.get("/production/{region_id}", response_model=List[ProductionResponse])
async def get_production(
    region_id: int,
    crop_id: Optional[int] = None,
    year: Optional[int] = None,
    season: Optional[SeasonType] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get production records for a region."""
    service = AgriculturalMonitoringService(db)
    productions = await service.get_production(
        region_id=region_id,
        crop_id=crop_id,
        year=year,
        season=season
    )
    return productions


@router.get("/production/{region_id}/summary")
async def get_production_summary(
    region_id: int,
    year: int = Query(..., ge=2000, le=2100),
    db: AsyncSession = Depends(get_db)
):
    """Get production summary for a region and year."""
    service = AgriculturalMonitoringService(db)
    summary = await service.get_regional_production_summary(region_id, year)
    return summary


# ==================== Harvest Forecasts ====================

@router.post("/forecasts", response_model=HarvestForecastResponse)
async def create_forecast(
    data: HarvestForecastCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a harvest forecast."""
    service = AgriculturalMonitoringService(db)
    forecast = await service.create_harvest_forecast(data)
    return forecast


@router.get("/forecasts", response_model=List[HarvestForecastResponse])
async def list_forecasts(
    region_id: Optional[int] = None,
    crop_id: Optional[int] = None,
    target_date_from: Optional[datetime] = None,
    target_date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """List harvest forecasts."""
    service = AgriculturalMonitoringService(db)
    forecasts = await service.get_forecasts(
        region_id=region_id,
        crop_id=crop_id,
        target_date_from=target_date_from,
        target_date_to=target_date_to
    )
    return forecasts


@router.post("/forecasts/generate/{region_id}/{crop_id}", response_model=HarvestForecastResponse)
async def generate_forecast(
    region_id: int,
    crop_id: int,
    horizon_days: int = Query(90, ge=30, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-based production forecast."""
    service = AgriculturalMonitoringService(db)
    try:
        forecast = await service.generate_production_forecast(
            region_id=region_id,
            crop_id=crop_id,
            horizon_days=horizon_days
        )
        return forecast
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Weather Data ====================

@router.post("/weather", response_model=WeatherDataResponse)
async def record_weather(
    data: WeatherDataCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record weather data."""
    service = AgriculturalMonitoringService(db)
    weather = await service.record_weather_data(data)
    return weather


@router.get("/weather/{region_id}", response_model=List[WeatherDataResponse])
async def get_weather(
    region_id: int,
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get weather data for a region."""
    service = AgriculturalMonitoringService(db)
    weather = await service.get_weather_data(region_id=region_id, days_back=days_back)
    return weather


@router.get("/weather/{region_id}/summary")
async def get_weather_summary(
    region_id: int,
    start_date: datetime,
    end_date: datetime,
    db: AsyncSession = Depends(get_db)
):
    """Get weather summary for a region and period."""
    service = AgriculturalMonitoringService(db)
    summary = await service.get_weather_summary(region_id, start_date, end_date)
    return summary


@router.post("/weather/{region_id}/fetch", response_model=LiveWeatherResponse)
async def fetch_live_weather(
    region_id: int,
    save_to_db: bool = Query(True, description="Save fetched weather to database"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch current weather from OpenWeatherMap API and optionally save to DB."""
    service = AgriculturalMonitoringService(db)
    try:
        result = await service.fetch_live_weather(region_id, save_to_db=save_to_db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/weather/{region_id}/forecast", response_model=WeatherForecastResponse)
async def get_weather_forecast(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get 5-day / 3-hour weather forecast from OpenWeatherMap API."""
    service = AgriculturalMonitoringService(db)
    try:
        result = await service.fetch_weather_forecast(region_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Crop Health ====================

@router.post("/crop-health", response_model=CropHealthResponse)
async def record_crop_health(
    data: CropHealthCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record crop health indicator data."""
    service = AgriculturalMonitoringService(db)
    health = await service.record_crop_health(data)
    return health


@router.get("/crop-health/{region_id}", response_model=List[CropHealthResponse])
async def get_crop_health(
    region_id: int,
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get crop health data for a region."""
    service = AgriculturalMonitoringService(db)
    health = await service.get_crop_health(region_id=region_id, days_back=days_back)
    return health


@router.get("/crop-health/{region_id}/analysis")
async def analyze_crop_health(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Analyze current crop health status."""
    service = AgriculturalMonitoringService(db)
    analysis = await service.analyze_crop_health(region_id)
    return analysis

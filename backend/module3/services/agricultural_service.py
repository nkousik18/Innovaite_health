"""
Agricultural Production Monitoring Service

Handles:
- Crop production tracking
- Harvest forecasting using AI/ML
- Weather data integration
- Crop health monitoring via satellite imagery
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from models.agricultural import (
    Region, Crop, AgriculturalProduction, HarvestForecast,
    WeatherData, CropHealthIndicator, CropType, SeasonType
)
from schemas.agricultural import (
    RegionCreate, RegionUpdate, RegionResponse,
    CropCreate, CropResponse,
    ProductionCreate, ProductionUpdate, ProductionResponse,
    HarvestForecastCreate, HarvestForecastResponse,
    WeatherDataCreate, WeatherDataResponse,
    CropHealthCreate, CropHealthResponse,
    RegionalProductionAnalysis, CropProductionTrend
)
from schemas.weather_api import LiveWeatherResponse, WeatherForecastResponse, ForecastEntry
from services.weather_api_service import WeatherAPIService
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AgriculturalMonitoringService:
    """Service for agricultural production monitoring and forecasting."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Region Management ====================

    async def create_region(self, data: RegionCreate) -> Region:
        """Create a new region."""
        region = Region(**data.model_dump())
        self.db.add(region)
        await self.db.flush()
        await self.db.refresh(region)
        logger.info(f"Created region: {region.name} ({region.region_code})")
        return region

    async def get_region(self, region_id: int) -> Optional[Region]:
        """Get region by ID."""
        result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        return result.scalar_one_or_none()

    async def get_region_by_code(self, region_code: str) -> Optional[Region]:
        """Get region by code."""
        result = await self.db.execute(
            select(Region).where(Region.region_code == region_code)
        )
        return result.scalar_one_or_none()

    async def list_regions(
        self,
        country: Optional[str] = None,
        is_active: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Region], int]:
        """List regions with optional filtering."""
        query = select(Region).where(Region.is_active == is_active)

        if country:
            query = query.where(Region.country == country)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        # Get paginated results
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        regions = result.scalars().all()

        return list(regions), total

    async def update_region(self, region_id: int, data: RegionUpdate) -> Optional[Region]:
        """Update region."""
        region = await self.get_region(region_id)
        if not region:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(region, field, value)

        await self.db.flush()
        await self.db.refresh(region)
        return region

    # ==================== Crop Management ====================

    async def create_crop(self, data: CropCreate) -> Crop:
        """Create a new crop definition."""
        crop = Crop(**data.model_dump())
        self.db.add(crop)
        await self.db.flush()
        await self.db.refresh(crop)
        logger.info(f"Created crop: {crop.name}")
        return crop

    async def get_crop(self, crop_id: int) -> Optional[Crop]:
        """Get crop by ID."""
        result = await self.db.execute(
            select(Crop).where(Crop.id == crop_id)
        )
        return result.scalar_one_or_none()

    async def list_crops(
        self,
        crop_type: Optional[CropType] = None,
        is_active: bool = True
    ) -> List[Crop]:
        """List all crops with optional type filter."""
        query = select(Crop).where(Crop.is_active == is_active)

        if crop_type:
            query = query.where(Crop.crop_type == crop_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Production Tracking ====================

    async def record_production(self, data: ProductionCreate) -> AgriculturalProduction:
        """Record agricultural production data."""
        # Calculate yield if not provided
        production_data = data.model_dump()
        if (data.production_tonnes and data.harvested_area_hectares
                and not data.yield_kg_per_hectare):
            production_data["yield_kg_per_hectare"] = (
                data.production_tonnes * 1000 / data.harvested_area_hectares
            )

        production = AgriculturalProduction(**production_data)
        self.db.add(production)
        await self.db.flush()
        await self.db.refresh(production)

        logger.info(
            f"Recorded production: Region {data.region_id}, "
            f"Crop {data.crop_id}, Year {data.year}"
        )
        return production

    async def get_production(
        self,
        region_id: int,
        crop_id: Optional[int] = None,
        year: Optional[int] = None,
        season: Optional[SeasonType] = None
    ) -> List[AgriculturalProduction]:
        """Get production records with filters."""
        query = select(AgriculturalProduction).where(
            AgriculturalProduction.region_id == region_id
        )

        if crop_id:
            query = query.where(AgriculturalProduction.crop_id == crop_id)
        if year:
            query = query.where(AgriculturalProduction.year == year)
        if season:
            query = query.where(AgriculturalProduction.season == season)

        query = query.order_by(AgriculturalProduction.year.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_regional_production_summary(
        self,
        region_id: int,
        year: int
    ) -> Dict[str, Any]:
        """Get production summary for a region and year."""
        query = select(
            AgriculturalProduction.crop_id,
            Crop.name.label("crop_name"),
            func.sum(AgriculturalProduction.production_tonnes).label("total_production"),
            func.sum(AgriculturalProduction.harvested_area_hectares).label("total_area"),
            func.avg(AgriculturalProduction.yield_kg_per_hectare).label("avg_yield")
        ).join(
            Crop, AgriculturalProduction.crop_id == Crop.id
        ).where(
            and_(
                AgriculturalProduction.region_id == region_id,
                AgriculturalProduction.year == year
            )
        ).group_by(
            AgriculturalProduction.crop_id, Crop.name
        )

        result = await self.db.execute(query)
        rows = result.all()

        production_by_crop = {}
        total_production = 0
        total_area = 0

        for row in rows:
            production_by_crop[row.crop_name] = {
                "production_tonnes": float(row.total_production or 0),
                "area_hectares": float(row.total_area or 0),
                "avg_yield_kg_per_ha": float(row.avg_yield or 0)
            }
            total_production += float(row.total_production or 0)
            total_area += float(row.total_area or 0)

        return {
            "region_id": region_id,
            "year": year,
            "total_production_tonnes": total_production,
            "total_area_hectares": total_area,
            "production_by_crop": production_by_crop
        }

    # ==================== Harvest Forecasting ====================

    async def create_harvest_forecast(
        self,
        data: HarvestForecastCreate
    ) -> HarvestForecast:
        """Create a harvest forecast."""
        # Calculate baseline and deviation
        historical = await self._get_historical_average(
            data.region_id, data.crop_id, years=5
        )

        forecast_data = data.model_dump()
        forecast_data["baseline_yield_tonnes"] = historical
        if historical > 0:
            forecast_data["deviation_percentage"] = (
                (data.predicted_yield_tonnes - historical) / historical * 100
            )

        # Calculate overall risk
        risks = [
            data.weather_risk or 0,
            data.labor_risk or 0,
        ]
        forecast_data["overall_risk"] = np.mean([r for r in risks if r > 0]) if any(risks) else 0

        # Calculate forecast horizon
        forecast_data["forecast_horizon_days"] = (
            data.target_date - datetime.utcnow()
        ).days

        forecast = HarvestForecast(**forecast_data)
        self.db.add(forecast)
        await self.db.flush()
        await self.db.refresh(forecast)

        logger.info(
            f"Created forecast: Region {data.region_id}, "
            f"Crop {data.crop_id}, Target {data.target_date}"
        )
        return forecast

    async def _get_historical_average(
        self,
        region_id: int,
        crop_id: int,
        years: int = 5
    ) -> float:
        """Get historical average production."""
        current_year = datetime.now().year
        query = select(
            func.avg(AgriculturalProduction.production_tonnes)
        ).where(
            and_(
                AgriculturalProduction.region_id == region_id,
                AgriculturalProduction.crop_id == crop_id,
                AgriculturalProduction.year >= current_year - years,
                AgriculturalProduction.year < current_year
            )
        )
        result = await self.db.execute(query)
        avg = result.scalar()
        return float(avg) if avg else 0

    async def get_forecasts(
        self,
        region_id: Optional[int] = None,
        crop_id: Optional[int] = None,
        target_date_from: Optional[datetime] = None,
        target_date_to: Optional[datetime] = None,
        is_active: bool = True
    ) -> List[HarvestForecast]:
        """Get harvest forecasts with filters."""
        query = select(HarvestForecast).where(
            HarvestForecast.is_active == is_active
        )

        if region_id:
            query = query.where(HarvestForecast.region_id == region_id)
        if crop_id:
            query = query.where(HarvestForecast.crop_id == crop_id)
        if target_date_from:
            query = query.where(HarvestForecast.target_date >= target_date_from)
        if target_date_to:
            query = query.where(HarvestForecast.target_date <= target_date_to)

        query = query.order_by(HarvestForecast.target_date)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def generate_production_forecast(
        self,
        region_id: int,
        crop_id: int,
        horizon_days: int = 90
    ) -> HarvestForecast:
        """Generate AI-based production forecast."""
        # Get historical data
        historical_data = await self.get_production(
            region_id=region_id,
            crop_id=crop_id
        )

        if len(historical_data) < 3:
            raise ValueError("Insufficient historical data for forecasting")

        # Get recent weather data
        weather_data = await self.get_weather_data(
            region_id=region_id,
            days_back=30
        )

        # Get crop health indicators
        crop_health = await self.get_crop_health(
            region_id=region_id,
            days_back=30
        )

        # Simple forecasting model (in production, use Prophet or similar)
        historical_yields = [p.production_tonnes for p in historical_data if p.production_tonnes]
        if not historical_yields:
            raise ValueError("No historical yield data available")

        base_prediction = np.mean(historical_yields)
        trend = self._calculate_trend(historical_yields)

        # Adjust for weather
        weather_factor = self._calculate_weather_factor(weather_data)

        # Adjust for crop health
        health_factor = self._calculate_health_factor(crop_health)

        # Final prediction
        predicted_yield = base_prediction * (1 + trend) * weather_factor * health_factor

        # Confidence interval
        std_dev = np.std(historical_yields) if len(historical_yields) > 1 else base_prediction * 0.1
        confidence = 0.7 if len(historical_data) > 5 else 0.5

        # Create forecast
        forecast_data = HarvestForecastCreate(
            region_id=region_id,
            crop_id=crop_id,
            target_date=datetime.utcnow() + timedelta(days=horizon_days),
            predicted_yield_tonnes=predicted_yield,
            predicted_yield_lower=predicted_yield - 1.96 * std_dev,
            predicted_yield_upper=predicted_yield + 1.96 * std_dev,
            confidence_score=confidence,
            weather_risk=1 - weather_factor if weather_factor < 1 else 0,
            model_name="simple_forecast_v1"
        )

        return await self.create_harvest_forecast(forecast_data)

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate simple linear trend."""
        if len(values) < 2:
            return 0
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        return coeffs[0] / np.mean(values) if np.mean(values) > 0 else 0

    def _calculate_weather_factor(self, weather_data: List[WeatherData]) -> float:
        """Calculate weather impact factor."""
        if not weather_data:
            return 1.0

        drought_days = sum(1 for w in weather_data if w.is_drought)
        flood_days = sum(1 for w in weather_data if w.is_flood)
        heatwave_days = sum(1 for w in weather_data if w.is_heatwave)

        total_days = len(weather_data)
        adverse_days = drought_days + flood_days + heatwave_days

        return max(0.5, 1 - (adverse_days / total_days * 0.5))

    def _calculate_health_factor(self, health_data: List[CropHealthIndicator]) -> float:
        """Calculate crop health impact factor."""
        if not health_data:
            return 1.0

        avg_ndvi = np.mean([h.ndvi for h in health_data if h.ndvi is not None])
        avg_stress = np.mean([h.crop_stress_index for h in health_data if h.crop_stress_index is not None])

        # NDVI adjustment (0.3-0.8 is typical healthy range)
        ndvi_factor = 1.0
        if avg_ndvi < 0.3:
            ndvi_factor = 0.7
        elif avg_ndvi > 0.6:
            ndvi_factor = 1.1

        # Stress adjustment
        stress_factor = 1 - (avg_stress * 0.3) if avg_stress else 1.0

        return ndvi_factor * stress_factor

    # ==================== Weather Data ====================

    async def record_weather_data(self, data: WeatherDataCreate) -> WeatherData:
        """Record weather data."""
        weather = WeatherData(**data.model_dump())
        self.db.add(weather)
        await self.db.flush()
        await self.db.refresh(weather)
        return weather

    async def get_weather_data(
        self,
        region_id: int,
        days_back: int = 30,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[WeatherData]:
        """Get weather data for a region."""
        query = select(WeatherData).where(
            WeatherData.region_id == region_id
        )

        if start_date and end_date:
            query = query.where(
                and_(
                    WeatherData.recorded_at >= start_date,
                    WeatherData.recorded_at <= end_date
                )
            )
        else:
            cutoff = datetime.utcnow() - timedelta(days=days_back)
            query = query.where(WeatherData.recorded_at >= cutoff)

        query = query.order_by(WeatherData.recorded_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_weather_summary(
        self,
        region_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get weather summary for a period."""
        weather_data = await self.get_weather_data(
            region_id=region_id,
            start_date=start_date,
            end_date=end_date
        )

        if not weather_data:
            return {"region_id": region_id, "data_available": False}

        temps = [w.temperature_c for w in weather_data if w.temperature_c is not None]
        rainfall = [w.rainfall_mm for w in weather_data if w.rainfall_mm is not None]

        return {
            "region_id": region_id,
            "period_start": start_date,
            "period_end": end_date,
            "days_recorded": len(weather_data),
            "avg_temperature_c": np.mean(temps) if temps else None,
            "min_temperature_c": min(temps) if temps else None,
            "max_temperature_c": max(temps) if temps else None,
            "total_rainfall_mm": sum(rainfall) if rainfall else None,
            "drought_days": sum(1 for w in weather_data if w.is_drought),
            "flood_days": sum(1 for w in weather_data if w.is_flood),
            "frost_days": sum(1 for w in weather_data if w.is_frost),
            "heatwave_days": sum(1 for w in weather_data if w.is_heatwave)
        }

    # ==================== Crop Health Monitoring ====================

    async def record_crop_health(self, data: CropHealthCreate) -> CropHealthIndicator:
        """Record crop health indicator data."""
        health = CropHealthIndicator(**data.model_dump())
        self.db.add(health)
        await self.db.flush()
        await self.db.refresh(health)
        return health

    async def get_crop_health(
        self,
        region_id: int,
        days_back: int = 30,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CropHealthIndicator]:
        """Get crop health data for a region."""
        query = select(CropHealthIndicator).where(
            CropHealthIndicator.region_id == region_id
        )

        if start_date and end_date:
            query = query.where(
                and_(
                    CropHealthIndicator.recorded_at >= start_date,
                    CropHealthIndicator.recorded_at <= end_date
                )
            )
        else:
            cutoff = datetime.utcnow() - timedelta(days=days_back)
            query = query.where(CropHealthIndicator.recorded_at >= cutoff)

        query = query.order_by(CropHealthIndicator.recorded_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def analyze_crop_health(self, region_id: int) -> Dict[str, Any]:
        """Analyze current crop health status."""
        recent_health = await self.get_crop_health(region_id, days_back=14)

        if not recent_health:
            return {
                "region_id": region_id,
                "status": "no_data",
                "message": "No recent crop health data available"
            }

        latest = recent_health[0]
        avg_ndvi = np.mean([h.ndvi for h in recent_health if h.ndvi is not None])
        avg_stress = np.mean([h.crop_stress_index for h in recent_health if h.crop_stress_index is not None])

        # Determine status
        if avg_ndvi < 0.2 or avg_stress > 0.7:
            status = "critical"
        elif avg_ndvi < 0.4 or avg_stress > 0.5:
            status = "stressed"
        elif avg_ndvi < 0.5 or avg_stress > 0.3:
            status = "moderate"
        else:
            status = "healthy"

        return {
            "region_id": region_id,
            "status": status,
            "latest_ndvi": latest.ndvi,
            "avg_ndvi_14d": avg_ndvi,
            "avg_stress_index": avg_stress,
            "disease_risk": latest.disease_risk,
            "pest_risk": latest.pest_risk,
            "vegetation_coverage": latest.vegetation_coverage_percentage,
            "last_updated": latest.recorded_at,
            "recommendations": self._get_health_recommendations(status, avg_stress)
        }

    def _get_health_recommendations(self, status: str, stress_level: float) -> List[str]:
        """Generate recommendations based on crop health status."""
        recommendations = []

        if status == "critical":
            recommendations.extend([
                "Immediate field inspection required",
                "Consider emergency irrigation if drought-related",
                "Assess potential yield losses"
            ])
        elif status == "stressed":
            recommendations.extend([
                "Monitor closely for further deterioration",
                "Review irrigation and fertilization schedules",
                "Check for pest or disease outbreaks"
            ])
        elif status == "moderate":
            recommendations.append("Continue regular monitoring")

        if stress_level > 0.5:
            recommendations.append("Investigate causes of crop stress")

        return recommendations

    # ==================== Live Weather (OpenWeatherMap API) ====================

    async def fetch_live_weather(
        self, region_id: int, save_to_db: bool = True
    ) -> LiveWeatherResponse:
        """
        Fetch current weather from OpenWeatherMap for a region,
        optionally saving the result to the weather_data table.
        """
        region = await self.get_region(region_id)
        if not region:
            raise ValueError(f"Region {region_id} not found")

        weather_service = WeatherAPIService()
        weather = await weather_service.get_current_weather(region.latitude, region.longitude)

        now = datetime.utcnow()

        saved_id = None
        if save_to_db:
            weather_record = WeatherDataCreate(
                region_id=region_id,
                recorded_at=now,
                temperature_c=weather.get("temperature_c"),
                temperature_min_c=weather.get("temperature_min_c"),
                temperature_max_c=weather.get("temperature_max_c"),
                rainfall_mm=weather.get("rainfall_mm"),
                humidity_percentage=weather.get("humidity_percentage"),
                wind_speed_kmh=weather.get("wind_speed_kmh"),
                is_drought=weather.get("is_drought", False),
                is_flood=weather.get("is_flood", False),
                is_frost=weather.get("is_frost", False),
                is_heatwave=weather.get("is_heatwave", False),
            )
            record = await self.record_weather_data(weather_record)
            saved_id = record.id

        return LiveWeatherResponse(
            region_id=region_id,
            region_name=region.name,
            temperature_c=weather.get("temperature_c"),
            temperature_min_c=weather.get("temperature_min_c"),
            temperature_max_c=weather.get("temperature_max_c"),
            feels_like_c=weather.get("feels_like_c"),
            humidity_percentage=weather.get("humidity_percentage"),
            rainfall_mm=weather.get("rainfall_mm"),
            wind_speed_kmh=weather.get("wind_speed_kmh"),
            wind_direction=weather.get("wind_direction"),
            cloud_cover_percentage=weather.get("cloud_cover_percentage"),
            pressure_hpa=weather.get("pressure_hpa"),
            description=weather.get("description", ""),
            is_drought=weather.get("is_drought", False),
            is_flood=weather.get("is_flood", False),
            is_frost=weather.get("is_frost", False),
            is_heatwave=weather.get("is_heatwave", False),
            saved_to_db=save_to_db and saved_id is not None,
            weather_record_id=saved_id,
            fetched_at=now,
        )

    async def fetch_weather_forecast(self, region_id: int) -> WeatherForecastResponse:
        """Fetch 5-day / 3-hour forecast from OpenWeatherMap for a region."""
        region = await self.get_region(region_id)
        if not region:
            raise ValueError(f"Region {region_id} not found")

        weather_service = WeatherAPIService()
        raw_entries = await weather_service.get_forecast(region.latitude, region.longitude)

        entries = [
            ForecastEntry(
                datetime_utc=e["datetime_utc"],
                temperature_c=e.get("temperature_c"),
                temperature_min_c=e.get("temperature_min_c"),
                temperature_max_c=e.get("temperature_max_c"),
                humidity_percentage=e.get("humidity_percentage"),
                rainfall_mm=e.get("rainfall_mm"),
                wind_speed_kmh=e.get("wind_speed_kmh"),
                description=e.get("description", ""),
                icon=e.get("icon", ""),
            )
            for e in raw_entries
        ]

        return WeatherForecastResponse(
            region_id=region_id,
            region_name=region.name,
            entries=entries,
            fetched_at=datetime.utcnow(),
        )

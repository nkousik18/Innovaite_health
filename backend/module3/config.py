"""
SENTINEL-HEALTH Module 3: Food Security & Dependency Management
Configuration Settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "SENTINEL-HEALTH Module 3: Food Security"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # API
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8023

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/sentinel_food_security",
        description="PostgreSQL connection string"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/3"
    cache_ttl: int = 3600  # 1 hour default cache TTL

    # External APIs
    weather_api_key: Optional[str] = None
    weather_api_url: str = "https://api.openweathermap.org/data/2.5"

    google_maps_api_key: Optional[str] = None
    google_maps_base_url: str = "https://maps.googleapis.com/maps/api"

    satellite_api_key: Optional[str] = None
    satellite_api_url: str = "https://api.sentinel-hub.com"

    external_api_timeout_seconds: int = 30

    # Alert Thresholds
    shortage_warning_days: int = 30  # Yellow alert
    shortage_imminent_days: int = 15  # Orange alert
    shortage_critical_days: int = 7   # Red alert

    # Prediction Settings
    forecast_horizon_days: int = 90
    production_forecast_update_hours: int = 24

    # Distribution Optimization
    max_distribution_centers: int = 100
    max_route_alternatives: int = 5

    # Food Categories
    staple_grains: list = ["rice", "wheat", "corn", "millet", "sorghum"]
    protein_sources: list = ["beef", "pork", "chicken", "fish", "legumes", "eggs"]
    produce: list = ["vegetables", "fruits"]
    shelf_stable: list = ["canned_goods", "dried_foods", "grains"]

    # Caloric Requirements (kcal/day)
    caloric_requirement_adult: int = 2000
    caloric_requirement_child: int = 1500
    caloric_requirement_elderly: int = 1800
    caloric_requirement_healthcare_worker: int = 2500

    # Module Integration
    module1_url: str = "http://localhost:8001"  # Early Warning Detection
    module2_url: str = "http://localhost:8002"  # Supply Chain Optimization

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class AlertLevels:
    """Alert level definitions."""
    NORMAL = "normal"
    WARNING = "warning"      # Yellow - Pre-Shortage
    IMMINENT = "imminent"    # Orange - Shortage Imminent
    CRITICAL = "critical"    # Red - Critical Shortage


class FoodCategories:
    """Food category constants."""
    STAPLE_GRAINS = "staple_grains"
    PROTEIN = "protein"
    PRODUCE = "produce"
    SHELF_STABLE = "shelf_stable"
    DAIRY = "dairy"
    OILS_FATS = "oils_fats"


class DistributionPriority:
    """Distribution priority levels."""
    VULNERABLE = 1      # Elderly, immunocompromised, children
    HEALTHCARE = 2      # Healthcare workers
    ESSENTIAL = 3       # Essential workers
    GENERAL = 4         # General population


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

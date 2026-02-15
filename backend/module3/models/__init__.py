"""
Database Models for Module 3: Food Security & Dependency Management
"""

from .base import Base, get_db, engine, AsyncSessionLocal
from .agricultural import (
    Region,
    Crop,
    AgriculturalProduction,
    HarvestForecast,
    WeatherData,
    CropHealthIndicator
)
from .distribution import (
    TransportationCorridor,
    DistributionCenter,
    TransportRoute,
    RouteDisruption,
    ColdChainFacility
)
from .inventory import (
    FoodInventory,
    FoodCategory,
    WarehouseStock,
    ConsumptionPattern
)
from .dependency import (
    RegionalDependency,
    ImportSource,
    FoodImport,
    VulnerabilityAssessment
)
from .alerts import (
    ShortageAlert,
    AlertHistory,
    AlertSubscription
)
from .distribution_plan import (
    DistributionPlan,
    DistributionPoint,
    RationAllocation,
    VulnerablePopulation
)
from .resilience import (
    UrbanAgricultureSite,
    CropDiversificationPlan,
    ResilienceRecommendation
)

__all__ = [
    # Base
    "Base",
    "get_db",
    "engine",
    "AsyncSessionLocal",
    # Agricultural
    "Region",
    "Crop",
    "AgriculturalProduction",
    "HarvestForecast",
    "WeatherData",
    "CropHealthIndicator",
    # Distribution
    "TransportationCorridor",
    "DistributionCenter",
    "TransportRoute",
    "RouteDisruption",
    "ColdChainFacility",
    # Inventory
    "FoodInventory",
    "FoodCategory",
    "WarehouseStock",
    "ConsumptionPattern",
    # Dependency
    "RegionalDependency",
    "ImportSource",
    "FoodImport",
    "VulnerabilityAssessment",
    # Alerts
    "ShortageAlert",
    "AlertHistory",
    "AlertSubscription",
    # Distribution Plan
    "DistributionPlan",
    "DistributionPoint",
    "RationAllocation",
    "VulnerablePopulation",
    # Resilience
    "UrbanAgricultureSite",
    "CropDiversificationPlan",
    "ResilienceRecommendation",
]

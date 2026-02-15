"""
API Routes for Module 3: Food Security & Dependency Management
"""

from fastapi import APIRouter

from .agricultural import router as agricultural_router
from .distribution import router as distribution_router
from .inventory import router as inventory_router
from .dependency import router as dependency_router
from .alerts import router as alerts_router
from .distribution_plans import router as distribution_plans_router
from .resilience import router as resilience_router
from fire_disaster import fire_disaster_router

# Main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(
    agricultural_router,
    prefix="/agricultural",
    tags=["Agricultural Production"]
)

api_router.include_router(
    distribution_router,
    prefix="/distribution",
    tags=["Distribution Network"]
)

api_router.include_router(
    inventory_router,
    prefix="/inventory",
    tags=["Food Inventory"]
)

api_router.include_router(
    dependency_router,
    prefix="/dependency",
    tags=["Food Dependency"]
)

api_router.include_router(
    alerts_router,
    prefix="/alerts",
    tags=["Shortage Alerts"]
)

api_router.include_router(
    distribution_plans_router,
    prefix="/distribution-plans",
    tags=["Distribution Plans"]
)

api_router.include_router(
    resilience_router,
    prefix="/resilience",
    tags=["Agricultural Resilience"]
)

api_router.include_router(
    fire_disaster_router,
    prefix="/fire-disaster",
    tags=["Fire Disaster Simulation"]
)

__all__ = ["api_router"]

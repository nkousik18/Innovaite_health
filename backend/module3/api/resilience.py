"""
Agricultural Resilience API Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.resilience import SiteType, ProjectStatus
from services.resilience_service import AgriculturalResilienceService
from schemas.resilience import (
    UrbanAgricultureSiteCreate, UrbanAgricultureSiteUpdate, UrbanAgricultureSiteResponse,
    CropDiversificationPlanCreate, CropDiversificationPlanUpdate, CropDiversificationPlanResponse,
    ResilienceRecommendationCreate, ResilienceRecommendationUpdate, ResilienceRecommendationResponse,
    LandConversionOpportunityCreate, LandConversionOpportunityResponse,
    ResilienceAssessment, FoodProductionPotential,
    ClimateAdaptationPlan, RegionalResilienceSummary, UrbanAgSummary
)
from schemas.common import PaginatedResponse

router = APIRouter()


# ==================== Urban Agriculture ====================

@router.post("/urban-agriculture", response_model=UrbanAgricultureSiteResponse)
async def create_urban_ag_site(
    data: UrbanAgricultureSiteCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create an urban agriculture site."""
    service = AgriculturalResilienceService(db)
    site = await service.create_urban_ag_site(data)
    return site


@router.get("/urban-agriculture", response_model=PaginatedResponse[UrbanAgricultureSiteResponse])
async def list_urban_ag_sites(
    region_id: Optional[int] = None,
    site_type: Optional[SiteType] = None,
    status: Optional[ProjectStatus] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List urban agriculture sites."""
    service = AgriculturalResilienceService(db)
    offset = (page - 1) * page_size
    sites, total = await service.list_urban_ag_sites(
        region_id=region_id,
        site_type=site_type,
        status=status,
        is_active=is_active,
        limit=page_size,
        offset=offset
    )
    return PaginatedResponse(
        items=sites,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/urban-agriculture/{site_id}", response_model=UrbanAgricultureSiteResponse)
async def get_urban_ag_site(
    site_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific urban agriculture site."""
    service = AgriculturalResilienceService(db)
    site = await service.get_urban_ag_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.patch("/urban-agriculture/{site_id}", response_model=UrbanAgricultureSiteResponse)
async def update_urban_ag_site(
    site_id: int,
    data: UrbanAgricultureSiteUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an urban agriculture site."""
    service = AgriculturalResilienceService(db)
    site = await service.update_urban_ag_site(site_id, data)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.get("/urban-agriculture/summary/{region_id}", response_model=UrbanAgSummary)
async def get_urban_ag_summary(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get urban agriculture summary for a region."""
    service = AgriculturalResilienceService(db)
    summary = await service.get_urban_ag_summary(region_id)
    return summary


# ==================== Crop Diversification ====================

@router.post("/diversification", response_model=CropDiversificationPlanResponse)
async def create_diversification_plan(
    data: CropDiversificationPlanCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a crop diversification plan."""
    service = AgriculturalResilienceService(db)
    plan = await service.create_diversification_plan(data)
    return plan


@router.get("/diversification", response_model=List[CropDiversificationPlanResponse])
async def list_diversification_plans(
    region_id: Optional[int] = None,
    status: Optional[ProjectStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """List crop diversification plans."""
    service = AgriculturalResilienceService(db)
    plans = await service.list_diversification_plans(
        region_id=region_id,
        status=status
    )
    return plans


@router.get("/diversification/{plan_id}", response_model=CropDiversificationPlanResponse)
async def get_diversification_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific diversification plan."""
    service = AgriculturalResilienceService(db)
    plan = await service.get_diversification_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/diversification/generate/{region_id}")
async def generate_diversification_recommendations(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-based crop diversification recommendations."""
    service = AgriculturalResilienceService(db)
    recommendations = await service.generate_diversification_recommendations(region_id)
    return recommendations.model_dump()


# ==================== Resilience Recommendations ====================

@router.post("/recommendations", response_model=ResilienceRecommendationResponse)
async def create_recommendation(
    data: ResilienceRecommendationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a resilience recommendation."""
    service = AgriculturalResilienceService(db)
    recommendation = await service.create_recommendation(data)
    return recommendation


@router.get("/recommendations", response_model=List[ResilienceRecommendationResponse])
async def list_recommendations(
    region_id: Optional[int] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    is_active: bool = True,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List resilience recommendations."""
    service = AgriculturalResilienceService(db)
    recommendations = await service.list_recommendations(
        region_id=region_id,
        category=category,
        status=status,
        is_active=is_active,
        limit=limit
    )
    return recommendations


@router.post("/recommendations/generate/{region_id}", response_model=List[ResilienceRecommendationResponse])
async def generate_recommendations(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-based resilience recommendations for a region."""
    service = AgriculturalResilienceService(db)
    try:
        recommendations = await service.generate_recommendations(region_id)
        return recommendations
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Land Conversion ====================

@router.post("/land-conversion", response_model=LandConversionOpportunityResponse)
async def create_land_opportunity(
    data: LandConversionOpportunityCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a land conversion opportunity."""
    service = AgriculturalResilienceService(db)
    opportunity = await service.create_land_opportunity(data)
    return opportunity


@router.get("/land-conversion", response_model=List[LandConversionOpportunityResponse])
async def list_land_opportunities(
    region_id: Optional[int] = None,
    current_use: Optional[str] = None,
    min_feasibility: Optional[float] = Query(None, ge=0, le=1),
    is_active: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List land conversion opportunities."""
    service = AgriculturalResilienceService(db)
    opportunities = await service.list_land_opportunities(
        region_id=region_id,
        current_use=current_use,
        min_feasibility=min_feasibility,
        is_active=is_active
    )
    return opportunities


# ==================== Assessments ====================

@router.get("/assessment/{region_id}", response_model=ResilienceAssessment)
async def assess_resilience(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Perform comprehensive resilience assessment for a region."""
    service = AgriculturalResilienceService(db)
    try:
        assessment = await service.assess_resilience(region_id)
        return assessment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/summary/{region_id}", response_model=RegionalResilienceSummary)
async def get_regional_summary(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get resilience summary for a region."""
    service = AgriculturalResilienceService(db)
    try:
        summary = await service.get_regional_summary(region_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

"""
Food Dependency API Routes
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.dependency import RiskLevel
from services.dependency_service import FoodDependencyService
from schemas.dependency import (
    RegionalDependencyCreate, RegionalDependencyUpdate, RegionalDependencyResponse,
    ImportSourceCreate, ImportSourceUpdate, ImportSourceResponse,
    FoodImportCreate, FoodImportUpdate, FoodImportResponse,
    VulnerabilityAssessmentCreate, VulnerabilityAssessmentResponse,
    DependencyProfile, ImportSummary, DependencyRiskAnalysis,
    ImportDisruptionScenario
)
from schemas.common import PaginatedResponse

router = APIRouter()


# ==================== Regional Dependencies ====================

@router.post("/profiles", response_model=RegionalDependencyResponse)
async def create_dependency_profile(
    data: RegionalDependencyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a regional dependency profile."""
    service = FoodDependencyService(db)
    dependency = await service.create_dependency_profile(data)
    return dependency


@router.get("/profiles", response_model=PaginatedResponse[RegionalDependencyResponse])
async def list_dependency_profiles(
    risk_level: Optional[RiskLevel] = None,
    min_risk_score: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List regional dependency profiles."""
    service = FoodDependencyService(db)
    offset = (page - 1) * page_size
    dependencies, total = await service.list_dependencies(
        risk_level=risk_level,
        min_risk_score=min_risk_score,
        limit=page_size,
        offset=offset
    )
    return PaginatedResponse(
        items=dependencies,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/profiles/{region_id}", response_model=DependencyProfile)
async def get_dependency_profile(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive dependency profile for a region."""
    service = FoodDependencyService(db)
    try:
        profile = await service.get_dependency_profile(region_id)
        return profile
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/profiles/{region_id}", response_model=RegionalDependencyResponse)
async def update_dependency_profile(
    region_id: int,
    data: RegionalDependencyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update dependency profile."""
    service = FoodDependencyService(db)
    dependency = await service.update_dependency(region_id, data)
    if not dependency:
        raise HTTPException(status_code=404, detail="Dependency profile not found")
    return dependency


# ==================== Import Sources ====================

@router.post("/import-sources", response_model=ImportSourceResponse)
async def create_import_source(
    data: ImportSourceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create an import source record."""
    service = FoodDependencyService(db)
    source = await service.create_import_source(data)
    return source


@router.get("/import-sources", response_model=List[ImportSourceResponse])
async def list_import_sources(
    dependency_id: Optional[int] = None,
    source_country: Optional[str] = None,
    food_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List import sources."""
    service = FoodDependencyService(db)
    sources = await service.list_import_sources(
        dependency_id=dependency_id,
        source_country=source_country,
        food_type=food_type
    )
    return sources


@router.patch("/import-sources/{source_id}", response_model=ImportSourceResponse)
async def update_import_source(
    source_id: int,
    data: ImportSourceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update import source."""
    service = FoodDependencyService(db)
    source = await service.update_import_source(source_id, data)
    if not source:
        raise HTTPException(status_code=404, detail="Import source not found")
    return source


# ==================== Food Imports ====================

@router.post("/imports", response_model=FoodImportResponse)
async def record_import(
    data: FoodImportCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record a food import."""
    service = FoodDependencyService(db)
    food_import = await service.record_import(data)
    return food_import


@router.get("/imports", response_model=PaginatedResponse[FoodImportResponse])
async def list_imports(
    region_id: Optional[int] = None,
    source_country: Optional[str] = None,
    food_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List food imports."""
    service = FoodDependencyService(db)
    offset = (page - 1) * page_size
    imports, total = await service.list_imports(
        region_id=region_id,
        source_country=source_country,
        food_type=food_type,
        start_date=start_date,
        end_date=end_date,
        limit=page_size,
        offset=offset
    )
    return PaginatedResponse(
        items=imports,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/imports/{region_id}/summary", response_model=ImportSummary)
async def get_import_summary(
    region_id: int,
    start_date: datetime,
    end_date: datetime,
    db: AsyncSession = Depends(get_db)
):
    """Get import summary for a region and period."""
    service = FoodDependencyService(db)
    summary = await service.get_import_summary(region_id, start_date, end_date)
    return summary


# ==================== Vulnerability Assessments ====================

@router.post("/assessments", response_model=VulnerabilityAssessmentResponse)
async def create_assessment(
    data: VulnerabilityAssessmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a vulnerability assessment."""
    service = FoodDependencyService(db)
    assessment = await service.create_assessment(data)
    return assessment


@router.get("/assessments", response_model=List[VulnerabilityAssessmentResponse])
async def list_assessments(
    region_id: Optional[int] = None,
    min_score: Optional[float] = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List vulnerability assessments."""
    service = FoodDependencyService(db)
    assessments = await service.list_assessments(
        region_id=region_id,
        min_score=min_score,
        limit=limit
    )
    return assessments


# ==================== Risk Analysis ====================

@router.get("/risk-analysis/{region_id}", response_model=DependencyRiskAnalysis)
async def analyze_dependency_risk(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Perform comprehensive dependency risk analysis."""
    service = FoodDependencyService(db)
    try:
        analysis = await service.analyze_dependency_risk(region_id)
        return analysis
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/simulate-disruption", response_model=ImportDisruptionScenario)
async def simulate_import_disruption(
    region_id: int,
    source_country: str,
    disruption_pct: float = Query(100, ge=0, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Simulate the impact of an import disruption."""
    service = FoodDependencyService(db)
    try:
        scenario = await service.simulate_import_disruption(
            region_id=region_id,
            source_country=source_country,
            disruption_pct=disruption_pct
        )
        return scenario
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

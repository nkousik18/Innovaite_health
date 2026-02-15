"""
Distribution Plans API Routes
"""

from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.distribution_plan import PlanStatus, PopulationType
from services.optimization_service import DistributionOptimizationService
from schemas.distribution_plan import (
    DistributionPlanCreate, DistributionPlanUpdate, DistributionPlanResponse,
    DistributionPointCreate, DistributionPointUpdate, DistributionPointResponse,
    RationAllocationCreate, RationAllocationResponse,
    VulnerablePopulationCreate, VulnerablePopulationResponse,
    DistributionRecordCreate, DistributionRecordResponse,
    DistributionOptimizationRequest, DistributionOptimizationResponse,
    DistributionAnalytics, CoverageAnalysis, PlanSummary
)
from schemas.common import PaginatedResponse

router = APIRouter()


# ==================== Distribution Plans ====================

@router.post("/", response_model=DistributionPlanResponse)
async def create_plan(
    data: DistributionPlanCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new distribution plan."""
    service = DistributionOptimizationService(db)
    plan = await service.create_plan(data)
    return plan


@router.get("/", response_model=PaginatedResponse[DistributionPlanResponse])
async def list_plans(
    region_id: Optional[int] = None,
    status: Optional[PlanStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """List distribution plans."""
    service = DistributionOptimizationService(db)
    offset = (page - 1) * page_size
    plans, total = await service.list_plans(
        region_id=region_id,
        status=status,
        limit=page_size,
        offset=offset
    )
    return PaginatedResponse(
        items=plans,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{plan_id}", response_model=DistributionPlanResponse)
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific distribution plan."""
    service = DistributionOptimizationService(db)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.patch("/{plan_id}", response_model=DistributionPlanResponse)
async def update_plan(
    plan_id: int,
    data: DistributionPlanUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a distribution plan."""
    service = DistributionOptimizationService(db)
    plan = await service.update_plan(plan_id, data)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/{plan_id}/approve", response_model=DistributionPlanResponse)
async def approve_plan(
    plan_id: int,
    approved_by: str,
    db: AsyncSession = Depends(get_db)
):
    """Approve a distribution plan."""
    service = DistributionOptimizationService(db)
    try:
        plan = await service.approve_plan(plan_id, approved_by)
        return plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{plan_id}/activate", response_model=DistributionPlanResponse)
async def activate_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Activate a distribution plan."""
    service = DistributionOptimizationService(db)
    try:
        plan = await service.activate_plan(plan_id)
        return plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{plan_id}/analytics", response_model=DistributionAnalytics)
async def get_plan_analytics(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get analytics for a distribution plan."""
    service = DistributionOptimizationService(db)
    try:
        analytics = await service.get_distribution_analytics(plan_id)
        return analytics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Distribution Points ====================

@router.post("/points", response_model=DistributionPointResponse)
async def create_distribution_point(
    data: DistributionPointCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a distribution point."""
    service = DistributionOptimizationService(db)
    point = await service.create_distribution_point(data)
    return point


@router.get("/{plan_id}/points", response_model=List[DistributionPointResponse])
async def list_distribution_points(
    plan_id: int,
    operational_status: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List distribution points for a plan."""
    service = DistributionOptimizationService(db)
    points = await service.list_distribution_points(
        plan_id=plan_id,
        operational_status=operational_status,
        is_active=is_active
    )
    return points


@router.post("/optimize-points", response_model=DistributionOptimizationResponse)
async def optimize_distribution_points(
    request: DistributionOptimizationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Optimize distribution point locations."""
    service = DistributionOptimizationService(db)
    result = await service.optimize_point_locations(request)
    return result


# ==================== Ration Allocations ====================

@router.post("/allocations", response_model=RationAllocationResponse)
async def create_ration_allocation(
    data: RationAllocationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a ration allocation."""
    service = DistributionOptimizationService(db)
    allocation = await service.create_ration_allocation(data)
    return allocation


@router.post("/{plan_id}/calculate-rations")
async def calculate_rations(
    plan_id: int,
    available_food: Dict[str, float],
    db: AsyncSession = Depends(get_db)
):
    """Calculate optimal ration allocations for all population groups."""
    service = DistributionOptimizationService(db)
    try:
        allocations = await service.calculate_rations(plan_id, available_food)
        return {"allocations": [a.model_dump() for a in allocations]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Vulnerable Populations ====================

@router.post("/vulnerable-populations", response_model=VulnerablePopulationResponse)
async def create_vulnerable_population(
    data: VulnerablePopulationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a vulnerable population record."""
    service = DistributionOptimizationService(db)
    population = await service.create_vulnerable_population(data)
    return population


@router.get("/vulnerable-populations/{region_id}", response_model=List[VulnerablePopulationResponse])
async def list_vulnerable_populations(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """List vulnerable populations in a region."""
    service = DistributionOptimizationService(db)
    populations = await service.list_vulnerable_populations(region_id)
    return populations


@router.get("/vulnerable-populations/{region_id}/counts")
async def get_priority_counts(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get population counts by priority type."""
    service = DistributionOptimizationService(db)
    counts = await service.get_priority_population_counts(region_id)
    return counts


# ==================== Distribution Records ====================

@router.post("/records", response_model=DistributionRecordResponse)
async def record_distribution(
    data: DistributionRecordCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record a distribution transaction."""
    service = DistributionOptimizationService(db)
    record = await service.record_distribution(data)
    return record


# ==================== Coverage Analysis ====================

@router.get("/coverage/{region_id}", response_model=CoverageAnalysis)
async def get_coverage_analysis(
    region_id: int,
    plan_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Analyze distribution coverage for a region."""
    service = DistributionOptimizationService(db)
    try:
        analysis = await service.get_coverage_analysis(region_id, plan_id)
        return analysis
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

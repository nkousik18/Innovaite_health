"""
Distribution Network API Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from models.distribution import CorridorType, DisruptionType, DisruptionSeverity
from services.distribution_service import DistributionNetworkService
from schemas.distribution import (
    CorridorCreate, CorridorUpdate, CorridorResponse,
    DistributionCenterCreate, DistributionCenterUpdate, DistributionCenterResponse,
    RouteCreate, RouteUpdate, RouteResponse,
    DisruptionCreate, DisruptionUpdate, DisruptionResponse,
    ColdChainFacilityCreate, ColdChainFacilityResponse,
    RouteOptimizationRequest, RouteOptimizationResponse,
    NetworkStatusResponse, ActiveDisruptionSummary
)
from schemas.google_maps import (
    AutoRouteGenerateRequest, AutoRouteGenerateResponse,
    SmartRouteOptimizationRequest,
)
from schemas.common import PaginatedResponse

router = APIRouter()


# ==================== Transportation Corridors ====================

@router.post("/corridors", response_model=CorridorResponse)
async def create_corridor(
    data: CorridorCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new transportation corridor."""
    service = DistributionNetworkService(db)
    corridor = await service.create_corridor(data)
    return corridor


@router.get("/corridors", response_model=PaginatedResponse[CorridorResponse])
async def list_corridors(
    corridor_type: Optional[CorridorType] = None,
    region_id: Optional[int] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List transportation corridors."""
    service = DistributionNetworkService(db)
    offset = (page - 1) * page_size
    corridors, total = await service.list_corridors(
        corridor_type=corridor_type,
        region_id=region_id,
        is_active=is_active,
        limit=page_size,
        offset=offset
    )
    return PaginatedResponse(
        items=corridors,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/corridors/{corridor_id}", response_model=CorridorResponse)
async def get_corridor(
    corridor_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific corridor."""
    service = DistributionNetworkService(db)
    corridor = await service.get_corridor(corridor_id)
    if not corridor:
        raise HTTPException(status_code=404, detail="Corridor not found")
    return corridor


@router.patch("/corridors/{corridor_id}", response_model=CorridorResponse)
async def update_corridor(
    corridor_id: int,
    data: CorridorUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a corridor."""
    service = DistributionNetworkService(db)
    corridor = await service.update_corridor(corridor_id, data)
    if not corridor:
        raise HTTPException(status_code=404, detail="Corridor not found")
    return corridor


# ==================== Distribution Centers ====================

@router.post("/centers", response_model=DistributionCenterResponse)
async def create_distribution_center(
    data: DistributionCenterCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new distribution center."""
    service = DistributionNetworkService(db)
    center = await service.create_distribution_center(data)
    return center


@router.get("/centers", response_model=PaginatedResponse[DistributionCenterResponse])
async def list_distribution_centers(
    region_id: Optional[int] = None,
    operational_status: Optional[str] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List distribution centers."""
    service = DistributionNetworkService(db)
    offset = (page - 1) * page_size
    centers, total = await service.list_distribution_centers(
        region_id=region_id,
        operational_status=operational_status,
        is_active=is_active,
        limit=page_size,
        offset=offset
    )
    return PaginatedResponse(
        items=centers,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/centers/{center_id}", response_model=DistributionCenterResponse)
async def get_distribution_center(
    center_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific distribution center."""
    service = DistributionNetworkService(db)
    center = await service.get_distribution_center(center_id)
    if not center:
        raise HTTPException(status_code=404, detail="Distribution center not found")
    return center


@router.patch("/centers/{center_id}", response_model=DistributionCenterResponse)
async def update_distribution_center(
    center_id: int,
    data: DistributionCenterUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a distribution center."""
    service = DistributionNetworkService(db)
    center = await service.update_distribution_center(center_id, data)
    if not center:
        raise HTTPException(status_code=404, detail="Distribution center not found")
    return center


@router.get("/centers/nearby")
async def get_nearby_centers(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(50, ge=1, le=500),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Find distribution centers near a location."""
    service = DistributionNetworkService(db)
    centers = await service.get_centers_near_location(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit
    )
    return centers


# ==================== Transport Routes ====================

@router.post("/routes", response_model=RouteResponse)
async def create_route(
    data: RouteCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new transport route."""
    service = DistributionNetworkService(db)
    route = await service.create_route(data)
    return route


@router.get("/routes", response_model=List[RouteResponse])
async def list_routes(
    origin_region_id: Optional[int] = None,
    destination_region_id: Optional[int] = None,
    corridor_id: Optional[int] = None,
    cold_chain_capable: Optional[bool] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List transport routes."""
    service = DistributionNetworkService(db)
    routes = await service.list_routes(
        origin_region_id=origin_region_id,
        destination_region_id=destination_region_id,
        corridor_id=corridor_id,
        cold_chain_capable=cold_chain_capable,
        is_active=is_active
    )
    return routes


@router.get("/routes/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific route."""
    service = DistributionNetworkService(db)
    route = await service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.post("/routes/optimize", response_model=RouteOptimizationResponse)
async def optimize_route(
    request: RouteOptimizationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Find optimal routes between regions."""
    service = DistributionNetworkService(db)
    try:
        result = await service.optimize_route(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/routes/auto-generate", response_model=AutoRouteGenerateResponse)
async def auto_generate_routes(
    request: AutoRouteGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Auto-generate routes between distribution centers using Google Maps API."""
    service = DistributionNetworkService(db)
    try:
        result = await service.auto_generate_routes(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/routes/optimize-smart", response_model=RouteOptimizationResponse)
async def optimize_route_smart(
    request: SmartRouteOptimizationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Enhanced route optimization with optional Google Maps real-time data."""
    service = DistributionNetworkService(db)
    try:
        result = await service.optimize_route_smart(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Route Disruptions ====================

@router.post("/disruptions", response_model=DisruptionResponse)
async def create_disruption(
    data: DisruptionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Report a new route disruption."""
    service = DistributionNetworkService(db)
    disruption = await service.create_disruption(data)
    return disruption


@router.get("/disruptions", response_model=List[DisruptionResponse])
async def list_active_disruptions(
    region_id: Optional[int] = None,
    disruption_type: Optional[DisruptionType] = None,
    severity: Optional[DisruptionSeverity] = None,
    db: AsyncSession = Depends(get_db)
):
    """List active disruptions."""
    service = DistributionNetworkService(db)
    disruptions = await service.list_active_disruptions(
        region_id=region_id,
        disruption_type=disruption_type,
        severity=severity
    )
    return disruptions


@router.get("/disruptions/{disruption_id}", response_model=DisruptionResponse)
async def get_disruption(
    disruption_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific disruption."""
    service = DistributionNetworkService(db)
    disruption = await service.get_disruption(disruption_id)
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")
    return disruption


@router.post("/disruptions/{disruption_id}/resolve", response_model=DisruptionResponse)
async def resolve_disruption(
    disruption_id: int,
    resolution_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Resolve a disruption."""
    service = DistributionNetworkService(db)
    disruption = await service.resolve_disruption(disruption_id, resolution_notes)
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")
    return disruption


@router.get("/disruptions/summary", response_model=ActiveDisruptionSummary)
async def get_disruption_summary(
    db: AsyncSession = Depends(get_db)
):
    """Get summary of active disruptions."""
    service = DistributionNetworkService(db)
    summary = await service.get_disruption_summary()
    return summary


# ==================== Cold Chain ====================

@router.post("/cold-chain", response_model=ColdChainFacilityResponse)
async def create_cold_chain_facility(
    data: ColdChainFacilityCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new cold chain facility."""
    service = DistributionNetworkService(db)
    facility = await service.create_cold_chain_facility(data)
    return facility


@router.get("/cold-chain", response_model=List[ColdChainFacilityResponse])
async def list_cold_chain_facilities(
    region_id: Optional[int] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List cold chain facilities."""
    service = DistributionNetworkService(db)
    facilities = await service.list_cold_chain_facilities(
        region_id=region_id,
        is_active=is_active
    )
    return facilities


@router.get("/cold-chain/capacity")
async def get_cold_chain_capacity(
    region_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get cold chain capacity summary."""
    service = DistributionNetworkService(db)
    capacity = await service.get_cold_chain_capacity(region_id=region_id)
    return capacity


# ==================== Network Status ====================

@router.get("/status", response_model=NetworkStatusResponse)
async def get_network_status(
    db: AsyncSession = Depends(get_db)
):
    """Get overall network status."""
    service = DistributionNetworkService(db)
    status = await service.get_network_status()
    return status

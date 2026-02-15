"""
Distribution Network Analysis Service

Handles:
- Transportation corridor management
- Distribution center operations
- Route optimization
- Disruption monitoring and management
- Cold chain tracking
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import selectinload

from models.distribution import (
    TransportationCorridor, DistributionCenter, TransportRoute,
    RouteDisruption, ColdChainFacility,
    CorridorType, DisruptionType, DisruptionSeverity
)
from models.agricultural import Region
from schemas.distribution import (
    CorridorCreate, CorridorUpdate, CorridorResponse,
    DistributionCenterCreate, DistributionCenterUpdate, DistributionCenterResponse,
    RouteCreate, RouteUpdate, RouteResponse,
    DisruptionCreate, DisruptionUpdate, DisruptionResponse,
    ColdChainFacilityCreate, ColdChainFacilityResponse,
    RouteOptimizationRequest, RouteOptimizationResponse, OptimizedRoute,
    NetworkStatusResponse, ActiveDisruptionSummary
)
from schemas.google_maps import (
    AutoRouteGenerateRequest, AutoRouteResult, AutoRouteGenerateResponse,
    SmartRouteOptimizationRequest, OptimizeFor,
)
from services.google_maps_service import GoogleMapsService
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DistributionNetworkService:
    """Service for distribution network management and analysis."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Transportation Corridors ====================

    async def create_corridor(self, data: CorridorCreate) -> TransportationCorridor:
        """Create a new transportation corridor."""
        corridor = TransportationCorridor(**data.model_dump())
        self.db.add(corridor)
        await self.db.flush()
        await self.db.refresh(corridor)
        logger.info(f"Created corridor: {corridor.name} ({corridor.corridor_code})")
        return corridor

    async def get_corridor(self, corridor_id: int) -> Optional[TransportationCorridor]:
        """Get corridor by ID."""
        result = await self.db.execute(
            select(TransportationCorridor)
            .options(selectinload(TransportationCorridor.routes))
            .where(TransportationCorridor.id == corridor_id)
        )
        return result.scalar_one_or_none()

    async def list_corridors(
        self,
        corridor_type: Optional[CorridorType] = None,
        region_id: Optional[int] = None,
        is_active: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[TransportationCorridor], int]:
        """List transportation corridors."""
        query = select(TransportationCorridor).where(
            TransportationCorridor.is_active == is_active
        )

        if corridor_type:
            query = query.where(TransportationCorridor.corridor_type == corridor_type)
        if region_id:
            query = query.where(
                or_(
                    TransportationCorridor.start_region_id == region_id,
                    TransportationCorridor.end_region_id == region_id
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        corridors = result.scalars().all()

        return list(corridors), total

    async def update_corridor(
        self,
        corridor_id: int,
        data: CorridorUpdate
    ) -> Optional[TransportationCorridor]:
        """Update corridor."""
        corridor = await self.get_corridor(corridor_id)
        if not corridor:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(corridor, field, value)

        await self.db.flush()
        await self.db.refresh(corridor)
        return corridor

    # ==================== Distribution Centers ====================

    async def create_distribution_center(
        self,
        data: DistributionCenterCreate
    ) -> DistributionCenter:
        """Create a new distribution center."""
        center = DistributionCenter(**data.model_dump())
        self.db.add(center)
        await self.db.flush()
        await self.db.refresh(center)
        logger.info(f"Created distribution center: {center.name}")
        return center

    async def get_distribution_center(
        self,
        center_id: int
    ) -> Optional[DistributionCenter]:
        """Get distribution center by ID."""
        result = await self.db.execute(
            select(DistributionCenter)
            .options(selectinload(DistributionCenter.stocks))
            .where(DistributionCenter.id == center_id)
        )
        return result.scalar_one_or_none()

    async def list_distribution_centers(
        self,
        region_id: Optional[int] = None,
        operational_status: Optional[str] = None,
        is_active: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[DistributionCenter], int]:
        """List distribution centers."""
        query = select(DistributionCenter).where(
            DistributionCenter.is_active == is_active
        )

        if region_id:
            query = query.where(DistributionCenter.region_id == region_id)
        if operational_status:
            query = query.where(
                DistributionCenter.operational_status == operational_status
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        centers = result.scalars().all()

        return list(centers), total

    async def update_distribution_center(
        self,
        center_id: int,
        data: DistributionCenterUpdate
    ) -> Optional[DistributionCenter]:
        """Update distribution center."""
        center = await self.get_distribution_center(center_id)
        if not center:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Calculate utilization if inventory updated
        if "current_inventory_tonnes" in update_data and center.total_capacity_tonnes:
            update_data["utilization_percentage"] = (
                update_data["current_inventory_tonnes"] /
                center.total_capacity_tonnes * 100
            )

        for field, value in update_data.items():
            setattr(center, field, value)

        await self.db.flush()
        await self.db.refresh(center)
        return center

    async def get_centers_near_location(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 50,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find distribution centers near a location."""
        # Simple distance calculation (Haversine approximation)
        # In production, use PostGIS for accurate geospatial queries
        centers_result = await self.db.execute(
            select(DistributionCenter).where(
                and_(
                    DistributionCenter.is_active == True,
                    DistributionCenter.operational_status == "operational"
                )
            )
        )
        centers = centers_result.scalars().all()

        nearby = []
        for center in centers:
            distance = self._calculate_distance(
                latitude, longitude,
                center.latitude, center.longitude
            )
            if distance <= radius_km:
                nearby.append({
                    "center": center,
                    "distance_km": distance
                })

        nearby.sort(key=lambda x: x["distance_km"])
        return nearby[:limit]

    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points (Haversine formula)."""
        R = 6371  # Earth's radius in km

        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)

        a = (np.sin(delta_lat / 2) ** 2 +
             np.cos(lat1_rad) * np.cos(lat2_rad) *
             np.sin(delta_lon / 2) ** 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        return R * c

    # ==================== Transport Routes ====================

    async def create_route(self, data: RouteCreate) -> TransportRoute:
        """Create a new transport route."""
        route_data = data.model_dump()

        # Calculate cost if distance provided
        if data.distance_km:
            route_data["total_cost"] = (
                data.distance_km * (route_data.get("cost_per_km", 1.0)) +
                (route_data.get("toll_costs", 0) or 0)
            )

        route = TransportRoute(**route_data)
        self.db.add(route)
        await self.db.flush()
        await self.db.refresh(route)
        logger.info(f"Created route: {route.name}")
        return route

    async def get_route(self, route_id: int) -> Optional[TransportRoute]:
        """Get route by ID."""
        result = await self.db.execute(
            select(TransportRoute).where(TransportRoute.id == route_id)
        )
        return result.scalar_one_or_none()

    async def list_routes(
        self,
        origin_region_id: Optional[int] = None,
        destination_region_id: Optional[int] = None,
        corridor_id: Optional[int] = None,
        cold_chain_capable: Optional[bool] = None,
        is_active: bool = True
    ) -> List[TransportRoute]:
        """List transport routes."""
        query = select(TransportRoute).where(
            TransportRoute.is_active == is_active
        )

        if origin_region_id:
            query = query.where(TransportRoute.origin_region_id == origin_region_id)
        if destination_region_id:
            query = query.where(TransportRoute.destination_region_id == destination_region_id)
        if corridor_id:
            query = query.where(TransportRoute.corridor_id == corridor_id)
        if cold_chain_capable is not None:
            query = query.where(TransportRoute.cold_chain_capable == cold_chain_capable)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_routes_between_regions(
        self,
        origin_region_id: int,
        destination_region_id: int,
        include_disrupted: bool = False
    ) -> List[TransportRoute]:
        """Find all routes between two regions."""
        query = select(TransportRoute).where(
            and_(
                TransportRoute.origin_region_id == origin_region_id,
                TransportRoute.destination_region_id == destination_region_id,
                TransportRoute.is_active == True
            )
        )

        if not include_disrupted:
            query = query.where(
                TransportRoute.operational_status == "operational"
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Route Disruptions ====================

    async def create_disruption(self, data: DisruptionCreate) -> RouteDisruption:
        """Create a new route disruption."""
        disruption_data = data.model_dump()
        disruption = RouteDisruption(**disruption_data)
        self.db.add(disruption)
        await self.db.flush()
        await self.db.refresh(disruption)

        # Update affected routes/corridors status
        await self._update_affected_infrastructure(disruption)

        logger.warning(
            f"Disruption created: {disruption.title} "
            f"(Severity: {disruption.severity.value})"
        )
        return disruption

    async def _update_affected_infrastructure(
        self,
        disruption: RouteDisruption
    ) -> None:
        """Update status of affected routes and corridors."""
        status_map = {
            DisruptionSeverity.LOW: "delayed",
            DisruptionSeverity.MEDIUM: "impaired",
            DisruptionSeverity.HIGH: "restricted",
            DisruptionSeverity.CRITICAL: "blocked"
        }

        new_status = status_map.get(disruption.severity, "impaired")

        if disruption.route_id:
            await self.db.execute(
                update(TransportRoute)
                .where(TransportRoute.id == disruption.route_id)
                .values(operational_status=new_status)
            )

        if disruption.corridor_id:
            await self.db.execute(
                update(TransportationCorridor)
                .where(TransportationCorridor.id == disruption.corridor_id)
                .values(operational_status=new_status)
            )

    async def get_disruption(self, disruption_id: int) -> Optional[RouteDisruption]:
        """Get disruption by ID."""
        result = await self.db.execute(
            select(RouteDisruption).where(RouteDisruption.id == disruption_id)
        )
        return result.scalar_one_or_none()

    async def list_active_disruptions(
        self,
        region_id: Optional[int] = None,
        disruption_type: Optional[DisruptionType] = None,
        severity: Optional[DisruptionSeverity] = None
    ) -> List[RouteDisruption]:
        """List active disruptions."""
        query = select(RouteDisruption).where(
            RouteDisruption.is_active == True
        )

        if region_id:
            query = query.where(RouteDisruption.region_id == region_id)
        if disruption_type:
            query = query.where(RouteDisruption.disruption_type == disruption_type)
        if severity:
            query = query.where(RouteDisruption.severity == severity)

        query = query.order_by(RouteDisruption.started_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def resolve_disruption(
        self,
        disruption_id: int,
        resolution_notes: Optional[str] = None
    ) -> Optional[RouteDisruption]:
        """Resolve a disruption."""
        disruption = await self.get_disruption(disruption_id)
        if not disruption:
            return None

        disruption.is_active = False
        disruption.actual_end_at = datetime.utcnow()
        disruption.duration_hours = (
            disruption.actual_end_at - disruption.started_at
        ).total_seconds() / 3600

        # Restore affected infrastructure
        if disruption.route_id:
            await self.db.execute(
                update(TransportRoute)
                .where(TransportRoute.id == disruption.route_id)
                .values(operational_status="operational")
            )

        if disruption.corridor_id:
            await self.db.execute(
                update(TransportationCorridor)
                .where(TransportationCorridor.id == disruption.corridor_id)
                .values(operational_status="operational")
            )

        await self.db.flush()
        await self.db.refresh(disruption)

        logger.info(f"Disruption resolved: {disruption.title}")
        return disruption

    async def get_disruption_summary(self) -> ActiveDisruptionSummary:
        """Get summary of active disruptions."""
        disruptions = await self.list_active_disruptions()

        by_severity = {}
        by_type = {}
        affected_regions = set()
        total_capacity_reduction = 0

        for d in disruptions:
            # Count by severity
            sev = d.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1

            # Count by type
            dtype = d.disruption_type.value
            by_type[dtype] = by_type.get(dtype, 0) + 1

            # Track affected regions
            if d.region_id:
                affected_regions.add(d.region_id)

            # Sum capacity reduction
            if d.capacity_reduction_percentage:
                total_capacity_reduction += d.capacity_reduction_percentage

        return ActiveDisruptionSummary(
            total_active=len(disruptions),
            by_severity=by_severity,
            by_type=by_type,
            affected_regions=list(affected_regions),
            total_capacity_reduction=total_capacity_reduction
        )

    # ==================== Route Optimization ====================

    async def optimize_route(
        self,
        request: RouteOptimizationRequest
    ) -> RouteOptimizationResponse:
        """Find optimal routes between regions."""
        # Get available routes
        routes = await self.find_routes_between_regions(
            origin_region_id=request.origin_region_id,
            destination_region_id=request.destination_region_id,
            include_disrupted=not request.avoid_disruptions
        )

        if not routes:
            # Try to find indirect routes
            routes = await self._find_indirect_routes(
                request.origin_region_id,
                request.destination_region_id
            )

        if not routes:
            raise ValueError("No routes available between specified regions")

        # Filter for cold chain if required
        if request.requires_cold_chain:
            routes = [r for r in routes if r.cold_chain_capable]
            if not routes:
                raise ValueError("No cold chain capable routes available")

        # Score and rank routes
        scored_routes = []
        for route in routes:
            score = self._score_route(route, request)
            scored_routes.append((route, score))

        scored_routes.sort(key=lambda x: x[1], reverse=True)

        # Get active disruptions for risk assessment
        disruptions = await self.list_active_disruptions()
        disruption_routes = {d.route_id for d in disruptions if d.route_id}

        # Build response
        optimized_routes = []
        for route, score in scored_routes[:request.max_alternatives]:
            disruption_risk = 0.5 if route.id in disruption_routes else 0.1
            optimized_routes.append(OptimizedRoute(
                route_id=route.id,
                route_name=route.name,
                distance_km=route.distance_km or 0,
                estimated_time_hours=route.estimated_time_hours or 0,
                estimated_cost=route.total_cost or 0,
                cold_chain_capable=route.cold_chain_capable,
                disruption_risk=disruption_risk,
                waypoints=[]  # Would include actual waypoints in production
            ))

        # Get region names
        origin = await self.db.execute(
            select(Region).where(Region.id == request.origin_region_id)
        )
        dest = await self.db.execute(
            select(Region).where(Region.id == request.destination_region_id)
        )
        origin_region = origin.scalar_one_or_none()
        dest_region = dest.scalar_one_or_none()

        return RouteOptimizationResponse(
            origin=origin_region.name if origin_region else str(request.origin_region_id),
            destination=dest_region.name if dest_region else str(request.destination_region_id),
            cargo_tonnes=request.cargo_tonnes,
            recommended_route=optimized_routes[0] if optimized_routes else None,
            alternative_routes=optimized_routes[1:] if len(optimized_routes) > 1 else [],
            analysis_timestamp=datetime.utcnow()
        )

    def _score_route(
        self,
        route: TransportRoute,
        request: RouteOptimizationRequest
    ) -> float:
        """Score a route based on multiple factors."""
        score = 100.0

        # Time factor (faster is better)
        if route.estimated_time_hours:
            score -= route.estimated_time_hours * 2

        # Cost factor
        if route.total_cost:
            score -= route.total_cost / 100

        # Capacity check
        if route.daily_capacity_tonnes and route.daily_capacity_tonnes < request.cargo_tonnes:
            score -= 30  # Penalty for insufficient capacity

        # Primary route bonus
        if route.is_primary_route:
            score += 10

        # Cold chain bonus if needed
        if request.requires_cold_chain and route.cold_chain_capable:
            score += 15

        # Operational status
        if route.operational_status != "operational":
            score -= 25

        return max(0, score)

    async def _find_indirect_routes(
        self,
        origin_region_id: int,
        destination_region_id: int,
        max_hops: int = 2
    ) -> List[TransportRoute]:
        """Find indirect routes through intermediate regions."""
        # Get routes from origin
        from_origin = await self.db.execute(
            select(TransportRoute).where(
                and_(
                    TransportRoute.origin_region_id == origin_region_id,
                    TransportRoute.is_active == True
                )
            )
        )
        origin_routes = from_origin.scalars().all()

        indirect_routes = []

        for route in origin_routes:
            # Check if we can reach destination from this intermediate
            intermediate_id = route.destination_region_id
            to_dest = await self.db.execute(
                select(TransportRoute).where(
                    and_(
                        TransportRoute.origin_region_id == intermediate_id,
                        TransportRoute.destination_region_id == destination_region_id,
                        TransportRoute.is_active == True
                    )
                )
            )
            connecting_routes = to_dest.scalars().all()

            for connecting in connecting_routes:
                # Create a virtual combined route
                indirect_routes.append(route)  # Simplified; would combine in production

        return indirect_routes

    # ==================== Cold Chain Management ====================

    async def create_cold_chain_facility(
        self,
        data: ColdChainFacilityCreate
    ) -> ColdChainFacility:
        """Create a new cold chain facility."""
        facility = ColdChainFacility(**data.model_dump())
        self.db.add(facility)
        await self.db.flush()
        await self.db.refresh(facility)
        logger.info(f"Created cold chain facility: {facility.name}")
        return facility

    async def list_cold_chain_facilities(
        self,
        region_id: Optional[int] = None,
        is_active: bool = True
    ) -> List[ColdChainFacility]:
        """List cold chain facilities."""
        query = select(ColdChainFacility).where(
            ColdChainFacility.is_active == is_active
        )

        if region_id:
            query = query.where(ColdChainFacility.region_id == region_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_cold_chain_capacity(
        self,
        region_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get cold chain capacity summary."""
        facilities = await self.list_cold_chain_facilities(region_id=region_id)

        total_capacity = sum(f.total_capacity_tonnes or 0 for f in facilities)
        total_used = sum(f.current_inventory_tonnes or 0 for f in facilities)
        freezer_capacity = sum(f.freezer_capacity_tonnes or 0 for f in facilities)
        chiller_capacity = sum(f.chiller_capacity_tonnes or 0 for f in facilities)

        alerts = [f for f in facilities if f.temperature_alert]

        return {
            "total_facilities": len(facilities),
            "operational_facilities": len([f for f in facilities if f.operational_status == "operational"]),
            "total_capacity_tonnes": total_capacity,
            "current_inventory_tonnes": total_used,
            "utilization_percentage": (total_used / total_capacity * 100) if total_capacity > 0 else 0,
            "freezer_capacity_tonnes": freezer_capacity,
            "chiller_capacity_tonnes": chiller_capacity,
            "temperature_alerts": len(alerts),
            "facilities_with_alerts": [{"id": f.id, "name": f.name} for f in alerts]
        }

    # ==================== Auto-Generate Routes (Google Maps) ====================

    async def auto_generate_routes(
        self, request: AutoRouteGenerateRequest
    ) -> AutoRouteGenerateResponse:
        """
        Auto-generate TransportRoute records between distribution centers
        using Google Maps Directions API for real distance/duration data.
        """
        maps_service = GoogleMapsService()

        # Load centers
        centers = await self._get_centers_for_route_generation(request)
        if len(centers) < 2:
            raise ValueError("Need at least 2 distribution centers to generate routes")

        # Generate pairs
        pairs = list(self._generate_center_pairs(centers, request.include_reverse))

        # Cap to max_routes
        pairs = pairs[: request.max_routes]

        results: List[AutoRouteResult] = []
        routes_created = 0
        routes_skipped = 0

        for origin, dest in pairs:
            # Check for existing route
            existing = await self.db.execute(
                select(TransportRoute).where(
                    and_(
                        TransportRoute.origin_center_id == origin.id,
                        TransportRoute.destination_center_id == dest.id,
                        TransportRoute.is_active == True,
                    )
                )
            )
            if existing.scalar_one_or_none():
                routes_skipped += 1
                results.append(AutoRouteResult(
                    origin_center_id=origin.id,
                    origin_center_name=origin.name,
                    destination_center_id=dest.id,
                    destination_center_name=dest.name,
                    distance_km=0,
                    duration_hours=0,
                    saved=False,
                    skipped_reason="Route already exists",
                ))
                continue

            try:
                directions = await maps_service.get_directions(
                    origin.latitude, origin.longitude,
                    dest.latitude, dest.longitude,
                )
            except Exception as e:
                routes_skipped += 1
                results.append(AutoRouteResult(
                    origin_center_id=origin.id,
                    origin_center_name=origin.name,
                    destination_center_id=dest.id,
                    destination_center_name=dest.name,
                    distance_km=0,
                    duration_hours=0,
                    saved=False,
                    skipped_reason=f"Google Maps error: {e}",
                ))
                continue

            route = await self._create_route_from_directions(origin, dest, directions)
            routes_created += 1
            results.append(AutoRouteResult(
                origin_center_id=origin.id,
                origin_center_name=origin.name,
                destination_center_id=dest.id,
                destination_center_name=dest.name,
                distance_km=directions["distance_km"],
                duration_hours=directions["duration_hours"],
                polyline=directions.get("polyline", ""),
                saved=True,
                route_id=route.id,
            ))

        return AutoRouteGenerateResponse(
            total_pairs_considered=len(pairs),
            routes_created=routes_created,
            routes_skipped=routes_skipped,
            results=results,
        )

    async def _create_route_from_directions(
        self,
        origin: DistributionCenter,
        dest: DistributionCenter,
        directions: Dict[str, Any],
    ) -> TransportRoute:
        """Create a TransportRoute record from Google Maps directions data."""
        route_code = f"AR-{origin.center_code}-{dest.center_code}"

        route = TransportRoute(
            name=f"{origin.name} -> {dest.name}",
            route_code=route_code,
            origin_center_id=origin.id,
            destination_center_id=dest.id,
            origin_region_id=origin.region_id,
            destination_region_id=dest.region_id,
            distance_km=directions["distance_km"],
            estimated_time_hours=directions["duration_hours"],
            path_geometry={"polyline": directions.get("polyline", "")},
            operational_status="operational",
            is_active=True,
        )
        self.db.add(route)
        await self.db.flush()
        await self.db.refresh(route)
        logger.info(f"Auto-created route: {route.name} ({route.route_code})")
        return route

    async def _get_centers_for_route_generation(
        self, request: AutoRouteGenerateRequest
    ) -> List[DistributionCenter]:
        """Load distribution centers by IDs or region IDs."""
        query = select(DistributionCenter).where(
            and_(
                DistributionCenter.is_active == True,
                DistributionCenter.operational_status == "operational",
            )
        )

        if request.center_ids:
            query = query.where(DistributionCenter.id.in_(request.center_ids))
        elif request.region_ids:
            query = query.where(DistributionCenter.region_id.in_(request.region_ids))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _generate_center_pairs(
        self,
        centers: List[DistributionCenter],
        include_reverse: bool,
    ):
        """Yield (origin, dest) pairs for route generation."""
        for i, origin in enumerate(centers):
            for j, dest in enumerate(centers):
                if i == j:
                    continue
                if not include_reverse and j < i:
                    continue
                yield origin, dest

    async def optimize_route_smart(
        self, request: SmartRouteOptimizationRequest
    ) -> RouteOptimizationResponse:
        """
        Enhanced route optimization. If use_google_maps is True, enrich
        existing routes with real Google Maps distance/duration data.
        Otherwise fall back to existing optimize_route().
        """
        # Fall back to existing optimization if Google Maps not requested
        if not request.use_google_maps:
            fallback_request = RouteOptimizationRequest(
                origin_region_id=request.origin_region_id,
                destination_region_id=request.destination_region_id,
                cargo_tonnes=request.cargo_tonnes,
                requires_cold_chain=request.requires_cold_chain,
                max_alternatives=request.max_alternatives,
                avoid_disruptions=request.avoid_disruptions,
            )
            return await self.optimize_route(fallback_request)

        maps_service = GoogleMapsService()

        # Get available routes between the two regions
        routes = await self.find_routes_between_regions(
            origin_region_id=request.origin_region_id,
            destination_region_id=request.destination_region_id,
            include_disrupted=not request.avoid_disruptions,
        )

        if request.requires_cold_chain:
            routes = [r for r in routes if r.cold_chain_capable]

        if not routes:
            raise ValueError("No routes available between specified regions")

        # Collect origin/dest coordinates for Distance Matrix call
        origins_coords = []
        dests_coords = []
        for route in routes:
            o_lat, o_lon = await self._get_route_origin_coords(route)
            d_lat, d_lon = await self._get_route_dest_coords(route)
            origins_coords.append({"lat": o_lat, "lon": o_lon})
            dests_coords.append({"lat": d_lat, "lon": d_lon})

        # Call Distance Matrix for real data
        try:
            matrix = await maps_service.get_distance_matrix(origins_coords, dests_coords)
        except Exception as e:
            logger.warning(f"Google Maps Distance Matrix failed, falling back: {e}")
            fallback_request = RouteOptimizationRequest(
                origin_region_id=request.origin_region_id,
                destination_region_id=request.destination_region_id,
                cargo_tonnes=request.cargo_tonnes,
                requires_cold_chain=request.requires_cold_chain,
                max_alternatives=request.max_alternatives,
                avoid_disruptions=request.avoid_disruptions,
            )
            return await self.optimize_route(fallback_request)

        # Enrich routes with real data and score
        disruptions = await self.list_active_disruptions()
        disruption_routes = {d.route_id for d in disruptions if d.route_id}

        scored_routes = []
        for idx, route in enumerate(routes):
            # Use diagonal element (same-index origin to dest)
            if idx < len(matrix["rows"]):
                row = matrix["rows"][idx]
                if idx < len(row["elements"]):
                    element = row["elements"][idx]
                    if element["status"] == "OK":
                        route.distance_km = element["distance_km"]
                        route.estimated_time_hours = element["duration_hours"]

            score = self._score_route_smart(route, request)
            scored_routes.append((route, score))

        scored_routes.sort(key=lambda x: x[1], reverse=True)

        # Build response
        optimized_routes = []
        for route, score in scored_routes[: request.max_alternatives]:
            disruption_risk = 0.5 if route.id in disruption_routes else 0.1
            optimized_routes.append(OptimizedRoute(
                route_id=route.id,
                route_name=route.name,
                distance_km=route.distance_km or 0,
                estimated_time_hours=route.estimated_time_hours or 0,
                estimated_cost=route.total_cost or 0,
                cold_chain_capable=route.cold_chain_capable,
                disruption_risk=disruption_risk,
                waypoints=[],
            ))

        origin_region = (await self.db.execute(
            select(Region).where(Region.id == request.origin_region_id)
        )).scalar_one_or_none()
        dest_region = (await self.db.execute(
            select(Region).where(Region.id == request.destination_region_id)
        )).scalar_one_or_none()

        return RouteOptimizationResponse(
            origin=origin_region.name if origin_region else str(request.origin_region_id),
            destination=dest_region.name if dest_region else str(request.destination_region_id),
            cargo_tonnes=request.cargo_tonnes,
            recommended_route=optimized_routes[0] if optimized_routes else None,
            alternative_routes=optimized_routes[1:] if len(optimized_routes) > 1 else [],
            analysis_timestamp=datetime.utcnow(),
        )

    def _score_route_smart(
        self,
        route: TransportRoute,
        request: SmartRouteOptimizationRequest,
    ) -> float:
        """Score a route with optimization priority weighting."""
        score = 100.0

        time_weight = 1.0
        cost_weight = 1.0

        if request.optimize_for == OptimizeFor.TIME:
            time_weight = 2.0
            cost_weight = 0.5
        elif request.optimize_for == OptimizeFor.COST:
            time_weight = 0.5
            cost_weight = 2.0

        if route.estimated_time_hours:
            score -= route.estimated_time_hours * 2 * time_weight

        if route.total_cost:
            score -= (route.total_cost / 100) * cost_weight

        if route.daily_capacity_tonnes and route.daily_capacity_tonnes < request.cargo_tonnes:
            score -= 30

        if route.is_primary_route:
            score += 10

        if request.requires_cold_chain and route.cold_chain_capable:
            score += 15

        if route.operational_status != "operational":
            score -= 25

        return max(0, score)

    async def _get_route_origin_coords(self, route: TransportRoute) -> tuple:
        """Get origin coordinates for a route (from center or region)."""
        if route.origin_center_id:
            center = await self.get_distribution_center(route.origin_center_id)
            if center:
                return center.latitude, center.longitude
        if route.origin_region_id:
            region = (await self.db.execute(
                select(Region).where(Region.id == route.origin_region_id)
            )).scalar_one_or_none()
            if region:
                return region.latitude, region.longitude
        return 0.0, 0.0

    async def _get_route_dest_coords(self, route: TransportRoute) -> tuple:
        """Get destination coordinates for a route (from center or region)."""
        if route.destination_center_id:
            center = await self.get_distribution_center(route.destination_center_id)
            if center:
                return center.latitude, center.longitude
        if route.destination_region_id:
            region = (await self.db.execute(
                select(Region).where(Region.id == route.destination_region_id)
            )).scalar_one_or_none()
            if region:
                return region.latitude, region.longitude
        return 0.0, 0.0

    # ==================== Network Status ====================

    async def get_network_status(self) -> NetworkStatusResponse:
        """Get overall network status."""
        # Count corridors
        corridors = await self.db.execute(
            select(func.count(), TransportationCorridor.operational_status)
            .where(TransportationCorridor.is_active == True)
            .group_by(TransportationCorridor.operational_status)
        )
        corridor_counts = dict(corridors.all())
        total_corridors = sum(corridor_counts.values())
        operational_corridors = corridor_counts.get("operational", 0)

        # Count routes
        routes = await self.db.execute(
            select(func.count(), TransportRoute.operational_status)
            .where(TransportRoute.is_active == True)
            .group_by(TransportRoute.operational_status)
        )
        route_counts = dict(routes.all())
        total_routes = sum(route_counts.values())
        operational_routes = route_counts.get("operational", 0)

        # Count active disruptions
        disruption_count = await self.db.execute(
            select(func.count())
            .select_from(RouteDisruption)
            .where(RouteDisruption.is_active == True)
        )
        active_disruptions = disruption_count.scalar()

        # Calculate capacity utilization
        centers = await self.db.execute(
            select(
                func.sum(DistributionCenter.current_inventory_tonnes),
                func.sum(DistributionCenter.total_capacity_tonnes)
            )
            .where(DistributionCenter.is_active == True)
        )
        inventory, capacity = centers.one()
        network_utilization = (
            (inventory / capacity * 100) if capacity and inventory else 0
        )

        # Cold chain utilization
        cold_chain = await self.get_cold_chain_capacity()

        return NetworkStatusResponse(
            total_corridors=total_corridors,
            operational_corridors=operational_corridors,
            total_routes=total_routes,
            operational_routes=operational_routes,
            active_disruptions=active_disruptions,
            network_capacity_utilization=network_utilization,
            cold_chain_capacity_utilization=cold_chain.get("utilization_percentage", 0)
        )

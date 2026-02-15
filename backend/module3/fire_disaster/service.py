"""
Fire Disaster Pipeline Service

Orchestrates the full automated response:
  1. Weather check at fire origin
  2. Flag affected zones (regions within radius)
  3. Create route disruptions for affected corridors
  4. Model population displacement
  5. Recalculate food supply / days-of-supply
  6. Generate shortage alerts
  7. Reroute — find alternatives around blocked routes
  8. Optimise distribution plans for safe regions
"""

import logging
import uuid
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models.agricultural import Region, WeatherData
from models.distribution import (
    TransportRoute, RouteDisruption, DistributionCenter,
    DisruptionType, DisruptionSeverity,
)
from models.inventory import FoodInventory
from models.alerts import ShortageAlert, AlertLevel, AlertType, AlertStatus
from models.distribution_plan import (
    DistributionPlan, PlanStatus, PopulationType,
)

from services.weather_api_service import WeatherAPIService
from services.google_maps_service import GoogleMapsService
from config import get_settings

from .schemas import (
    FireDisasterRequest, FireDisasterResponse,
    WeatherCheckResult,
    AffectedZone, FlagZonesResult,
    DisruptionRecord, CreateDisruptionsResult,
    DisplacementEntry, DisplacePopulationResult,
    SupplyRecalcEntry, RecalculateSupplyResult,
    AlertRecord, GenerateAlertsResult,
    RerouteEntry, RerouteResult,
    DistributionPlanSummary, OptimizeDistributionResult,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Wind-direction → bearing (degrees clockwise from N)
_WIND_BEARINGS = {
    "N": 0, "NE": 45, "E": 90, "SE": 135,
    "S": 180, "SW": 225, "W": 270, "NW": 315,
}


class FireDisasterService:
    """Orchestrates the end-to-end fire disaster response pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── public entry point ───────────────────────────────────────────

    async def run_pipeline(self, req: FireDisasterRequest) -> FireDisasterResponse:
        scenario_id = f"FIRE-{uuid.uuid4().hex[:10].upper()}"
        started = datetime.utcnow()
        logger.info(f"[{scenario_id}] Pipeline started — fire at ({req.latitude}, {req.longitude})")

        # Step 1
        weather = await self._step1_weather_check(req)
        logger.info(f"[{scenario_id}] Step 1 done — {weather.fire_weather_risk} risk")

        # Step 2
        zones = await self._step2_flag_zones(req, weather)
        logger.info(f"[{scenario_id}] Step 2 done — {len(zones.affected_zones)} zones affected")

        # Step 3
        disruptions = await self._step3_create_disruptions(scenario_id, zones)
        logger.info(f"[{scenario_id}] Step 3 done — {disruptions.disruptions_created} disruptions")

        # Step 4
        displacement = await self._step4_displace_population(req, zones)
        logger.info(f"[{scenario_id}] Step 4 done — {displacement.total_displaced} people displaced")

        # Step 5
        supply = await self._step5_recalculate_supply(zones, displacement)
        logger.info(f"[{scenario_id}] Step 5 done — {supply.regions_updated} regions updated")

        # Step 6
        alerts = await self._step6_generate_alerts(scenario_id, zones, supply)
        logger.info(f"[{scenario_id}] Step 6 done — {alerts.alerts_generated} alerts")

        # Step 7
        reroute = await self._step7_reroute(scenario_id, zones)
        logger.info(f"[{scenario_id}] Step 7 done — {reroute.alternative_routes_created} alt routes")

        # Step 8
        distribution = await self._step8_optimize_distribution(
            scenario_id, zones, displacement, supply
        )
        logger.info(f"[{scenario_id}] Step 8 done — {distribution.plans_created} plans")

        completed = datetime.utcnow()
        duration = (completed - started).total_seconds()

        affected_pop = sum(
            (z.population or 0) for z in zones.affected_zones
        )

        summary = {
            "scenario_id": scenario_id,
            "fire_weather_risk": weather.fire_weather_risk,
            "regions_affected": len(zones.affected_zones),
            "population_in_affected_zones": affected_pop,
            "total_displaced": displacement.total_displaced,
            "routes_disrupted": disruptions.disruptions_created,
            "alerts_raised": alerts.alerts_generated,
            "alternative_routes": reroute.alternative_routes_created,
            "distribution_plans": distribution.plans_created,
            "pipeline_duration_seconds": round(duration, 2),
        }

        return FireDisasterResponse(
            scenario_id=scenario_id,
            fire_location={"latitude": req.latitude, "longitude": req.longitude},
            started_at=started,
            completed_at=completed,
            duration_seconds=round(duration, 2),
            step_1_weather=weather,
            step_2_zones=zones,
            step_3_disruptions=disruptions,
            step_4_displacement=displacement,
            step_5_supply=supply,
            step_6_alerts=alerts,
            step_7_reroute=reroute,
            step_8_distribution=distribution,
            summary=summary,
        )

    # ── Step 1 — Weather check ───────────────────────────────────────

    async def _step1_weather_check(self, req: FireDisasterRequest) -> WeatherCheckResult:
        weather_svc = WeatherAPIService()
        w = await weather_svc.get_current_weather(req.latitude, req.longitude)

        # Classify fire-weather risk
        temp = w.get("temperature_c") or 0
        humidity = w.get("humidity_percentage") or 100
        wind = w.get("wind_speed_kmh") or 0

        risk_score = 0
        if temp > 35:
            risk_score += 3
        elif temp > 28:
            risk_score += 2
        elif temp > 20:
            risk_score += 1

        if humidity < 20:
            risk_score += 3
        elif humidity < 35:
            risk_score += 2
        elif humidity < 50:
            risk_score += 1

        if wind > 40:
            risk_score += 3
        elif wind > 25:
            risk_score += 2
        elif wind > 10:
            risk_score += 1

        if risk_score >= 7:
            risk_label = "extreme"
        elif risk_score >= 5:
            risk_label = "high"
        elif risk_score >= 3:
            risk_label = "moderate"
        else:
            risk_label = "low"

        return WeatherCheckResult(
            temperature_c=w.get("temperature_c"),
            humidity_pct=w.get("humidity_percentage"),
            wind_speed_kmh=w.get("wind_speed_kmh"),
            wind_direction=w.get("wind_direction"),
            rainfall_mm=w.get("rainfall_mm"),
            description=w.get("description", ""),
            fire_weather_risk=risk_label,
        )

    # ── Step 2 — Flag affected zones ─────────────────────────────────

    async def _step2_flag_zones(
        self, req: FireDisasterRequest, weather: WeatherCheckResult
    ) -> FlagZonesResult:
        # Load all active regions
        result = await self.db.execute(
            select(Region).where(Region.is_active == True)
        )
        all_regions: List[Region] = list(result.scalars().all())

        wind_bearing = _WIND_BEARINGS.get(weather.wind_direction or "", None)

        affected: List[AffectedZone] = []
        for region in all_regions:
            dist = self._haversine(
                req.latitude, req.longitude,
                region.latitude, region.longitude,
            )
            if dist > req.radius_km:
                continue

            # Severity: closer = worse, scaled by fire_intensity
            normalised = dist / req.radius_km  # 0 at centre, 1 at edge
            severity_score = (1 - normalised) * req.fire_intensity

            if severity_score >= 0.6:
                severity = "critical"
            elif severity_score >= 0.3:
                severity = "high"
            else:
                severity = "moderate"

            # Check wind exposure — region is downwind of fire origin
            wind_exposed = False
            if wind_bearing is not None:
                bearing_to_region = self._bearing(
                    req.latitude, req.longitude,
                    region.latitude, region.longitude,
                )
                angle_diff = abs(bearing_to_region - wind_bearing)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                wind_exposed = angle_diff < 60  # within 60-degree cone

            # Upgrade severity one level if wind-exposed
            if wind_exposed and severity == "moderate":
                severity = "high"
            elif wind_exposed and severity == "high":
                severity = "critical"

            affected.append(AffectedZone(
                region_id=region.id,
                region_name=region.name,
                distance_km=round(dist, 1),
                severity=severity,
                population=region.population,
                wind_exposed=wind_exposed,
            ))

        affected.sort(key=lambda z: z.distance_km)

        return FlagZonesResult(
            total_regions_scanned=len(all_regions),
            affected_zones=affected,
        )

    # ── Step 3 — Create route disruptions ────────────────────────────

    async def _step3_create_disruptions(
        self, scenario_id: str, zones: FlagZonesResult
    ) -> CreateDisruptionsResult:
        affected_ids = {z.region_id for z in zones.affected_zones}
        severity_map = {z.region_id: z.severity for z in zones.affected_zones}

        if not affected_ids:
            return CreateDisruptionsResult(routes_scanned=0, disruptions_created=0, disruptions=[])

        # Find routes that touch any affected region
        result = await self.db.execute(
            select(TransportRoute).where(
                and_(
                    TransportRoute.is_active == True,
                    TransportRoute.operational_status == "operational",
                    (
                        TransportRoute.origin_region_id.in_(affected_ids)
                        | TransportRoute.destination_region_id.in_(affected_ids)
                    ),
                )
            )
        )
        routes: List[TransportRoute] = list(result.scalars().all())

        records: List[DisruptionRecord] = []
        for route in routes:
            # Pick the worst severity from origin/dest
            sev_origin = severity_map.get(route.origin_region_id, "")
            sev_dest = severity_map.get(route.destination_region_id, "")
            worst = self._worst_severity(sev_origin, sev_dest)

            db_severity = {
                "critical": DisruptionSeverity.CRITICAL,
                "high": DisruptionSeverity.HIGH,
                "moderate": DisruptionSeverity.MEDIUM,
            }.get(worst, DisruptionSeverity.MEDIUM)

            status_map = {
                DisruptionSeverity.CRITICAL: "blocked",
                DisruptionSeverity.HIGH: "restricted",
                DisruptionSeverity.MEDIUM: "impaired",
            }

            disruption = RouteDisruption(
                route_id=route.id,
                region_id=route.origin_region_id,
                disruption_type=DisruptionType.WEATHER,
                severity=db_severity,
                title=f"[{scenario_id}] Fire disruption on {route.name}",
                description=f"Route affected by fire disaster scenario {scenario_id}",
                capacity_reduction_percentage={
                    "critical": 100, "high": 70, "moderate": 40
                }.get(worst, 40),
                is_active=True,
            )
            self.db.add(disruption)
            await self.db.flush()
            await self.db.refresh(disruption)

            # Update route status
            route.operational_status = status_map.get(db_severity, "impaired")

            records.append(DisruptionRecord(
                disruption_id=disruption.id,
                route_id=route.id,
                route_name=route.name,
                severity=worst,
                status=route.operational_status,
            ))

        return CreateDisruptionsResult(
            routes_scanned=len(routes),
            disruptions_created=len(records),
            disruptions=records,
        )

    # ── Step 4 — Displace population ─────────────────────────────────

    async def _step4_displace_population(
        self, req: FireDisasterRequest, zones: FlagZonesResult
    ) -> DisplacePopulationResult:
        affected_ids = {z.region_id for z in zones.affected_zones}

        # Find safe regions (not affected) to receive displaced people
        result = await self.db.execute(
            select(Region).where(
                and_(Region.is_active == True, ~Region.id.in_(affected_ids))
            )
        )
        safe_regions: List[Region] = list(result.scalars().all())

        if not safe_regions:
            # If every region is affected, use the least-affected as receivers
            safe_regions_sorted = sorted(
                zones.affected_zones, key=lambda z: z.distance_km, reverse=True
            )
            receiver_ids = [z.region_id for z in safe_regions_sorted[:3]]
            result = await self.db.execute(
                select(Region).where(Region.id.in_(receiver_ids))
            )
            safe_regions = list(result.scalars().all())

        entries: List[DisplacementEntry] = []
        total_displaced = 0

        for zone in zones.affected_zones:
            pop = zone.population or 0
            if pop == 0:
                continue

            # Severity multiplier: critical displaces more than moderate
            sev_mult = {"critical": 1.0, "high": 0.7, "moderate": 0.3}.get(zone.severity, 0.3)
            displaced = int(pop * req.displacement_pct * sev_mult)

            if displaced == 0:
                continue

            # Distribute displaced population across safe regions (closest first)
            safe_with_dist = []
            from_region = await self._get_region(zone.region_id)
            if not from_region:
                continue

            for sr in safe_regions:
                d = self._haversine(from_region.latitude, from_region.longitude,
                                    sr.latitude, sr.longitude)
                safe_with_dist.append((sr, d))
            safe_with_dist.sort(key=lambda x: x[1])

            # Send proportionally more to closer safe regions
            remaining = displaced
            for i, (sr, _) in enumerate(safe_with_dist):
                if remaining <= 0:
                    break
                # Allocate decreasing shares
                share = max(1, remaining // (len(safe_with_dist) - i))
                share = min(share, remaining)

                entries.append(DisplacementEntry(
                    from_region_id=zone.region_id,
                    from_region_name=zone.region_name,
                    to_region_id=sr.id,
                    to_region_name=sr.name,
                    displaced_count=share,
                ))
                remaining -= share

            total_displaced += displaced

        return DisplacePopulationResult(
            total_displaced=total_displaced,
            entries=entries,
        )

    # ── Step 5 — Recalculate supply ──────────────────────────────────

    async def _step5_recalculate_supply(
        self, zones: FlagZonesResult, displacement: DisplacePopulationResult
    ) -> RecalculateSupplyResult:
        # Build a map: region_id -> net population change
        pop_delta: Dict[int, int] = {}
        for entry in displacement.entries:
            pop_delta[entry.from_region_id] = pop_delta.get(entry.from_region_id, 0) - entry.displaced_count
            pop_delta[entry.to_region_id] = pop_delta.get(entry.to_region_id, 0) + entry.displaced_count

        # Collect all region IDs involved
        region_ids = set(pop_delta.keys())
        for z in zones.affected_zones:
            region_ids.add(z.region_id)

        entries: List[SupplyRecalcEntry] = []
        for rid in region_ids:
            region = await self._get_region(rid)
            if not region:
                continue

            original_pop = region.population or 0
            delta = pop_delta.get(rid, 0)
            effective_pop = max(0, original_pop + delta)
            demand_mult = effective_pop / original_pop if original_pop > 0 else 1.0

            # Get latest inventory for this region to estimate days-of-supply
            inv_result = await self.db.execute(
                select(FoodInventory)
                .where(FoodInventory.region_id == rid)
                .order_by(FoodInventory.recorded_at.desc())
                .limit(1)
            )
            inv: Optional[FoodInventory] = inv_result.scalar_one_or_none()

            est_days: Optional[float] = None
            if inv and inv.consumption_rate_tonnes_per_day and inv.consumption_rate_tonnes_per_day > 0:
                adjusted_rate = inv.consumption_rate_tonnes_per_day * demand_mult
                est_days = round(inv.quantity_tonnes / adjusted_rate, 1) if adjusted_rate > 0 else None
            elif inv and inv.days_of_supply:
                est_days = round(inv.days_of_supply / demand_mult, 1) if demand_mult > 0 else None

            entries.append(SupplyRecalcEntry(
                region_id=rid,
                region_name=region.name,
                original_population=original_pop,
                effective_population=effective_pop,
                demand_multiplier=round(demand_mult, 2),
                estimated_days_of_supply=est_days,
            ))

        return RecalculateSupplyResult(
            regions_updated=len(entries),
            entries=entries,
        )

    # ── Step 6 — Generate alerts ─────────────────────────────────────

    async def _step6_generate_alerts(
        self, scenario_id: str, zones: FlagZonesResult, supply: RecalculateSupplyResult
    ) -> GenerateAlertsResult:
        records: List[AlertRecord] = []

        # Alert for every affected zone based on severity
        for zone in zones.affected_zones:
            # Determine alert level
            if zone.severity == "critical":
                level = AlertLevel.CRITICAL
            elif zone.severity == "high":
                level = AlertLevel.IMMINENT
            else:
                level = AlertLevel.WARNING

            # Find supply data for this region
            supply_entry = next(
                (s for s in supply.entries if s.region_id == zone.region_id), None
            )
            days = supply_entry.estimated_days_of_supply if supply_entry else None

            # Override level upward if days-of-supply is critically low
            if days is not None:
                if days < settings.shortage_critical_days:
                    level = AlertLevel.CRITICAL
                elif days < settings.shortage_imminent_days and level != AlertLevel.CRITICAL:
                    level = AlertLevel.IMMINENT

            alert_code = f"SA-{uuid.uuid4().hex[:8].upper()}"
            title = f"[{scenario_id}] Fire disaster — {zone.region_name} ({zone.severity})"

            alert = ShortageAlert(
                region_id=zone.region_id,
                alert_code=alert_code,
                alert_type=AlertType.WEATHER,
                alert_level=level,
                status=AlertStatus.ACTIVE,
                title=title,
                description=(
                    f"Fire disaster scenario {scenario_id}. "
                    f"Region {zone.region_name} is {zone.severity}ly affected "
                    f"(distance {zone.distance_km} km from fire origin). "
                    f"Wind-exposed: {zone.wind_exposed}."
                ),
                population_affected=zone.population,
                days_until_shortage=int(days) if days else None,
                current_days_supply=days,
                confidence_score=0.85,
                model_name="fire_disaster_pipeline_v1",
                recommended_actions=[
                    {"action": "Activate emergency food reserves", "priority": 1},
                    {"action": "Begin evacuation-corridor supply staging", "priority": 2},
                    {"action": "Deploy mobile distribution units", "priority": 3},
                ],
                is_active=True,
            )
            self.db.add(alert)
            await self.db.flush()
            await self.db.refresh(alert)

            records.append(AlertRecord(
                alert_id=alert.id,
                alert_code=alert_code,
                region_id=zone.region_id,
                region_name=zone.region_name,
                level=level.value,
                title=title,
            ))

        return GenerateAlertsResult(
            alerts_generated=len(records),
            alerts=records,
        )

    # ── Step 7 — Reroute ─────────────────────────────────────────────

    async def _step7_reroute(
        self, scenario_id: str, zones: FlagZonesResult
    ) -> RerouteResult:
        affected_ids = {z.region_id for z in zones.affected_zones}

        # Find blocked / restricted routes
        result = await self.db.execute(
            select(TransportRoute).where(
                and_(
                    TransportRoute.is_active == True,
                    TransportRoute.operational_status.in_(["blocked", "restricted"]),
                )
            )
        )
        blocked_routes: List[TransportRoute] = list(result.scalars().all())

        if not blocked_routes:
            return RerouteResult(blocked_routes=0, alternative_routes_created=0, alternatives=[])

        # Get safe distribution centers (outside affected zones)
        safe_centers_result = await self.db.execute(
            select(DistributionCenter).where(
                and_(
                    DistributionCenter.is_active == True,
                    DistributionCenter.operational_status == "operational",
                    ~DistributionCenter.region_id.in_(affected_ids),
                )
            )
        )
        safe_centers: List[DistributionCenter] = list(safe_centers_result.scalars().all())

        # For each blocked route, try to create an alternative via Google Maps
        # between safe centers that serve the same origin/dest pair
        maps_svc = GoogleMapsService()
        alternatives: List[RerouteEntry] = []
        seen_pairs = set()

        for route in blocked_routes:
            # Find safe centers in origin and destination regions
            origin_center = await self._find_nearest_safe_center(
                route.origin_region_id, safe_centers, affected_ids
            )
            dest_center = await self._find_nearest_safe_center(
                route.destination_region_id, safe_centers, affected_ids
            )

            if not origin_center or not dest_center:
                continue
            if origin_center.id == dest_center.id:
                continue

            pair_key = (origin_center.id, dest_center.id)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Check if this alternative route already exists
            existing = await self.db.execute(
                select(TransportRoute).where(
                    and_(
                        TransportRoute.origin_center_id == origin_center.id,
                        TransportRoute.destination_center_id == dest_center.id,
                        TransportRoute.is_active == True,
                        TransportRoute.operational_status == "operational",
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            try:
                directions = await maps_svc.get_directions(
                    origin_center.latitude, origin_center.longitude,
                    dest_center.latitude, dest_center.longitude,
                )
            except Exception as e:
                logger.warning(f"[{scenario_id}] Google Maps alt-route failed: {e}")
                continue

            route_code = f"ALT-{scenario_id[-6:]}-{origin_center.center_code}-{dest_center.center_code}"
            alt_route = TransportRoute(
                name=f"[ALT] {origin_center.name} -> {dest_center.name}",
                route_code=route_code,
                origin_center_id=origin_center.id,
                destination_center_id=dest_center.id,
                origin_region_id=origin_center.region_id,
                destination_region_id=dest_center.region_id,
                distance_km=directions["distance_km"],
                estimated_time_hours=directions["duration_hours"],
                path_geometry={"polyline": directions.get("polyline", "")},
                operational_status="operational",
                is_active=True,
            )
            self.db.add(alt_route)
            await self.db.flush()
            await self.db.refresh(alt_route)

            alternatives.append(RerouteEntry(
                route_id=alt_route.id,
                origin=origin_center.name,
                destination=dest_center.name,
                distance_km=directions["distance_km"],
                duration_hours=directions["duration_hours"],
            ))

        return RerouteResult(
            blocked_routes=len(blocked_routes),
            alternative_routes_created=len(alternatives),
            alternatives=alternatives,
        )

    # ── Step 8 — Optimise distribution ───────────────────────────────

    async def _step8_optimize_distribution(
        self,
        scenario_id: str,
        zones: FlagZonesResult,
        displacement: DisplacePopulationResult,
        supply: RecalculateSupplyResult,
    ) -> OptimizeDistributionResult:
        # Build map of receiving regions and their displaced population
        receiving: Dict[int, int] = {}
        for entry in displacement.entries:
            receiving[entry.to_region_id] = (
                receiving.get(entry.to_region_id, 0) + entry.displaced_count
            )

        # Also include affected regions that still have population
        for zone in zones.affected_zones:
            if zone.population and zone.region_id not in receiving:
                sev_mult = {"critical": 0.0, "high": 0.3, "moderate": 0.7}.get(zone.severity, 0.5)
                remaining_pop = int((zone.population or 0) * sev_mult)
                if remaining_pop > 0:
                    receiving[zone.region_id] = receiving.get(zone.region_id, 0) + remaining_pop

        plans: List[DistributionPlanSummary] = []

        for region_id, pop_to_serve in receiving.items():
            if pop_to_serve <= 0:
                continue

            region = await self._get_region(region_id)
            if not region:
                continue

            # Estimate food needed: 0.6 kg per person per day for 7-day plan
            food_tonnes = round(pop_to_serve * 0.6 * 7 / 1000, 2)

            # Count distribution centers in this region
            dc_result = await self.db.execute(
                select(func.count()).select_from(DistributionCenter).where(
                    and_(
                        DistributionCenter.region_id == region_id,
                        DistributionCenter.is_active == True,
                    )
                )
            )
            dc_count = dc_result.scalar() or 0

            plan_code = f"DP-{scenario_id[-6:]}-{region.region_code}"
            plan = DistributionPlan(
                plan_code=plan_code,
                plan_name=f"[{scenario_id}] Emergency plan — {region.name}",
                region_id=region_id,
                trigger_reason=f"Fire disaster {scenario_id}",
                status=PlanStatus.DRAFT,
                population_covered=pop_to_serve,
                total_food_tonnes=food_tonnes,
                duration_days=7,
                distribution_centers_count=dc_count,
                priority_weights={
                    PopulationType.ELDERLY.value: 1.0,
                    PopulationType.CHILDREN.value: 1.0,
                    PopulationType.PREGNANT.value: 1.0,
                    PopulationType.HEALTHCARE_WORKER.value: 0.9,
                    PopulationType.GENERAL.value: 0.7,
                },
                food_allocation={
                    "rice": round(food_tonnes * 0.4, 2),
                    "wheat": round(food_tonnes * 0.2, 2),
                    "legumes": round(food_tonnes * 0.15, 2),
                    "oil": round(food_tonnes * 0.05, 2),
                    "vegetables": round(food_tonnes * 0.2, 2),
                },
            )
            self.db.add(plan)
            await self.db.flush()
            await self.db.refresh(plan)

            plans.append(DistributionPlanSummary(
                plan_id=plan.id,
                plan_code=plan_code,
                region_id=region_id,
                region_name=region.name,
                population_covered=pop_to_serve,
                food_allocated_tonnes=food_tonnes,
                distribution_points=max(dc_count, 1),
                priority_groups=["elderly", "children", "pregnant", "healthcare_worker", "general"],
            ))

        return OptimizeDistributionResult(
            plans_created=len(plans),
            plans=plans,
        )

    # ── Helpers ───────────────────────────────────────────────────────

    async def _get_region(self, region_id: int) -> Optional[Region]:
        result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        return result.scalar_one_or_none()

    async def _find_nearest_safe_center(
        self,
        target_region_id: int,
        safe_centers: List[DistributionCenter],
        affected_ids: set,
    ) -> Optional[DistributionCenter]:
        """Find the nearest safe distribution center to a target region."""
        region = await self._get_region(target_region_id)
        if not region:
            return safe_centers[0] if safe_centers else None

        best = None
        best_dist = float("inf")
        for c in safe_centers:
            if c.region_id in affected_ids:
                continue
            d = self._haversine(region.latitude, region.longitude, c.latitude, c.longitude)
            if d < best_dist:
                best_dist = d
                best = c
        return best

    @staticmethod
    def _worst_severity(a: str, b: str) -> str:
        order = {"critical": 3, "high": 2, "moderate": 1, "": 0}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Bearing from point 1 to point 2 in degrees [0, 360)."""
        dlon = math.radians(lon2 - lon1)
        lat1r = math.radians(lat1)
        lat2r = math.radians(lat2)
        x = math.sin(dlon) * math.cos(lat2r)
        y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon)
        return (math.degrees(math.atan2(x, y)) + 360) % 360

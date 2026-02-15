"""
Distribution Optimization Service

Handles:
- Distribution plan creation and management
- Optimal distribution point placement
- Ration allocation calculation
- Priority-based distribution
- Resource allocation optimization
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from models.distribution_plan import (
    DistributionPlan, DistributionPoint, RationAllocation,
    VulnerablePopulation, DistributionRecord,
    PlanStatus, PopulationType
)
from models.distribution import DistributionCenter
from models.agricultural import Region
from models.inventory import FoodCategory, FoodInventory
from schemas.distribution_plan import (
    DistributionPlanCreate, DistributionPlanUpdate, DistributionPlanResponse,
    DistributionPointCreate, DistributionPointUpdate, DistributionPointResponse,
    RationAllocationCreate, RationAllocationUpdate, RationAllocationResponse,
    VulnerablePopulationCreate, VulnerablePopulationUpdate, VulnerablePopulationResponse,
    DistributionRecordCreate, DistributionRecordResponse,
    DistributionOptimizationRequest, DistributionOptimizationResponse,
    OptimizedDistributionPoint, DistributionAnalytics, CoverageAnalysis, PlanSummary
)
from config import get_settings, DistributionPriority

logger = logging.getLogger(__name__)
settings = get_settings()


class DistributionOptimizationService:
    """Service for optimizing food distribution during crises."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Distribution Plans ====================

    async def create_plan(self, data: DistributionPlanCreate) -> DistributionPlan:
        """Create a new distribution plan."""
        plan_data = data.model_dump()
        plan_data["plan_code"] = f"DP-{uuid.uuid4().hex[:8].upper()}"
        plan_data["status"] = PlanStatus.DRAFT

        # Set default priority weights if not provided
        if not plan_data.get("priority_weights"):
            plan_data["priority_weights"] = {
                PopulationType.ELDERLY.value: 1.0,
                PopulationType.CHILDREN.value: 1.0,
                PopulationType.PREGNANT.value: 1.0,
                PopulationType.IMMUNOCOMPROMISED.value: 1.0,
                PopulationType.HEALTHCARE_WORKER.value: 0.9,
                PopulationType.ESSENTIAL_WORKER.value: 0.8,
                PopulationType.DISABLED.value: 0.9,
                PopulationType.LOW_INCOME.value: 0.85,
                PopulationType.GENERAL.value: 0.7
            }

        plan = DistributionPlan(**plan_data)
        self.db.add(plan)
        await self.db.flush()
        await self.db.refresh(plan)

        logger.info(f"Created distribution plan: {plan.plan_code}")
        return plan

    async def get_plan(self, plan_id: int) -> Optional[DistributionPlan]:
        """Get distribution plan by ID."""
        result = await self.db.execute(
            select(DistributionPlan)
            .options(
                selectinload(DistributionPlan.distribution_points),
                selectinload(DistributionPlan.allocations)
            )
            .where(DistributionPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def update_plan(
        self,
        plan_id: int,
        data: DistributionPlanUpdate
    ) -> Optional[DistributionPlan]:
        """Update distribution plan."""
        plan = await self.get_plan(plan_id)
        if not plan:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == PlanStatus.ACTIVE and not plan.activation_date:
                update_data["activation_date"] = datetime.utcnow()
            elif new_status == PlanStatus.COMPLETED:
                update_data["end_date"] = datetime.utcnow()
                update_data["completion_pct"] = 100

        for field, value in update_data.items():
            setattr(plan, field, value)

        await self.db.flush()
        await self.db.refresh(plan)
        return plan

    async def list_plans(
        self,
        region_id: Optional[int] = None,
        status: Optional[PlanStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[DistributionPlan], int]:
        """List distribution plans."""
        query = select(DistributionPlan)

        if region_id:
            query = query.where(DistributionPlan.region_id == region_id)
        if status:
            query = query.where(DistributionPlan.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.order_by(DistributionPlan.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def approve_plan(
        self,
        plan_id: int,
        approved_by: str
    ) -> Optional[DistributionPlan]:
        """Approve a distribution plan."""
        plan = await self.get_plan(plan_id)
        if not plan:
            return None

        if plan.status != PlanStatus.PENDING_APPROVAL:
            raise ValueError(f"Plan must be in PENDING_APPROVAL status")

        plan.status = PlanStatus.APPROVED
        plan.approved_at = datetime.utcnow()
        plan.approved_by = approved_by

        await self.db.flush()
        await self.db.refresh(plan)

        logger.info(f"Plan approved: {plan.plan_code} by {approved_by}")
        return plan

    async def activate_plan(self, plan_id: int) -> Optional[DistributionPlan]:
        """Activate an approved distribution plan."""
        plan = await self.get_plan(plan_id)
        if not plan:
            return None

        if plan.status != PlanStatus.APPROVED:
            raise ValueError("Plan must be approved before activation")

        plan.status = PlanStatus.ACTIVE
        plan.activation_date = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(plan)

        logger.info(f"Plan activated: {plan.plan_code}")
        return plan

    # ==================== Distribution Points ====================

    async def create_distribution_point(
        self,
        data: DistributionPointCreate
    ) -> DistributionPoint:
        """Create a distribution point."""
        point_data = data.model_dump()
        point_data["point_code"] = f"PT-{uuid.uuid4().hex[:8].upper()}"

        point = DistributionPoint(**point_data)
        self.db.add(point)
        await self.db.flush()
        await self.db.refresh(point)

        # Update plan's point count
        await self._update_plan_counts(data.plan_id)

        logger.info(f"Created distribution point: {point.point_code}")
        return point

    async def _update_plan_counts(self, plan_id: int) -> None:
        """Update distribution center and point counts in plan."""
        point_count = await self.db.execute(
            select(func.count())
            .select_from(DistributionPoint)
            .where(
                and_(
                    DistributionPoint.plan_id == plan_id,
                    DistributionPoint.is_active == True
                )
            )
        )

        plan = await self.get_plan(plan_id)
        if plan:
            plan.distribution_points_count = point_count.scalar()

    async def list_distribution_points(
        self,
        plan_id: int,
        operational_status: Optional[str] = None,
        is_active: bool = True
    ) -> List[DistributionPoint]:
        """List distribution points for a plan."""
        query = select(DistributionPoint).where(
            and_(
                DistributionPoint.plan_id == plan_id,
                DistributionPoint.is_active == is_active
            )
        )

        if operational_status:
            query = query.where(
                DistributionPoint.operational_status == operational_status
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def optimize_point_locations(
        self,
        request: DistributionOptimizationRequest
    ) -> DistributionOptimizationResponse:
        """Optimize distribution point locations using AI."""
        # Get region data
        region_result = await self.db.execute(
            select(Region).where(Region.id == request.region_id)
        )
        region = region_result.scalar_one_or_none()
        if not region:
            raise ValueError(f"Region {request.region_id} not found")

        # Get existing distribution centers
        centers = []
        for center_id in request.distribution_centers:
            center_result = await self.db.execute(
                select(DistributionCenter).where(DistributionCenter.id == center_id)
            )
            center = center_result.scalar_one_or_none()
            if center:
                centers.append(center)

        # Get vulnerable population data
        vulnerable = await self.list_vulnerable_populations(request.region_id)

        # Calculate optimal points using simplified k-means approach
        recommended_points = self._calculate_optimal_points(
            region=region,
            centers=centers,
            population_data=request.population_data,
            available_food=request.available_food,
            vulnerable_populations=vulnerable,
            max_points=request.max_distribution_points
        )

        # Calculate total coverage
        total_population = sum(request.population_data.values())
        covered_population = sum(p.assigned_population for p in recommended_points)
        coverage = covered_population / total_population if total_population > 0 else 0

        # Calculate efficiency score
        efficiency = self._calculate_efficiency_score(
            recommended_points,
            request.available_food
        )

        return DistributionOptimizationResponse(
            region_id=request.region_id,
            optimization_date=datetime.utcnow(),
            recommended_points=recommended_points,
            total_coverage=coverage,
            efficiency_score=efficiency,
            estimated_distribution_days=self._estimate_distribution_days(
                recommended_points,
                request.available_food
            )
        )

    def _calculate_optimal_points(
        self,
        region: Region,
        centers: List[DistributionCenter],
        population_data: Dict[str, int],
        available_food: Dict[str, float],
        vulnerable_populations: List[VulnerablePopulation],
        max_points: int
    ) -> List[OptimizedDistributionPoint]:
        """Calculate optimal distribution point locations."""
        points = []

        # Use distribution centers as primary points
        for center in centers[:max_points]:
            # Calculate population in coverage radius
            coverage_radius = 5.0  # km

            # Estimate assigned population (simplified)
            assigned_pop = sum(population_data.values()) // max(len(centers), 1)

            # Allocate food proportionally
            food_allocation = {
                food: qty / max(len(centers), 1)
                for food, qty in available_food.items()
            }

            # Determine priority groups served
            priority_groups = []
            for vp in vulnerable_populations:
                if vp.priority_level <= 2:
                    priority_groups.append(vp.population_type.value)

            points.append(OptimizedDistributionPoint(
                location={
                    "latitude": center.latitude,
                    "longitude": center.longitude
                },
                assigned_population=assigned_pop,
                coverage_radius_km=coverage_radius,
                food_allocation=food_allocation,
                priority_groups=list(set(priority_groups))
            ))

        # If we need more points, generate additional locations
        if len(points) < max_points and region.latitude and region.longitude:
            remaining = max_points - len(points)
            for i in range(remaining):
                # Generate points around region center
                angle = 2 * np.pi * i / remaining
                radius = 0.05  # Roughly 5km

                lat = region.latitude + radius * np.cos(angle)
                lon = region.longitude + radius * np.sin(angle)

                points.append(OptimizedDistributionPoint(
                    location={"latitude": lat, "longitude": lon},
                    assigned_population=sum(population_data.values()) // max_points,
                    coverage_radius_km=5.0,
                    food_allocation={
                        food: qty / max_points
                        for food, qty in available_food.items()
                    },
                    priority_groups=["general"]
                ))

        return points

    def _calculate_efficiency_score(
        self,
        points: List[OptimizedDistributionPoint],
        available_food: Dict[str, float]
    ) -> float:
        """Calculate distribution efficiency score."""
        if not points or not available_food:
            return 0

        # Score based on food utilization
        total_food = sum(available_food.values())
        allocated_food = sum(
            sum(p.food_allocation.values()) for p in points
        )

        utilization = allocated_food / total_food if total_food > 0 else 0

        # Score based on population coverage
        coverage_score = min(1.0, len(points) / 10)  # Assuming 10 is optimal

        return (utilization + coverage_score) / 2

    def _estimate_distribution_days(
        self,
        points: List[OptimizedDistributionPoint],
        available_food: Dict[str, float]
    ) -> int:
        """Estimate days needed for distribution."""
        if not points:
            return 0

        total_population = sum(p.assigned_population for p in points)
        avg_daily_capacity = 500 * len(points)  # Assume 500 people per point per day

        return max(1, int(np.ceil(total_population / avg_daily_capacity)))

    # ==================== Ration Allocation ====================

    async def create_ration_allocation(
        self,
        data: RationAllocationCreate
    ) -> RationAllocation:
        """Create a ration allocation."""
        allocation_data = data.model_dump()

        # Calculate rations planned
        if data.population_count and data.total_ration_kg:
            allocation_data["rations_planned"] = data.population_count

        # Calculate total cost
        if data.population_count and data.cost_per_ration_usd:
            allocation_data["total_cost_usd"] = (
                data.population_count * data.cost_per_ration_usd
            )

        # Calculate nutritional adequacy
        if data.calories_per_ration and data.daily_caloric_target:
            allocation_data["nutritional_adequacy_pct"] = (
                data.calories_per_ration / data.daily_caloric_target * 100
            )

        allocation = RationAllocation(**allocation_data)
        self.db.add(allocation)
        await self.db.flush()
        await self.db.refresh(allocation)

        return allocation

    async def calculate_rations(
        self,
        plan_id: int,
        available_food: Dict[str, float]
    ) -> List[RationAllocationCreate]:
        """Calculate optimal ration allocations for all population groups."""
        plan = await self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Get vulnerable populations
        populations = await self.list_vulnerable_populations(plan.region_id)

        allocations = []

        # Sort by priority
        populations.sort(key=lambda x: x.priority_level)

        remaining_food = available_food.copy()

        for pop in populations:
            # Calculate ration based on caloric needs
            daily_calories = pop.daily_caloric_need or settings.caloric_requirement_adult

            # Build ration composition
            ration = self._build_ration_composition(
                daily_calories,
                remaining_food,
                pop.special_dietary_needs
            )

            if not ration["composition"]:
                continue

            # Deduct from available food
            for food, qty in ration["composition"].items():
                if food in remaining_food:
                    remaining_food[food] -= qty * pop.total_count
                    remaining_food[food] = max(0, remaining_food[food])

            allocations.append(RationAllocationCreate(
                plan_id=plan_id,
                allocation_date=datetime.utcnow(),
                population_type=pop.population_type,
                population_count=pop.total_count,
                households_count=pop.households_count,
                ration_composition=ration["composition"],
                total_ration_kg=ration["total_kg"],
                calories_per_ration=ration["calories"],
                daily_caloric_target=daily_calories,
                cost_per_ration_usd=ration["cost"]
            ))

        return allocations

    def _build_ration_composition(
        self,
        target_calories: int,
        available_food: Dict[str, float],
        dietary_needs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Build a ration composition based on available food."""
        composition = {}
        total_calories = 0
        total_kg = 0
        cost = 0

        # Standard ration components (simplified)
        ration_template = {
            "rice": {"kg": 0.4, "cal_per_kg": 3600, "cost_per_kg": 0.8},
            "wheat": {"kg": 0.2, "cal_per_kg": 3400, "cost_per_kg": 0.5},
            "legumes": {"kg": 0.1, "cal_per_kg": 3500, "cost_per_kg": 1.0},
            "oil": {"kg": 0.05, "cal_per_kg": 8800, "cost_per_kg": 2.0},
            "vegetables": {"kg": 0.2, "cal_per_kg": 250, "cost_per_kg": 1.5},
        }

        for food, specs in ration_template.items():
            # Check if food is available
            available = available_food.get(food, 0)
            if available > 0:
                qty = min(specs["kg"], available)
                composition[food] = qty
                total_calories += qty * specs["cal_per_kg"]
                total_kg += qty
                cost += qty * specs["cost_per_kg"]

        return {
            "composition": composition,
            "total_kg": total_kg,
            "calories": int(total_calories),
            "cost": round(cost, 2)
        }

    # ==================== Vulnerable Populations ====================

    async def create_vulnerable_population(
        self,
        data: VulnerablePopulationCreate
    ) -> VulnerablePopulation:
        """Create a vulnerable population record."""
        population = VulnerablePopulation(**data.model_dump())
        self.db.add(population)
        await self.db.flush()
        await self.db.refresh(population)
        return population

    async def list_vulnerable_populations(
        self,
        region_id: int
    ) -> List[VulnerablePopulation]:
        """List vulnerable populations in a region."""
        result = await self.db.execute(
            select(VulnerablePopulation)
            .where(VulnerablePopulation.region_id == region_id)
            .order_by(VulnerablePopulation.priority_level)
        )
        return list(result.scalars().all())

    async def get_priority_population_counts(
        self,
        region_id: int
    ) -> Dict[str, int]:
        """Get population counts by priority type."""
        populations = await self.list_vulnerable_populations(region_id)

        counts = {}
        for pop in populations:
            counts[pop.population_type.value] = pop.total_count

        return counts

    # ==================== Distribution Records ====================

    async def record_distribution(
        self,
        data: DistributionRecordCreate
    ) -> DistributionRecord:
        """Record a distribution transaction."""
        record_data = data.model_dump()
        record_data["transaction_code"] = f"TX-{uuid.uuid4().hex[:10].upper()}"
        record_data["distribution_date"] = datetime.utcnow()

        # Calculate total calories
        total_calories = 0
        for item, qty in data.items_distributed.items():
            # Simplified calorie calculation
            cal_per_kg = {"rice": 3600, "wheat": 3400, "legumes": 3500}.get(item, 1500)
            total_calories += qty * cal_per_kg

        record_data["total_calories"] = int(total_calories)

        record = DistributionRecord(**record_data)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)

        # Update plan progress
        await self._update_distribution_progress(data.plan_id, data.total_weight_kg)

        # Update distribution point stats
        await self._update_point_stats(data.distribution_point_id)

        return record

    async def _update_distribution_progress(
        self,
        plan_id: int,
        distributed_kg: float
    ) -> None:
        """Update plan distribution progress."""
        plan = await self.get_plan(plan_id)
        if not plan:
            return

        plan.food_distributed_tonnes = (
            (plan.food_distributed_tonnes or 0) + distributed_kg / 1000
        )
        plan.beneficiaries_served = (plan.beneficiaries_served or 0) + 1

        if plan.total_food_tonnes and plan.total_food_tonnes > 0:
            plan.completion_pct = min(100, (
                plan.food_distributed_tonnes / plan.total_food_tonnes * 100
            ))

    async def _update_point_stats(self, point_id: int) -> None:
        """Update distribution point statistics."""
        result = await self.db.execute(
            select(DistributionPoint).where(DistributionPoint.id == point_id)
        )
        point = result.scalar_one_or_none()
        if not point:
            return

        point.total_beneficiaries_served = (point.total_beneficiaries_served or 0) + 1

    # ==================== Analytics ====================

    async def get_distribution_analytics(
        self,
        plan_id: int
    ) -> DistributionAnalytics:
        """Get analytics for a distribution plan."""
        plan = await self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Get all records
        records_result = await self.db.execute(
            select(DistributionRecord)
            .where(DistributionRecord.plan_id == plan_id)
        )
        records = records_result.scalars().all()

        # Calculate by population type
        by_type = {}
        for record in records:
            ptype = record.population_type.value if record.population_type else "unknown"
            if ptype not in by_type:
                by_type[ptype] = {
                    "beneficiaries": 0,
                    "food_kg": 0,
                    "calories": 0
                }
            by_type[ptype]["beneficiaries"] += 1
            by_type[ptype]["food_kg"] += record.total_weight_kg
            by_type[ptype]["calories"] += record.total_calories or 0

        # Calculate by distribution point
        points = await self.list_distribution_points(plan_id)
        by_point = [
            {
                "point_id": p.id,
                "point_name": p.point_name,
                "beneficiaries_served": p.total_beneficiaries_served or 0,
                "food_distributed_tonnes": p.total_food_distributed_tonnes or 0
            }
            for p in points
        ]

        # Daily distribution rate
        daily_rate = []
        if records:
            records_by_date = {}
            for record in records:
                date = record.distribution_date.date()
                if date not in records_by_date:
                    records_by_date[date] = {"count": 0, "weight": 0}
                records_by_date[date]["count"] += 1
                records_by_date[date]["weight"] += record.total_weight_kg

            daily_rate = [
                {"date": date.isoformat(), **stats}
                for date, stats in sorted(records_by_date.items())
            ]

        # Efficiency metrics
        total_beneficiaries = len(records)
        planned_beneficiaries = plan.population_covered or 1

        return DistributionAnalytics(
            plan_id=plan_id,
            period_start=plan.activation_date or plan.created_at,
            period_end=plan.end_date or datetime.utcnow(),
            total_beneficiaries=total_beneficiaries,
            total_food_distributed_tonnes=plan.food_distributed_tonnes or 0,
            by_population_type=by_type,
            by_distribution_point=by_point,
            daily_distribution_rate=daily_rate,
            efficiency_metrics={
                "coverage_rate": total_beneficiaries / planned_beneficiaries,
                "completion_percentage": plan.completion_pct or 0,
                "avg_daily_beneficiaries": total_beneficiaries / max(1, len(daily_rate)),
                "points_utilization": sum(1 for p in points if (p.total_beneficiaries_served or 0) > 0) / max(1, len(points))
            }
        )

    async def get_coverage_analysis(
        self,
        region_id: int,
        plan_id: Optional[int] = None
    ) -> CoverageAnalysis:
        """Analyze distribution coverage for a region."""
        # Get region info
        region_result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        region = region_result.scalar_one_or_none()
        if not region:
            raise ValueError(f"Region {region_id} not found")

        # Get vulnerable populations
        populations = await self.list_vulnerable_populations(region_id)
        total_population = sum(p.total_count for p in populations)

        # Get active plan distribution points
        covered_population = 0
        if plan_id:
            points = await self.list_distribution_points(plan_id)
            covered_population = sum(p.assigned_population or 0 for p in points)

        # Coverage by population type
        coverage_by_type = {}
        for pop in populations:
            # Simplified coverage calculation
            type_coverage = (covered_population / total_population) if total_population > 0 else 0
            coverage_by_type[pop.population_type.value] = type_coverage

        # Identify underserved areas
        underserved = []
        for pop in populations:
            if pop.avg_distance_to_distribution_km and pop.avg_distance_to_distribution_km > 10:
                underserved.append({
                    "population_type": pop.population_type.value,
                    "count": pop.total_count,
                    "avg_distance_km": pop.avg_distance_to_distribution_km,
                    "issue": "Distance to distribution point exceeds 10km"
                })

        # Generate recommendations
        recommendations = []
        coverage_pct = (covered_population / total_population * 100) if total_population > 0 else 0

        if coverage_pct < 80:
            recommendations.append("Increase number of distribution points")
        if underserved:
            recommendations.append("Add mobile distribution for remote areas")
        if any(p.mobility_limited_pct and p.mobility_limited_pct > 20 for p in populations):
            recommendations.append("Implement home delivery for mobility-limited populations")

        return CoverageAnalysis(
            region_id=region_id,
            total_population=total_population,
            covered_population=covered_population,
            coverage_percentage=coverage_pct,
            coverage_by_type=coverage_by_type,
            underserved_areas=underserved,
            recommendations=recommendations
        )

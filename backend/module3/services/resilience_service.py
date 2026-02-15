"""
Agricultural Resilience Planning Service

Handles:
- Urban agriculture site management
- Crop diversification planning
- Resilience recommendations
- Land conversion opportunities
- Long-term food security planning
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from models.resilience import (
    UrbanAgricultureSite, CropDiversificationPlan,
    ResilienceRecommendation, LandConversionOpportunity,
    SiteType, ProjectStatus
)
from models.agricultural import Region, Crop, AgriculturalProduction
from models.dependency import RegionalDependency
from schemas.resilience import (
    UrbanAgricultureSiteCreate, UrbanAgricultureSiteUpdate, UrbanAgricultureSiteResponse,
    CropDiversificationPlanCreate, CropDiversificationPlanUpdate, CropDiversificationPlanResponse,
    ResilienceRecommendationCreate, ResilienceRecommendationUpdate, ResilienceRecommendationResponse,
    LandConversionOpportunityCreate, LandConversionOpportunityResponse,
    ResilienceAssessment, FoodProductionPotential,
    ClimateAdaptationPlan, RegionalResilienceSummary, UrbanAgSummary
)
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AgriculturalResilienceService:
    """Service for agricultural resilience planning."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Urban Agriculture ====================

    async def create_urban_ag_site(
        self,
        data: UrbanAgricultureSiteCreate
    ) -> UrbanAgricultureSite:
        """Create an urban agriculture site."""
        site_data = data.model_dump()
        site_data["site_code"] = f"UA-{uuid.uuid4().hex[:8].upper()}"
        site_data["status"] = ProjectStatus.PROPOSED

        site = UrbanAgricultureSite(**site_data)
        self.db.add(site)
        await self.db.flush()
        await self.db.refresh(site)

        logger.info(f"Created urban agriculture site: {site.site_code}")
        return site

    async def get_urban_ag_site(self, site_id: int) -> Optional[UrbanAgricultureSite]:
        """Get urban agriculture site by ID."""
        result = await self.db.execute(
            select(UrbanAgricultureSite).where(UrbanAgricultureSite.id == site_id)
        )
        return result.scalar_one_or_none()

    async def list_urban_ag_sites(
        self,
        region_id: Optional[int] = None,
        site_type: Optional[SiteType] = None,
        status: Optional[ProjectStatus] = None,
        is_active: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[UrbanAgricultureSite], int]:
        """List urban agriculture sites."""
        query = select(UrbanAgricultureSite).where(
            UrbanAgricultureSite.is_active == is_active
        )

        if region_id:
            query = query.where(UrbanAgricultureSite.region_id == region_id)
        if site_type:
            query = query.where(UrbanAgricultureSite.site_type == site_type)
        if status:
            query = query.where(UrbanAgricultureSite.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    async def update_urban_ag_site(
        self,
        site_id: int,
        data: UrbanAgricultureSiteUpdate
    ) -> Optional[UrbanAgricultureSite]:
        """Update an urban agriculture site."""
        site = await self.get_urban_ag_site(site_id)
        if not site:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transition to operational
        if update_data.get("status") == ProjectStatus.OPERATIONAL and not site.established_date:
            site.established_date = datetime.utcnow()

        for field, value in update_data.items():
            setattr(site, field, value)

        await self.db.flush()
        await self.db.refresh(site)
        return site

    async def get_urban_ag_summary(self, region_id: int) -> UrbanAgSummary:
        """Get urban agriculture summary for a region."""
        sites, _ = await self.list_urban_ag_sites(region_id=region_id)

        operational = [s for s in sites if s.status == ProjectStatus.OPERATIONAL]

        by_type = {}
        for site in sites:
            stype = site.site_type.value
            by_type[stype] = by_type.get(stype, 0) + 1

        return UrbanAgSummary(
            region_id=region_id,
            total_sites=len(sites),
            operational_sites=len(operational),
            total_area_sqm=sum(s.total_area_sqm or 0 for s in sites),
            total_production_tonnes_year=sum(
                s.current_production_tonnes_year or 0 for s in operational
            ),
            households_served=sum(s.households_supplied or 0 for s in operational),
            by_type=by_type
        )

    # ==================== Crop Diversification ====================

    async def create_diversification_plan(
        self,
        data: CropDiversificationPlanCreate
    ) -> CropDiversificationPlan:
        """Create a crop diversification plan."""
        plan_data = data.model_dump()
        plan_data["plan_code"] = f"CD-{uuid.uuid4().hex[:8].upper()}"
        plan_data["status"] = ProjectStatus.PROPOSED

        # Calculate diversity indices
        current_diversity = self._calculate_diversity_index(data.current_crop_mix)
        target_diversity = self._calculate_diversity_index(data.target_crop_mix)

        plan_data["current_diversity_index"] = current_diversity
        plan_data["target_diversity_index"] = target_diversity
        plan_data["current_risk_score"] = 1 - current_diversity  # Lower diversity = higher risk
        plan_data["target_risk_score"] = 1 - target_diversity

        plan = CropDiversificationPlan(**plan_data)
        self.db.add(plan)
        await self.db.flush()
        await self.db.refresh(plan)

        logger.info(f"Created diversification plan: {plan.plan_code}")
        return plan

    def _calculate_diversity_index(self, crop_mix: Dict[str, float]) -> float:
        """Calculate Simpson's Diversity Index."""
        if not crop_mix:
            return 0

        total = sum(crop_mix.values())
        if total == 0:
            return 0

        # Simpson's index: 1 - sum(p^2)
        proportions = [v / total for v in crop_mix.values()]
        return 1 - sum(p ** 2 for p in proportions)

    async def get_diversification_plan(
        self,
        plan_id: int
    ) -> Optional[CropDiversificationPlan]:
        """Get diversification plan by ID."""
        result = await self.db.execute(
            select(CropDiversificationPlan)
            .where(CropDiversificationPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def list_diversification_plans(
        self,
        region_id: Optional[int] = None,
        status: Optional[ProjectStatus] = None
    ) -> List[CropDiversificationPlan]:
        """List crop diversification plans."""
        query = select(CropDiversificationPlan)

        if region_id:
            query = query.where(CropDiversificationPlan.region_id == region_id)
        if status:
            query = query.where(CropDiversificationPlan.status == status)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def generate_diversification_recommendations(
        self,
        region_id: int
    ) -> CropDiversificationPlanCreate:
        """Generate AI-based crop diversification recommendations."""
        # Get current production data
        production_result = await self.db.execute(
            select(AgriculturalProduction, Crop)
            .join(Crop, AgriculturalProduction.crop_id == Crop.id)
            .where(
                and_(
                    AgriculturalProduction.region_id == region_id,
                    AgriculturalProduction.year >= datetime.now().year - 3
                )
            )
        )
        productions = production_result.all()

        # Calculate current crop mix
        current_mix = {}
        crop_totals = {}
        for prod, crop in productions:
            if crop.name not in crop_totals:
                crop_totals[crop.name] = 0
            crop_totals[crop.name] += prod.production_tonnes or 0

        total_production = sum(crop_totals.values())
        if total_production > 0:
            current_mix = {
                crop: tonnes / total_production * 100
                for crop, tonnes in crop_totals.items()
            }

        # Identify vulnerable crops (high dependence on single crops)
        vulnerable = [
            crop for crop, pct in current_mix.items()
            if pct > 30
        ]

        # Get region climate data
        region_result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        region = region_result.scalar_one_or_none()

        # Generate target mix (more balanced)
        target_mix = self._generate_target_crop_mix(current_mix, region)

        # Identify recommended crops
        current_crops = set(current_mix.keys())
        target_crops = set(target_mix.keys())
        recommended = list(target_crops - current_crops)
        to_reduce = [c for c in vulnerable if current_mix.get(c, 0) > target_mix.get(c, 0)]

        return CropDiversificationPlanCreate(
            region_id=region_id,
            plan_name=f"Diversification Plan - {region.name if region else 'Region'}",
            current_crop_mix=current_mix,
            target_crop_mix=target_mix,
            vulnerable_crops=vulnerable,
            recommended_crops=recommended,
            crops_to_reduce=to_reduce,
            implementation_phases=[
                {"phase": 1, "duration_months": 12, "actions": ["Pilot new crops"]},
                {"phase": 2, "duration_months": 24, "actions": ["Scale successful crops"]},
                {"phase": 3, "duration_months": 12, "actions": ["Optimize mix"]}
            ],
            estimated_duration_years=4,
            investment_required_usd=self._estimate_diversification_cost(region_id)
        )

    def _generate_target_crop_mix(
        self,
        current_mix: Dict[str, float],
        region: Optional[Region]
    ) -> Dict[str, float]:
        """Generate target crop mix for better resilience."""
        # Ideal diversified mix
        ideal_categories = {
            "staple_grains": 35,  # Rice, wheat, etc.
            "legumes": 15,
            "vegetables": 20,
            "fruits": 10,
            "tubers": 10,
            "oil_crops": 10
        }

        # Adjust based on current mix
        target = {}

        # Keep some existing crops but limit concentration
        for crop, pct in current_mix.items():
            target[crop] = min(25, pct * 0.8)  # Reduce concentration

        # Add missing categories
        remaining = 100 - sum(target.values())
        if remaining > 0:
            # Add recommended crops
            recommendations = ["legumes", "drought_resistant_millet", "vegetables"]
            for crop in recommendations:
                if crop not in target and remaining > 0:
                    allocation = min(remaining, 15)
                    target[crop] = allocation
                    remaining -= allocation

        # Normalize to 100%
        total = sum(target.values())
        if total > 0:
            target = {k: v / total * 100 for k, v in target.items()}

        return target

    def _estimate_diversification_cost(self, region_id: int) -> float:
        """Estimate cost of diversification."""
        # Simplified cost estimation
        base_cost = 50000  # Base cost per region
        return base_cost

    # ==================== Resilience Recommendations ====================

    async def create_recommendation(
        self,
        data: ResilienceRecommendationCreate
    ) -> ResilienceRecommendation:
        """Create a resilience recommendation."""
        rec_data = data.model_dump()
        rec_data["recommendation_code"] = f"RR-{uuid.uuid4().hex[:8].upper()}"
        rec_data["status"] = "generated"
        rec_data["generated_at"] = datetime.utcnow()

        recommendation = ResilienceRecommendation(**rec_data)
        self.db.add(recommendation)
        await self.db.flush()
        await self.db.refresh(recommendation)

        return recommendation

    async def list_recommendations(
        self,
        region_id: Optional[int] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        is_active: bool = True,
        limit: int = 50
    ) -> List[ResilienceRecommendation]:
        """List resilience recommendations."""
        query = select(ResilienceRecommendation).where(
            ResilienceRecommendation.is_active == is_active
        )

        if region_id:
            query = query.where(ResilienceRecommendation.region_id == region_id)
        if category:
            query = query.where(ResilienceRecommendation.category == category)
        if status:
            query = query.where(ResilienceRecommendation.status == status)

        query = query.order_by(ResilienceRecommendation.priority)
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def generate_recommendations(
        self,
        region_id: int
    ) -> List[ResilienceRecommendation]:
        """Generate AI-based resilience recommendations for a region."""
        # Get region data
        region_result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        region = region_result.scalar_one_or_none()
        if not region:
            raise ValueError(f"Region {region_id} not found")

        # Get dependency data
        dependency_result = await self.db.execute(
            select(RegionalDependency).where(RegionalDependency.region_id == region_id)
        )
        dependency = dependency_result.scalar_one_or_none()

        # Get urban agriculture summary
        urban_ag = await self.get_urban_ag_summary(region_id)

        # Generate recommendations based on analysis
        recommendations = []

        # Production recommendations
        if region.arable_land_sq_km and region.arable_land_sq_km > 0:
            if region.irrigation_coverage and region.irrigation_coverage < 50:
                recommendations.append(
                    await self._create_recommendation(
                        region_id=region_id,
                        category="production",
                        title="Expand Irrigation Infrastructure",
                        description=(
                            f"Current irrigation coverage is {region.irrigation_coverage}%. "
                            "Expanding irrigation would increase production resilience."
                        ),
                        priority=1,
                        urgency="short_term",
                        impact_score=0.8,
                        feasibility_score=0.6,
                        estimated_cost_usd=500000
                    )
                )

        # Storage recommendations
        if dependency and dependency.strategic_reserve_days:
            if dependency.strategic_reserve_days < 30:
                recommendations.append(
                    await self._create_recommendation(
                        region_id=region_id,
                        category="storage",
                        title="Increase Strategic Food Reserves",
                        description=(
                            f"Current reserves of {dependency.strategic_reserve_days:.0f} days "
                            "are below the recommended 45 days."
                        ),
                        priority=1,
                        urgency="immediate",
                        impact_score=0.9,
                        feasibility_score=0.7,
                        estimated_cost_usd=200000
                    )
                )

        # Urban agriculture recommendations
        if urban_ag.operational_sites < 5:
            recommendations.append(
                await self._create_recommendation(
                    region_id=region_id,
                    category="urban_agriculture",
                    title="Expand Urban Agriculture Program",
                    description=(
                        "Developing more urban agriculture sites would increase "
                        "local food production and reduce import dependency."
                    ),
                    priority=2,
                    urgency="medium_term",
                    impact_score=0.6,
                    feasibility_score=0.8,
                    estimated_cost_usd=100000
                )
            )

        # Distribution recommendations
        if dependency and dependency.port_dependency:
            recommendations.append(
                await self._create_recommendation(
                    region_id=region_id,
                    category="distribution",
                    title="Reduce Port Dependency",
                    description=(
                        "High dependency on a single port creates vulnerability. "
                        "Develop alternative import channels."
                    ),
                    priority=2,
                    urgency="medium_term",
                    impact_score=0.7,
                    feasibility_score=0.5,
                    estimated_cost_usd=1000000
                )
            )

        return recommendations

    async def _create_recommendation(
        self,
        region_id: int,
        category: str,
        title: str,
        description: str,
        priority: int,
        urgency: str,
        impact_score: float,
        feasibility_score: float,
        estimated_cost_usd: float
    ) -> ResilienceRecommendation:
        """Helper to create a recommendation."""
        data = ResilienceRecommendationCreate(
            region_id=region_id,
            category=category,
            title=title,
            description=description,
            priority=priority,
            urgency=urgency,
            impact_score=impact_score,
            feasibility_score=feasibility_score,
            estimated_cost_usd=estimated_cost_usd,
            model_name="resilience_recommender_v1",
            confidence_score=0.75
        )
        return await self.create_recommendation(data)

    # ==================== Land Conversion ====================

    async def create_land_opportunity(
        self,
        data: LandConversionOpportunityCreate
    ) -> LandConversionOpportunity:
        """Create a land conversion opportunity."""
        opportunity = LandConversionOpportunity(**data.model_dump())
        opportunity.identified_date = datetime.utcnow()
        self.db.add(opportunity)
        await self.db.flush()
        await self.db.refresh(opportunity)
        return opportunity

    async def list_land_opportunities(
        self,
        region_id: Optional[int] = None,
        current_use: Optional[str] = None,
        min_feasibility: Optional[float] = None,
        is_active: bool = True
    ) -> List[LandConversionOpportunity]:
        """List land conversion opportunities."""
        query = select(LandConversionOpportunity).where(
            LandConversionOpportunity.is_active == is_active
        )

        if region_id:
            query = query.where(LandConversionOpportunity.region_id == region_id)
        if current_use:
            query = query.where(LandConversionOpportunity.current_use == current_use)
        if min_feasibility is not None:
            query = query.where(
                LandConversionOpportunity.feasibility_score >= min_feasibility
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Assessments ====================

    async def assess_resilience(self, region_id: int) -> ResilienceAssessment:
        """Perform comprehensive resilience assessment for a region."""
        # Get all relevant data
        region_result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        region = region_result.scalar_one_or_none()
        if not region:
            raise ValueError(f"Region {region_id} not found")

        dependency_result = await self.db.execute(
            select(RegionalDependency).where(RegionalDependency.region_id == region_id)
        )
        dependency = dependency_result.scalar_one_or_none()

        urban_ag = await self.get_urban_ag_summary(region_id)
        recommendations = await self.list_recommendations(region_id=region_id)

        # Calculate component scores
        production_resilience = self._calculate_production_resilience(region, urban_ag)
        distribution_resilience = self._calculate_distribution_resilience(dependency)
        storage_resilience = self._calculate_storage_resilience(dependency)
        economic_resilience = self._calculate_economic_resilience(dependency)

        # Overall score
        overall_score = np.mean([
            production_resilience,
            distribution_resilience,
            storage_resilience,
            economic_resilience
        ])

        # SWOT analysis
        strengths = []
        weaknesses = []
        opportunities = []
        threats = []

        if production_resilience > 0.6:
            strengths.append("Strong local production capacity")
        else:
            weaknesses.append("Limited local production")

        if dependency and dependency.strategic_reserve_days and dependency.strategic_reserve_days > 30:
            strengths.append("Adequate strategic reserves")
        else:
            weaknesses.append("Insufficient strategic reserves")

        if urban_ag.operational_sites > 5:
            strengths.append("Active urban agriculture program")
        else:
            opportunities.append("Potential for urban agriculture expansion")

        if region.drought_risk and region.drought_risk > 0.5:
            threats.append("High drought risk")
        if region.flood_risk and region.flood_risk > 0.5:
            threats.append("High flood risk")

        # Get priority recommendations
        priority_recs = [
            {
                "title": r.title,
                "priority": r.priority,
                "urgency": r.urgency,
                "impact_score": r.impact_score
            }
            for r in recommendations[:5]
        ]

        return ResilienceAssessment(
            region_id=region_id,
            assessment_date=datetime.utcnow(),
            overall_resilience_score=overall_score,
            production_resilience=production_resilience,
            distribution_resilience=distribution_resilience,
            storage_resilience=storage_resilience,
            economic_resilience=economic_resilience,
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            threats=threats,
            priority_recommendations=priority_recs
        )

    def _calculate_production_resilience(
        self,
        region: Region,
        urban_ag: UrbanAgSummary
    ) -> float:
        """Calculate production resilience score."""
        score = 0.5  # Base score

        # Arable land bonus
        if region.arable_land_sq_km and region.arable_land_sq_km > 100:
            score += 0.15

        # Irrigation bonus
        if region.irrigation_coverage and region.irrigation_coverage > 50:
            score += 0.15

        # Urban agriculture bonus
        if urban_ag.operational_sites > 5:
            score += 0.1

        # Climate risk penalty
        if region.drought_risk and region.drought_risk > 0.5:
            score -= 0.1
        if region.flood_risk and region.flood_risk > 0.5:
            score -= 0.1

        return max(0, min(1, score))

    def _calculate_distribution_resilience(
        self,
        dependency: Optional[RegionalDependency]
    ) -> float:
        """Calculate distribution resilience score."""
        if not dependency:
            return 0.5

        score = 0.6  # Base score

        # Single source penalty
        if dependency.single_source_dependency:
            score -= 0.2

        # Port dependency penalty
        if dependency.port_dependency:
            score -= 0.15

        # Multiple sources bonus
        if dependency.num_import_sources and dependency.num_import_sources > 3:
            score += 0.15

        return max(0, min(1, score))

    def _calculate_storage_resilience(
        self,
        dependency: Optional[RegionalDependency]
    ) -> float:
        """Calculate storage resilience score."""
        if not dependency:
            return 0.5

        score = 0.3  # Base score

        # Reserve days impact
        if dependency.strategic_reserve_days:
            if dependency.strategic_reserve_days >= 45:
                score += 0.5
            elif dependency.strategic_reserve_days >= 30:
                score += 0.3
            elif dependency.strategic_reserve_days >= 15:
                score += 0.1

        # Cold storage impact
        if dependency.cold_storage_days and dependency.cold_storage_days >= 7:
            score += 0.2

        return max(0, min(1, score))

    def _calculate_economic_resilience(
        self,
        dependency: Optional[RegionalDependency]
    ) -> float:
        """Calculate economic resilience score."""
        if not dependency:
            return 0.5

        score = 0.6  # Base score

        # Import dependency penalty
        if dependency.import_dependency_pct:
            if dependency.import_dependency_pct > 70:
                score -= 0.3
            elif dependency.import_dependency_pct > 50:
                score -= 0.15

        # Aid dependency penalty
        if dependency.aid_dependency_pct and dependency.aid_dependency_pct > 30:
            score -= 0.2

        return max(0, min(1, score))

    async def get_regional_summary(self, region_id: int) -> RegionalResilienceSummary:
        """Get resilience summary for a region."""
        region_result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        region = region_result.scalar_one_or_none()
        if not region:
            raise ValueError(f"Region {region_id} not found")

        # Get assessment
        assessment = await self.assess_resilience(region_id)

        # Get active projects
        urban_ag_sites, _ = await self.list_urban_ag_sites(
            region_id=region_id,
            status=ProjectStatus.OPERATIONAL
        )
        diversification_plans = await self.list_diversification_plans(
            region_id=region_id,
            status=ProjectStatus.APPROVED
        )

        active_projects = len(urban_ag_sites) + len(diversification_plans)

        # Get pending recommendations
        recommendations = await self.list_recommendations(
            region_id=region_id,
            status="generated"
        )

        # Determine trend
        trend = "stable"  # Would compare with historical assessments

        return RegionalResilienceSummary(
            region_id=region_id,
            region_name=region.name,
            resilience_score=assessment.overall_resilience_score,
            trend=trend,
            key_metrics={
                "production": assessment.production_resilience,
                "distribution": assessment.distribution_resilience,
                "storage": assessment.storage_resilience,
                "economic": assessment.economic_resilience
            },
            active_projects=active_projects,
            recommendations_pending=len(recommendations),
            recent_improvements=assessment.strengths
        )

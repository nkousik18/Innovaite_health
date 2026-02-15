"""
Food Dependency Analysis Service

Handles:
- Regional food dependency profiling
- Import source tracking and risk assessment
- Vulnerability assessments
- Import/Export monitoring
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from models.dependency import (
    RegionalDependency, ImportSource, FoodImport,
    VulnerabilityAssessment, RiskLevel
)
from models.agricultural import Region
from models.inventory import FoodCategory, FoodInventory
from schemas.dependency import (
    RegionalDependencyCreate, RegionalDependencyUpdate, RegionalDependencyResponse,
    ImportSourceCreate, ImportSourceUpdate, ImportSourceResponse,
    FoodImportCreate, FoodImportUpdate, FoodImportResponse,
    VulnerabilityAssessmentCreate, VulnerabilityAssessmentResponse,
    DependencyProfile, ImportSummary, DependencyRiskAnalysis,
    ImportDisruptionScenario
)
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FoodDependencyService:
    """Service for analyzing regional food dependencies and vulnerabilities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Regional Dependency ====================

    async def create_dependency_profile(
        self,
        data: RegionalDependencyCreate
    ) -> RegionalDependency:
        """Create a regional dependency profile."""
        # Calculate risk level based on metrics
        risk_level = self._calculate_risk_level(data)
        risk_score = self._calculate_risk_score(data)

        dependency_data = data.model_dump()
        dependency_data["overall_risk_level"] = risk_level
        dependency_data["risk_score"] = risk_score
        dependency_data["last_assessment_date"] = datetime.utcnow()

        # Determine reserve status
        if data.strategic_reserve_days:
            if data.strategic_reserve_days < 7:
                dependency_data["reserve_status"] = "critical"
            elif data.strategic_reserve_days < 15:
                dependency_data["reserve_status"] = "low"
            elif data.strategic_reserve_days < 30:
                dependency_data["reserve_status"] = "adequate"
            else:
                dependency_data["reserve_status"] = "surplus"

        # Check for single source dependency
        if data.num_import_sources and data.num_import_sources == 1:
            dependency_data["single_source_dependency"] = True

        dependency = RegionalDependency(**dependency_data)
        self.db.add(dependency)
        await self.db.flush()
        await self.db.refresh(dependency)

        logger.info(f"Created dependency profile for region {data.region_id}")
        return dependency

    def _calculate_risk_level(self, data: RegionalDependencyCreate) -> RiskLevel:
        """Calculate overall risk level."""
        risk_factors = 0

        # High import dependency
        if data.import_dependency_pct and data.import_dependency_pct > 60:
            risk_factors += 2
        elif data.import_dependency_pct and data.import_dependency_pct > 40:
            risk_factors += 1

        # Low reserves
        if data.strategic_reserve_days and data.strategic_reserve_days < 15:
            risk_factors += 2
        elif data.strategic_reserve_days and data.strategic_reserve_days < 30:
            risk_factors += 1

        # Limited sources
        if data.num_import_sources and data.num_import_sources <= 2:
            risk_factors += 1

        # Port dependency
        if data.primary_port_name:  # Implies port dependency
            risk_factors += 1

        if risk_factors >= 5:
            return RiskLevel.CRITICAL
        elif risk_factors >= 3:
            return RiskLevel.HIGH
        elif risk_factors >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _calculate_risk_score(self, data: RegionalDependencyCreate) -> float:
        """Calculate numerical risk score (0-100)."""
        score = 0

        # Import dependency contribution (max 30 points)
        if data.import_dependency_pct:
            score += min(30, data.import_dependency_pct * 0.5)

        # Reserve days contribution (max 30 points)
        if data.strategic_reserve_days:
            if data.strategic_reserve_days < 7:
                score += 30
            elif data.strategic_reserve_days < 15:
                score += 25
            elif data.strategic_reserve_days < 30:
                score += 15
            elif data.strategic_reserve_days < 45:
                score += 5

        # Source diversity contribution (max 20 points)
        if data.num_import_sources:
            if data.num_import_sources == 1:
                score += 20
            elif data.num_import_sources == 2:
                score += 15
            elif data.num_import_sources <= 4:
                score += 10

        # Cold storage contribution (max 10 points)
        if data.cold_storage_days and data.cold_storage_days < 3:
            score += 10
        elif data.cold_storage_days and data.cold_storage_days < 7:
            score += 5

        # Population at risk contribution (max 10 points)
        if data.population_at_risk and data.population_at_risk > 1000000:
            score += 10
        elif data.population_at_risk and data.population_at_risk > 100000:
            score += 5

        return min(100, score)

    async def get_dependency(self, region_id: int) -> Optional[RegionalDependency]:
        """Get dependency profile by region ID."""
        result = await self.db.execute(
            select(RegionalDependency)
            .options(selectinload(RegionalDependency.import_sources))
            .where(RegionalDependency.region_id == region_id)
        )
        return result.scalar_one_or_none()

    async def update_dependency(
        self,
        region_id: int,
        data: RegionalDependencyUpdate
    ) -> Optional[RegionalDependency]:
        """Update dependency profile."""
        dependency = await self.get_dependency(region_id)
        if not dependency:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Recalculate risk if relevant fields updated
        if any(k in update_data for k in ["import_dependency_pct", "strategic_reserve_days"]):
            # Create temp object for calculation
            temp_data = RegionalDependencyCreate(
                region_id=region_id,
                import_dependency_pct=update_data.get(
                    "import_dependency_pct", dependency.import_dependency_pct
                ),
                strategic_reserve_days=update_data.get(
                    "strategic_reserve_days", dependency.strategic_reserve_days
                ),
                num_import_sources=dependency.num_import_sources
            )
            update_data["overall_risk_level"] = self._calculate_risk_level(temp_data)
            update_data["risk_score"] = self._calculate_risk_score(temp_data)

        for field, value in update_data.items():
            setattr(dependency, field, value)

        dependency.last_assessment_date = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(dependency)
        return dependency

    async def list_dependencies(
        self,
        risk_level: Optional[RiskLevel] = None,
        min_risk_score: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[RegionalDependency], int]:
        """List regional dependencies with filters."""
        query = select(RegionalDependency)

        if risk_level:
            query = query.where(RegionalDependency.overall_risk_level == risk_level)
        if min_risk_score is not None:
            query = query.where(RegionalDependency.risk_score >= min_risk_score)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.order_by(RegionalDependency.risk_score.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_dependency_profile(self, region_id: int) -> DependencyProfile:
        """Get comprehensive dependency profile for a region."""
        dependency = await self.get_dependency(region_id)
        if not dependency:
            raise ValueError(f"No dependency profile for region {region_id}")

        # Get region info
        region_result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        region = region_result.scalar_one_or_none()

        # Get import sources
        sources = await self.list_import_sources(dependency_id=dependency.id)

        primary_sources = [
            {
                "country": s.source_country,
                "food_type": s.food_type,
                "share_pct": s.share_of_imports_pct,
                "reliability": s.reliability_score
            }
            for s in sources if s.is_primary_source
        ]

        return DependencyProfile(
            region_id=region_id,
            region_name=region.name if region else f"Region {region_id}",
            population=region.population if region else 0,
            import_dependency_pct=dependency.import_dependency_pct or 0,
            strategic_reserve_days=dependency.strategic_reserve_days or 0,
            risk_level=dependency.overall_risk_level,
            risk_score=dependency.risk_score or 0,
            primary_import_sources=primary_sources,
            vulnerabilities=dependency.vulnerabilities or [],
            recommendations=dependency.recommendations or [],
            last_assessment_date=dependency.last_assessment_date
        )

    # ==================== Import Sources ====================

    async def create_import_source(self, data: ImportSourceCreate) -> ImportSource:
        """Create an import source record."""
        source_data = data.model_dump()

        # Calculate overall risk
        risks = [
            data.political_risk or 0,
            data.logistics_risk or 0,
            (1 - data.reliability_score) if data.reliability_score else 0
        ]
        source_data["overall_risk"] = np.mean([r for r in risks if r > 0]) if any(risks) else 0

        source = ImportSource(**source_data)
        self.db.add(source)
        await self.db.flush()
        await self.db.refresh(source)

        # Update dependency's source count
        await self._update_source_count(data.dependency_id)

        logger.info(
            f"Created import source: {data.source_country} -> "
            f"{data.food_type}"
        )
        return source

    async def _update_source_count(self, dependency_id: int) -> None:
        """Update the number of import sources in dependency."""
        count_result = await self.db.execute(
            select(func.count())
            .select_from(ImportSource)
            .where(
                and_(
                    ImportSource.dependency_id == dependency_id,
                    ImportSource.is_active == True
                )
            )
        )
        count = count_result.scalar()

        await self.db.execute(
            select(RegionalDependency)
            .where(RegionalDependency.id == dependency_id)
        )
        dependency = (await self.db.execute(
            select(RegionalDependency).where(RegionalDependency.id == dependency_id)
        )).scalar_one_or_none()

        if dependency:
            dependency.num_import_sources = count
            dependency.single_source_dependency = count == 1

    async def list_import_sources(
        self,
        dependency_id: Optional[int] = None,
        source_country: Optional[str] = None,
        food_type: Optional[str] = None,
        is_active: bool = True
    ) -> List[ImportSource]:
        """List import sources."""
        query = select(ImportSource).where(ImportSource.is_active == is_active)

        if dependency_id:
            query = query.where(ImportSource.dependency_id == dependency_id)
        if source_country:
            query = query.where(ImportSource.source_country == source_country)
        if food_type:
            query = query.where(ImportSource.food_type == food_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_import_source(
        self,
        source_id: int,
        data: ImportSourceUpdate
    ) -> Optional[ImportSource]:
        """Update import source."""
        result = await self.db.execute(
            select(ImportSource).where(ImportSource.id == source_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(source, field, value)

        await self.db.flush()
        await self.db.refresh(source)
        return source

    # ==================== Food Imports ====================

    async def record_import(self, data: FoodImportCreate) -> FoodImport:
        """Record a food import."""
        import_data = data.model_dump()

        # Calculate price per tonne
        if data.value_usd and data.quantity_tonnes:
            import_data["price_per_tonne"] = data.value_usd / data.quantity_tonnes

        food_import = FoodImport(**import_data)
        self.db.add(food_import)
        await self.db.flush()
        await self.db.refresh(food_import)

        logger.info(
            f"Recorded import: {data.quantity_tonnes}t of {data.food_type} "
            f"from {data.source_country}"
        )
        return food_import

    async def list_imports(
        self,
        region_id: Optional[int] = None,
        source_country: Optional[str] = None,
        food_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[FoodImport], int]:
        """List food imports."""
        query = select(FoodImport)

        if region_id:
            query = query.where(FoodImport.region_id == region_id)
        if source_country:
            query = query.where(FoodImport.source_country == source_country)
        if food_type:
            query = query.where(FoodImport.food_type == food_type)
        if start_date:
            query = query.where(FoodImport.import_date >= start_date)
        if end_date:
            query = query.where(FoodImport.import_date <= end_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.order_by(FoodImport.import_date.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_import_summary(
        self,
        region_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> ImportSummary:
        """Get import summary for a region and period."""
        imports, _ = await self.list_imports(
            region_id=region_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        by_country = {}
        by_food_type = {}
        total_tonnes = 0
        total_value = 0
        lead_times = []
        on_time_count = 0

        for imp in imports:
            # Aggregate by country
            by_country[imp.source_country] = (
                by_country.get(imp.source_country, 0) + imp.quantity_tonnes
            )

            # Aggregate by food type
            by_food_type[imp.food_type] = (
                by_food_type.get(imp.food_type, 0) + imp.quantity_tonnes
            )

            total_tonnes += imp.quantity_tonnes
            total_value += imp.value_usd or 0

            if imp.lead_time_days:
                lead_times.append(imp.lead_time_days)

            if imp.delay_days == 0:
                on_time_count += 1

        return ImportSummary(
            region_id=region_id,
            period_start=start_date,
            period_end=end_date,
            total_imports_tonnes=total_tonnes,
            total_value_usd=total_value,
            by_country=by_country,
            by_food_type=by_food_type,
            avg_lead_time_days=np.mean(lead_times) if lead_times else 0,
            on_time_percentage=(on_time_count / len(imports) * 100) if imports else 0
        )

    # ==================== Vulnerability Assessments ====================

    async def create_assessment(
        self,
        data: VulnerabilityAssessmentCreate
    ) -> VulnerabilityAssessment:
        """Create a vulnerability assessment."""
        assessment_data = data.model_dump()
        assessment_data["assessment_date"] = datetime.utcnow()

        assessment = VulnerabilityAssessment(**assessment_data)
        self.db.add(assessment)
        await self.db.flush()
        await self.db.refresh(assessment)

        # Update dependency with latest assessment
        dependency = await self.get_dependency(data.region_id)
        if dependency:
            dependency.last_assessment_date = datetime.utcnow()
            dependency.risk_score = data.overall_score

        logger.info(
            f"Created vulnerability assessment for region {data.region_id}: "
            f"Score {data.overall_score}"
        )
        return assessment

    async def list_assessments(
        self,
        region_id: Optional[int] = None,
        min_score: Optional[float] = None,
        limit: int = 20
    ) -> List[VulnerabilityAssessment]:
        """List vulnerability assessments."""
        query = select(VulnerabilityAssessment)

        if region_id:
            query = query.where(VulnerabilityAssessment.region_id == region_id)
        if min_score is not None:
            query = query.where(VulnerabilityAssessment.overall_score >= min_score)

        query = query.order_by(VulnerabilityAssessment.assessment_date.desc())
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Risk Analysis ====================

    async def analyze_dependency_risk(
        self,
        region_id: int
    ) -> DependencyRiskAnalysis:
        """Perform comprehensive dependency risk analysis."""
        dependency = await self.get_dependency(region_id)
        if not dependency:
            raise ValueError(f"No dependency profile for region {region_id}")

        region_result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        region = region_result.scalar_one_or_none()

        # Get import sources for analysis
        sources = await self.list_import_sources(dependency_id=dependency.id)

        # Calculate risk breakdown
        risk_breakdown = {
            "overall": dependency.risk_score / 100 if dependency.risk_score else 0,
            "climate": region.drought_risk if region else 0,
            "logistics": self._calculate_logistics_risk(sources),
            "economic": self._calculate_economic_risk(dependency),
            "political": self._calculate_political_risk(sources),
            "infrastructure": 0.3 if dependency.port_dependency else 0.1
        }

        # Identify critical dependencies
        critical_deps = [
            {
                "source": s.source_country,
                "food_type": s.food_type,
                "share_pct": s.share_of_imports_pct,
                "risk": s.overall_risk
            }
            for s in sources
            if s.share_of_imports_pct and s.share_of_imports_pct > 25
        ]

        # Generate recommendations
        recommendations = self._generate_risk_recommendations(dependency, sources)

        # Scenario analysis
        scenario = await self._analyze_disruption_scenarios(dependency, sources)

        return DependencyRiskAnalysis(
            region_id=region_id,
            region_name=region.name if region else f"Region {region_id}",
            risk_level=dependency.overall_risk_level,
            risk_score=dependency.risk_score or 0,
            risk_breakdown=risk_breakdown,
            critical_dependencies=critical_deps,
            mitigation_recommendations=recommendations,
            scenario_analysis=scenario
        )

    def _calculate_logistics_risk(self, sources: List[ImportSource]) -> float:
        """Calculate logistics risk from import sources."""
        if not sources:
            return 0

        logistics_risks = [s.logistics_risk for s in sources if s.logistics_risk]
        return np.mean(logistics_risks) if logistics_risks else 0.3

    def _calculate_economic_risk(self, dependency: RegionalDependency) -> float:
        """Calculate economic risk."""
        risk = 0.3  # Base risk

        if dependency.import_dependency_pct:
            risk += min(0.3, dependency.import_dependency_pct / 200)

        if dependency.strategic_reserve_days and dependency.strategic_reserve_days < 15:
            risk += 0.2

        return min(1.0, risk)

    def _calculate_political_risk(self, sources: List[ImportSource]) -> float:
        """Calculate political risk from import sources."""
        if not sources:
            return 0

        # Weight by import share
        weighted_risk = 0
        total_share = 0

        for s in sources:
            if s.political_risk and s.share_of_imports_pct:
                weighted_risk += s.political_risk * s.share_of_imports_pct
                total_share += s.share_of_imports_pct

        return weighted_risk / total_share if total_share > 0 else 0

    def _generate_risk_recommendations(
        self,
        dependency: RegionalDependency,
        sources: List[ImportSource]
    ) -> List[str]:
        """Generate risk mitigation recommendations."""
        recommendations = []

        if dependency.strategic_reserve_days and dependency.strategic_reserve_days < 30:
            recommendations.append(
                f"Increase strategic reserves from {dependency.strategic_reserve_days} "
                f"to at least 45 days"
            )

        if dependency.single_source_dependency:
            recommendations.append(
                "Diversify import sources to reduce single-source dependency"
            )

        if dependency.port_dependency:
            recommendations.append(
                "Develop alternative port infrastructure to reduce port dependency"
            )

        if dependency.import_dependency_pct and dependency.import_dependency_pct > 50:
            recommendations.append(
                "Invest in local production capacity to reduce import dependency"
            )

        # Check for high-risk sources
        high_risk_sources = [s for s in sources if s.overall_risk and s.overall_risk > 0.6]
        for source in high_risk_sources:
            recommendations.append(
                f"Review and mitigate risks with {source.source_country} imports"
            )

        return recommendations

    async def _analyze_disruption_scenarios(
        self,
        dependency: RegionalDependency,
        sources: List[ImportSource]
    ) -> Dict[str, Any]:
        """Analyze potential disruption scenarios."""
        scenarios = []

        # Primary source disruption
        primary_sources = [s for s in sources if s.is_primary_source]
        if primary_sources:
            primary = primary_sources[0]
            scenarios.append({
                "name": "Primary Source Disruption",
                "description": f"Complete loss of imports from {primary.source_country}",
                "probability": primary.overall_risk or 0.1,
                "impact_pct": primary.share_of_imports_pct or 0,
                "mitigation": "Activate alternative sources, draw on reserves"
            })

        # Port disruption (if applicable)
        if dependency.port_dependency:
            scenarios.append({
                "name": "Port Disruption",
                "description": f"Closure of {dependency.primary_port_name}",
                "probability": 0.1,
                "impact_pct": dependency.import_dependency_pct or 0,
                "mitigation": "Pre-position supplies, use alternative ports"
            })

        # Regional conflict
        if any(s.political_risk and s.political_risk > 0.5 for s in sources):
            scenarios.append({
                "name": "Regional Instability",
                "description": "Political disruption affecting multiple sources",
                "probability": 0.15,
                "impact_pct": 40,
                "mitigation": "Diversify to stable regions, increase reserves"
            })

        return {
            "scenarios": scenarios,
            "most_likely": scenarios[0]["name"] if scenarios else None,
            "highest_impact": max(
                scenarios,
                key=lambda x: x["impact_pct"],
                default={}
            ).get("name")
        }

    async def simulate_import_disruption(
        self,
        region_id: int,
        source_country: str,
        disruption_pct: float = 100
    ) -> ImportDisruptionScenario:
        """Simulate the impact of an import disruption."""
        dependency = await self.get_dependency(region_id)
        if not dependency:
            raise ValueError(f"No dependency profile for region {region_id}")

        sources = await self.list_import_sources(
            dependency_id=dependency.id,
            source_country=source_country
        )

        if not sources:
            raise ValueError(f"No imports from {source_country}")

        affected_source = sources[0]
        impact_tonnes = (
            (affected_source.annual_volume_tonnes or 0) *
            (disruption_pct / 100)
        )

        # Calculate impact on days of supply
        if dependency.strategic_reserve_days:
            impact_days = impact_tonnes / (
                impact_tonnes / 365
            ) if impact_tonnes > 0 else 0
        else:
            impact_days = 0

        # Find alternative sources
        alternatives = await self.list_import_sources(
            food_type=affected_source.food_type
        )
        alternative_sources = [
            s for s in alternatives
            if s.source_country != source_country
        ]

        mitigation_options = []
        for alt in alternative_sources[:3]:
            mitigation_options.append({
                "source": alt.source_country,
                "capacity": alt.annual_volume_tonnes,
                "lead_time_days": alt.avg_lead_time_days,
                "reliability": alt.reliability_score
            })

        return ImportDisruptionScenario(
            scenario_name=f"{source_country} Import Disruption",
            description=f"{disruption_pct}% reduction in imports from {source_country}",
            affected_sources=[source_country],
            impact_tonnes=impact_tonnes,
            impact_days_supply=impact_days,
            mitigation_options=mitigation_options,
            estimated_recovery_days=int(
                (affected_source.avg_lead_time_days or 30) * 1.5
            )
        )

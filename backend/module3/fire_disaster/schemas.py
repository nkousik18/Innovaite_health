"""
Pydantic schemas for the fire disaster simulation pipeline.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from schemas.common import BaseSchema


# ── Request ──────────────────────────────────────────────────────────────

class FireDisasterRequest(BaseModel):
    """Input for a fire disaster simulation."""
    latitude: float = Field(..., ge=-90, le=90, description="Fire origin latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Fire origin longitude")
    radius_km: float = Field(
        default=50, ge=5, le=500,
        description="Radius (km) within which regions are considered affected"
    )
    fire_intensity: float = Field(
        default=0.7, ge=0.1, le=1.0,
        description="Fire intensity factor (0.1=minor, 1.0=catastrophic)"
    )
    displacement_pct: float = Field(
        default=0.4, ge=0.0, le=1.0,
        description="Fraction of population in affected zones that gets displaced"
    )


# ── Step results ─────────────────────────────────────────────────────────

class WeatherCheckResult(BaseSchema):
    """Step 1 — live weather at the fire location."""
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction: Optional[str] = None
    rainfall_mm: Optional[float] = None
    description: str = ""
    fire_weather_risk: str = "unknown"


class AffectedZone(BaseSchema):
    """A single region flagged as affected."""
    region_id: int
    region_name: str
    distance_km: float
    severity: str  # critical / high / moderate
    population: Optional[int] = None
    wind_exposed: bool = False


class FlagZonesResult(BaseSchema):
    """Step 2 — affected zones around the fire."""
    total_regions_scanned: int
    affected_zones: List[AffectedZone]


class DisruptionRecord(BaseSchema):
    """One disruption created on a route."""
    disruption_id: int
    route_id: int
    route_name: str
    severity: str
    status: str


class CreateDisruptionsResult(BaseSchema):
    """Step 3 — route disruptions created."""
    routes_scanned: int
    disruptions_created: int
    disruptions: List[DisruptionRecord]


class DisplacementEntry(BaseSchema):
    """Population displaced from one zone to another."""
    from_region_id: int
    from_region_name: str
    to_region_id: int
    to_region_name: str
    displaced_count: int


class DisplacePopulationResult(BaseSchema):
    """Step 4 — displacement modelling."""
    total_displaced: int
    entries: List[DisplacementEntry]


class SupplyRecalcEntry(BaseSchema):
    """Updated supply status for one region."""
    region_id: int
    region_name: str
    original_population: Optional[int] = None
    effective_population: int
    demand_multiplier: float
    estimated_days_of_supply: Optional[float] = None


class RecalculateSupplyResult(BaseSchema):
    """Step 5 — supply recalculation."""
    regions_updated: int
    entries: List[SupplyRecalcEntry]


class AlertRecord(BaseSchema):
    """An alert generated."""
    alert_id: int
    alert_code: str
    region_id: int
    region_name: str
    level: str
    title: str


class GenerateAlertsResult(BaseSchema):
    """Step 6 — shortage alerts."""
    alerts_generated: int
    alerts: List[AlertRecord]


class RerouteEntry(BaseSchema):
    """An alternative route created."""
    route_id: int
    origin: str
    destination: str
    distance_km: float
    duration_hours: float


class RerouteResult(BaseSchema):
    """Step 7 — rerouting around blocked areas."""
    blocked_routes: int
    alternative_routes_created: int
    alternatives: List[RerouteEntry]


class DistributionPlanSummary(BaseSchema):
    """Step 8 — distribution plan summary."""
    plan_id: Optional[int] = None
    plan_code: Optional[str] = None
    region_id: int
    region_name: str
    population_covered: int
    food_allocated_tonnes: float
    distribution_points: int
    priority_groups: List[str]


class OptimizeDistributionResult(BaseSchema):
    """Step 8 — distribution optimisation."""
    plans_created: int
    plans: List[DistributionPlanSummary]


# ── Full pipeline response ───────────────────────────────────────────────

class FireDisasterResponse(BaseSchema):
    """Complete pipeline output."""
    scenario_id: str
    fire_location: Dict[str, float]
    started_at: datetime
    completed_at: datetime
    duration_seconds: float

    step_1_weather: WeatherCheckResult
    step_2_zones: FlagZonesResult
    step_3_disruptions: CreateDisruptionsResult
    step_4_displacement: DisplacePopulationResult
    step_5_supply: RecalculateSupplyResult
    step_6_alerts: GenerateAlertsResult
    step_7_reroute: RerouteResult
    step_8_distribution: OptimizeDistributionResult

    summary: Dict[str, Any]

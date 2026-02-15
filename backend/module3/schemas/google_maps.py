"""
Schemas for Google Maps auto-route generation and smart optimization.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

from .common import BaseSchema


class OptimizeFor(str, Enum):
    TIME = "time"
    COST = "cost"
    BALANCED = "balanced"


class AutoRouteGenerateRequest(BaseModel):
    """Request to auto-generate routes between distribution centers."""
    center_ids: Optional[List[int]] = Field(
        None,
        description="Specific distribution center IDs to generate routes between"
    )
    region_ids: Optional[List[int]] = Field(
        None,
        description="Generate routes between all centers in these regions"
    )
    include_reverse: bool = Field(
        default=True,
        description="Also create reverse direction routes"
    )
    max_routes: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of routes to generate (cost control)"
    )


class AutoRouteResult(BaseSchema):
    """Result for a single auto-generated route."""
    origin_center_id: int
    origin_center_name: str
    destination_center_id: int
    destination_center_name: str
    distance_km: float
    duration_hours: float
    polyline: str = ""
    saved: bool = False
    route_id: Optional[int] = None
    skipped_reason: Optional[str] = None


class AutoRouteGenerateResponse(BaseSchema):
    """Response from auto-route generation."""
    total_pairs_considered: int
    routes_created: int
    routes_skipped: int
    results: List[AutoRouteResult]


class SmartRouteOptimizationRequest(BaseModel):
    """Enhanced route optimization request with Google Maps support."""
    origin_region_id: int
    destination_region_id: int
    cargo_tonnes: float
    requires_cold_chain: bool = False
    max_alternatives: int = Field(default=3, ge=1, le=10)
    avoid_disruptions: bool = True
    use_google_maps: bool = Field(
        default=False,
        description="Use Google Maps API for real distance/duration data"
    )
    optimize_for: OptimizeFor = Field(
        default=OptimizeFor.BALANCED,
        description="Optimization priority"
    )

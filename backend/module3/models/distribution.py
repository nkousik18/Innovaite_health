"""
Distribution network and transportation models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Text, Boolean,
    ForeignKey, Enum as SQLEnum, JSON, Index
)
from sqlalchemy.orm import relationship
import enum

from .base import Base


class CorridorType(enum.Enum):
    """Transportation corridor types."""
    HIGHWAY = "highway"
    RAIL = "rail"
    WATERWAY = "waterway"
    AIR = "air"
    PIPELINE = "pipeline"


class DisruptionType(enum.Enum):
    """Types of route disruptions."""
    LOCKDOWN = "lockdown"
    INFRASTRUCTURE = "infrastructure"
    WEATHER = "weather"
    CONFLICT = "conflict"
    FUEL_SHORTAGE = "fuel_shortage"
    BORDER_CLOSURE = "border_closure"
    CIVIL_UNREST = "civil_unrest"
    ACCIDENT = "accident"
    MAINTENANCE = "maintenance"


class DisruptionSeverity(enum.Enum):
    """Severity levels for disruptions."""
    LOW = "low"          # Minor delays
    MEDIUM = "medium"    # Significant delays
    HIGH = "high"        # Route partially blocked
    CRITICAL = "critical"  # Route completely blocked


class TransportationCorridor(Base):
    """Major transportation corridors for food distribution."""

    __tablename__ = "transportation_corridors"

    name = Column(String(255), nullable=False)
    corridor_code = Column(String(50), unique=True, nullable=False)
    corridor_type = Column(SQLEnum(CorridorType), nullable=False)

    # Geographic data
    start_region_id = Column(Integer, ForeignKey("regions.id"))
    end_region_id = Column(Integer, ForeignKey("regions.id"))
    path_geometry = Column(JSON)  # GeoJSON LineString
    length_km = Column(Float)

    # Capacity
    daily_capacity_tonnes = Column(Float)
    current_utilization = Column(Float)  # percentage
    max_vehicle_weight_tonnes = Column(Float)

    # Infrastructure
    num_lanes = Column(Integer)  # for roads
    is_paved = Column(Boolean, default=True)
    has_toll = Column(Boolean, default=False)
    border_crossings = Column(JSON)  # List of border crossing points

    # Cold chain
    cold_chain_capable = Column(Boolean, default=False)
    cold_storage_points = Column(JSON)  # List of cold storage locations

    # Status
    operational_status = Column(String(50), default="operational")
    last_inspection_date = Column(DateTime)

    is_active = Column(Boolean, default=True)

    # Relationships
    start_region = relationship("Region", foreign_keys=[start_region_id])
    end_region = relationship("Region", foreign_keys=[end_region_id])
    routes = relationship("TransportRoute", back_populates="corridor")
    disruptions = relationship("RouteDisruption", back_populates="corridor")


class DistributionCenter(Base):
    """Food distribution centers and warehouses."""

    __tablename__ = "distribution_centers"

    name = Column(String(255), nullable=False)
    center_code = Column(String(50), unique=True, nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)

    # Location
    address = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Capacity
    total_capacity_tonnes = Column(Float)
    current_inventory_tonnes = Column(Float)
    utilization_percentage = Column(Float)

    # Cold storage
    cold_storage_capacity_tonnes = Column(Float)
    cold_storage_current_tonnes = Column(Float)
    temperature_zones = Column(JSON)  # Different temp zones

    # Operations
    operating_hours = Column(JSON)  # Daily operating schedule
    staff_count = Column(Integer)
    vehicles_available = Column(Integer)
    daily_throughput_tonnes = Column(Float)

    # Contact
    contact_name = Column(String(100))
    contact_phone = Column(String(50))
    contact_email = Column(String(100))

    # Status
    operational_status = Column(String(50), default="operational")
    last_inspection_date = Column(DateTime)

    is_active = Column(Boolean, default=True)

    # Relationships
    region = relationship("Region", back_populates="distribution_centers")
    stocks = relationship("WarehouseStock", back_populates="distribution_center")
    distribution_points = relationship("DistributionPoint", back_populates="center")

    __table_args__ = (
        Index("idx_dc_region", "region_id"),
        Index("idx_dc_location", "latitude", "longitude"),
    )


class TransportRoute(Base):
    """Specific transport routes between locations."""

    __tablename__ = "transport_routes"

    name = Column(String(255), nullable=False)
    route_code = Column(String(50), unique=True, nullable=False)
    corridor_id = Column(Integer, ForeignKey("transportation_corridors.id"))

    # Origin and destination
    origin_center_id = Column(Integer, ForeignKey("distribution_centers.id"))
    destination_center_id = Column(Integer, ForeignKey("distribution_centers.id"))
    origin_region_id = Column(Integer, ForeignKey("regions.id"))
    destination_region_id = Column(Integer, ForeignKey("regions.id"))

    # Route details
    distance_km = Column(Float)
    estimated_time_hours = Column(Float)
    path_geometry = Column(JSON)  # GeoJSON

    # Capacity
    daily_capacity_tonnes = Column(Float)
    vehicle_type = Column(String(50))  # truck, train, ship, etc.

    # Cost
    cost_per_km = Column(Float)
    toll_costs = Column(Float)
    total_cost = Column(Float)

    # Cold chain
    cold_chain_capable = Column(Boolean, default=False)
    max_cold_duration_hours = Column(Float)

    # Priority
    priority_score = Column(Float)  # Higher = more important
    is_primary_route = Column(Boolean, default=False)

    # Status
    operational_status = Column(String(50), default="operational")
    current_traffic_level = Column(String(20))  # low, medium, high

    is_active = Column(Boolean, default=True)

    # Relationships
    corridor = relationship("TransportationCorridor", back_populates="routes")
    origin_center = relationship("DistributionCenter", foreign_keys=[origin_center_id])
    destination_center = relationship("DistributionCenter", foreign_keys=[destination_center_id])
    origin_region = relationship("Region", foreign_keys=[origin_region_id])
    destination_region = relationship("Region", foreign_keys=[destination_region_id])

    __table_args__ = (
        Index("idx_route_origin_dest", "origin_region_id", "destination_region_id"),
    )


class RouteDisruption(Base):
    """Active and historical route disruptions."""

    __tablename__ = "route_disruptions"

    corridor_id = Column(Integer, ForeignKey("transportation_corridors.id"))
    route_id = Column(Integer, ForeignKey("transport_routes.id"))
    region_id = Column(Integer, ForeignKey("regions.id"))

    # Disruption details
    disruption_type = Column(SQLEnum(DisruptionType), nullable=False)
    severity = Column(SQLEnum(DisruptionSeverity), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expected_end_at = Column(DateTime)
    actual_end_at = Column(DateTime)
    duration_hours = Column(Float)

    # Impact
    affected_area_geometry = Column(JSON)  # GeoJSON
    capacity_reduction_percentage = Column(Float)
    delay_hours = Column(Float)
    affected_routes_count = Column(Integer)
    affected_shipments_count = Column(Integer)

    # Alternative routing
    alternative_routes = Column(JSON)  # List of alternative route IDs
    reroute_recommended = Column(Boolean, default=False)

    # Source
    reported_by = Column(String(100))
    verified = Column(Boolean, default=False)
    verification_source = Column(String(100))

    is_active = Column(Boolean, default=True)

    # Relationships
    corridor = relationship("TransportationCorridor", back_populates="disruptions")
    route = relationship("TransportRoute")
    region = relationship("Region")

    __table_args__ = (
        Index("idx_disruption_active", "is_active", "started_at"),
        Index("idx_disruption_type_severity", "disruption_type", "severity"),
    )


class ColdChainFacility(Base):
    """Cold chain storage and processing facilities."""

    __tablename__ = "cold_chain_facilities"

    name = Column(String(255), nullable=False)
    facility_code = Column(String(50), unique=True, nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    distribution_center_id = Column(Integer, ForeignKey("distribution_centers.id"))

    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text)

    # Capacity
    total_capacity_tonnes = Column(Float)
    current_inventory_tonnes = Column(Float)
    utilization_percentage = Column(Float)

    # Temperature zones
    freezer_capacity_tonnes = Column(Float)  # Below -18C
    chiller_capacity_tonnes = Column(Float)  # 0-4C
    cool_room_capacity_tonnes = Column(Float)  # 10-15C
    temperature_zones = Column(JSON)

    # Power
    power_source = Column(String(50))  # grid, generator, solar
    backup_power_hours = Column(Float)
    power_consumption_kwh = Column(Float)

    # Equipment
    refrigeration_units = Column(Integer)
    last_maintenance_date = Column(DateTime)
    equipment_status = Column(JSON)

    # Operations
    operating_hours = Column(JSON)
    staff_count = Column(Integer)

    # Status
    operational_status = Column(String(50), default="operational")
    temperature_alert = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)

    # Relationships
    region = relationship("Region")
    distribution_center = relationship("DistributionCenter")

    __table_args__ = (
        Index("idx_cold_chain_region", "region_id"),
    )

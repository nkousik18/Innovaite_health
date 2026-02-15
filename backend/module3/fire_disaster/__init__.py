"""
Fire Disaster Simulation Pipeline

Automated end-to-end response pipeline:
  weather check -> flag zones -> create disruptions -> displace population
  -> recalculate supply -> generate alerts -> reroute -> optimize distribution
"""

from .router import router as fire_disaster_router

__all__ = ["fire_disaster_router"]

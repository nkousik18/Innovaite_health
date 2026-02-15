"""
Google Maps API Service

Provides route directions and distance matrix calculations
using the Google Maps Directions and Distance Matrix APIs.
"""

import logging
from typing import List, Optional, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleMapsService:
    """Stateless client for Google Maps API calls."""

    def __init__(self):
        self.api_key = settings.google_maps_api_key
        self.base_url = settings.google_maps_base_url
        self.timeout = settings.external_api_timeout_seconds

    async def get_directions(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        waypoints: Optional[List[Dict[str, float]]] = None,
        avoid: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get driving directions between two points.

        Returns dict with:
          - distance_km: total distance in km
          - duration_hours: total duration in hours
          - polyline: encoded polyline string
          - steps: list of step instructions
        """
        params: Dict[str, str] = {
            "origin": f"{origin_lat},{origin_lon}",
            "destination": f"{dest_lat},{dest_lon}",
            "mode": "driving",
        }

        if waypoints:
            wp_str = "|".join(f"{w['lat']},{w['lon']}" for w in waypoints)
            params["waypoints"] = wp_str

        if avoid:
            params["avoid"] = "|".join(avoid)

        data = await self._make_request("directions/json", params)

        if not data.get("routes"):
            raise ValueError("No routes found between the specified locations")

        route = data["routes"][0]
        leg = route["legs"][0]

        steps = []
        for step in leg.get("steps", []):
            steps.append({
                "instruction": step.get("html_instructions", ""),
                "distance_m": step["distance"]["value"],
                "duration_s": step["duration"]["value"],
            })

        # Sum all legs if waypoints create multiple legs
        total_distance_m = sum(l["distance"]["value"] for l in route["legs"])
        total_duration_s = sum(l["duration"]["value"] for l in route["legs"])

        return {
            "distance_km": round(total_distance_m / 1000, 2),
            "duration_hours": round(total_duration_s / 3600, 2),
            "polyline": route.get("overview_polyline", {}).get("points", ""),
            "steps": steps,
        }

    async def get_distance_matrix(
        self,
        origins: List[Dict[str, float]],
        destinations: List[Dict[str, float]],
    ) -> Dict[str, Any]:
        """
        Get pairwise distance and duration between origins and destinations.

        Each origin/destination is a dict with 'lat' and 'lon' keys.

        Returns dict with:
          - rows: list of origin rows, each containing list of destination elements
            with distance_km and duration_hours
        """
        origins_str = "|".join(f"{o['lat']},{o['lon']}" for o in origins)
        destinations_str = "|".join(f"{d['lat']},{d['lon']}" for d in destinations)

        params = {
            "origins": origins_str,
            "destinations": destinations_str,
            "mode": "driving",
        }

        data = await self._make_request("distancematrix/json", params)

        rows = []
        for row in data.get("rows", []):
            elements = []
            for element in row.get("elements", []):
                if element.get("status") == "OK":
                    elements.append({
                        "distance_km": round(element["distance"]["value"] / 1000, 2),
                        "duration_hours": round(element["duration"]["value"] / 3600, 2),
                        "status": "OK",
                    })
                else:
                    elements.append({
                        "distance_km": None,
                        "duration_hours": None,
                        "status": element.get("status", "UNKNOWN"),
                    })
            rows.append({"elements": elements})

        return {"rows": rows}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def _make_request(self, endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
        """Make an authenticated GET request to the Google Maps API."""
        if not self.api_key:
            raise ValueError("Google Maps API key is not configured")

        params["key"] = self.api_key
        url = f"{self.base_url}/{endpoint}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        status = data.get("status", "")
        if status not in ("OK", "ZERO_RESULTS"):
            error_msg = data.get("error_message", status)
            logger.error(f"Google Maps API error: {error_msg}")
            raise ValueError(f"Google Maps API error: {error_msg}")

        return data

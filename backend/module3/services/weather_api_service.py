"""
OpenWeatherMap API Service

Provides current weather and 5-day forecast data
using the OpenWeatherMap API.
"""

import logging
from typing import List, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Thresholds for extreme weather flags
DROUGHT_HUMIDITY_THRESHOLD = 20  # %
HEATWAVE_TEMP_THRESHOLD = 40  # Celsius
FROST_TEMP_THRESHOLD = 0  # Celsius
FLOOD_RAINFALL_THRESHOLD = 50  # mm in 3 hours


class WeatherAPIService:
    """Stateless client for OpenWeatherMap API calls."""

    def __init__(self):
        self.api_key = settings.weather_api_key
        self.base_url = settings.weather_api_url
        self.timeout = settings.external_api_timeout_seconds

    async def get_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get current weather for a location.

        Returns dict with:
          - temperature_c, temperature_min_c, temperature_max_c, feels_like_c
          - humidity_percentage, rainfall_mm, wind_speed_kmh, wind_direction
          - cloud_cover_percentage, pressure_hpa
          - is_drought, is_flood, is_frost, is_heatwave
          - description, icon
        """
        params = {
            "lat": str(lat),
            "lon": str(lon),
            "units": "metric",
        }

        data = await self._make_request("weather", params)

        main = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        rain = data.get("rain", {})
        weather_info = data.get("weather", [{}])[0]

        temp = main.get("temp")
        humidity = main.get("humidity")
        rainfall_mm = rain.get("1h", 0) or rain.get("3h", 0)

        return {
            "temperature_c": temp,
            "temperature_min_c": main.get("temp_min"),
            "temperature_max_c": main.get("temp_max"),
            "feels_like_c": main.get("feels_like"),
            "humidity_percentage": humidity,
            "rainfall_mm": rainfall_mm,
            "wind_speed_kmh": round((wind.get("speed", 0) or 0) * 3.6, 1),
            "wind_direction": self._degrees_to_direction(wind.get("deg", 0)),
            "cloud_cover_percentage": clouds.get("all"),
            "pressure_hpa": main.get("pressure"),
            "is_drought": (humidity is not None and humidity < DROUGHT_HUMIDITY_THRESHOLD),
            "is_flood": (rainfall_mm >= FLOOD_RAINFALL_THRESHOLD),
            "is_frost": (temp is not None and temp <= FROST_TEMP_THRESHOLD),
            "is_heatwave": (temp is not None and temp >= HEATWAVE_TEMP_THRESHOLD),
            "description": weather_info.get("description", ""),
            "icon": weather_info.get("icon", ""),
        }

    async def get_forecast(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """
        Get 5-day / 3-hour forecast for a location.

        Returns list of forecast entries, each with:
          - datetime_utc, temperature_c, temperature_min_c, temperature_max_c
          - humidity_percentage, rainfall_mm, wind_speed_kmh
          - description, icon
        """
        params = {
            "lat": str(lat),
            "lon": str(lon),
            "units": "metric",
        }

        data = await self._make_request("forecast", params)

        entries = []
        for item in data.get("list", []):
            main = item.get("main", {})
            wind = item.get("wind", {})
            rain = item.get("rain", {})
            weather_info = item.get("weather", [{}])[0]

            entries.append({
                "datetime_utc": item.get("dt_txt", ""),
                "temperature_c": main.get("temp"),
                "temperature_min_c": main.get("temp_min"),
                "temperature_max_c": main.get("temp_max"),
                "humidity_percentage": main.get("humidity"),
                "rainfall_mm": rain.get("3h", 0),
                "wind_speed_kmh": round((wind.get("speed", 0) or 0) * 3.6, 1),
                "description": weather_info.get("description", ""),
                "icon": weather_info.get("icon", ""),
            })

        return entries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def _make_request(self, endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
        """Make an authenticated GET request to the OpenWeatherMap API."""
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is not configured")

        params["appid"] = self.api_key
        url = f"{self.base_url}/{endpoint}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("cod") and str(data["cod"]) not in ("200",):
            error_msg = data.get("message", "Unknown error")
            logger.error(f"OpenWeatherMap API error: {error_msg}")
            raise ValueError(f"OpenWeatherMap API error: {error_msg}")

        return data

    @staticmethod
    def _degrees_to_direction(degrees: float) -> str:
        """Convert wind degrees to compass direction."""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = round(degrees / 45) % 8
        return directions[index]

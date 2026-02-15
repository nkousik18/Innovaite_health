# SENTINEL-HEALTH Module 3 — Frontend API Documentation

> **For:** Django Frontend Team
> **Backend:** FastAPI + PostgreSQL (async)
> **Base URL:** `http://localhost:8023/api/v1`
> **Swagger UI:** `http://localhost:8023/docs`
> **Last Updated:** 2026-02-15

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Global Endpoints](#2-global-endpoints)
3. [Enum Reference](#3-enum-reference)
4. [Agricultural Production](#4-agricultural-production)
5. [Distribution Network](#5-distribution-network)
6. [Food Inventory](#6-food-inventory)
7. [Food Dependency](#7-food-dependency)
8. [Shortage Alerts](#8-shortage-alerts)
9. [Distribution Plans](#9-distribution-plans)
10. [Agricultural Resilience](#10-agricultural-resilience)
11. [Fire Disaster Simulation](#11-fire-disaster-simulation)
12. [Pagination](#12-pagination)
13. [Error Handling](#13-error-handling)
14. [Django Integration Guide](#14-django-integration-guide)

---

## 1. Quick Start

### Making Requests from Django

All API calls use JSON. Set `Content-Type: application/json` for POST/PATCH requests.

```python
# settings.py
SENTINEL_API_BASE = "http://localhost:8023/api/v1"

# utils/api_client.py
import requests

class SentinelAPI:
    BASE = settings.SENTINEL_API_BASE

    @staticmethod
    def get(path, params=None):
        r = requests.get(f"{SentinelAPI.BASE}{path}", params=params)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def post(path, data=None):
        r = requests.post(f"{SentinelAPI.BASE}{path}", json=data)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def patch(path, data=None):
        r = requests.patch(f"{SentinelAPI.BASE}{path}", json=data)
        r.raise_for_status()
        return r.json()
```

### Quick Example — Fetch Regions

```python
regions = SentinelAPI.get("/agricultural/regions", params={"page": 1, "page_size": 50})
# Returns: { "items": [...], "total": 3, "page": 1, "page_size": 50, "total_pages": 1 }
```

---

## 2. Global Endpoints

These are NOT under `/api/v1`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — returns `{status, service, version, environment, timestamp}` |
| `GET` | `/` | Root info — returns service metadata |
| `GET` | `/integration/module1` | Module 1 integration status |
| `GET` | `/integration/module2` | Module 2 integration status |

---

## 3. Enum Reference

All enums are passed as **lowercase strings** in JSON.

### CropType
`"staple_grain"` | `"protein"` | `"vegetable"` | `"fruit"` | `"legume"` | `"tuber"` | `"oil_seed"` | `"other"`

### SeasonType
`"spring"` | `"summer"` | `"fall"` | `"winter"` | `"wet"` | `"dry"` | `"year_round"`

### CorridorType
`"highway"` | `"rail"` | `"waterway"` | `"air"` | `"pipeline"`

### DisruptionType
`"lockdown"` | `"infrastructure"` | `"weather"` | `"conflict"` | `"fuel_shortage"` | `"border_closure"` | `"civil_unrest"` | `"accident"` | `"maintenance"`

### DisruptionSeverity
`"low"` | `"medium"` | `"high"` | `"critical"`

### FoodCategoryType
`"staple_grains"` | `"protein"` | `"vegetables"` | `"fruits"` | `"dairy"` | `"oils_fats"` | `"shelf_stable"` | `"beverages"` | `"infant_food"` | `"medical_nutrition"`

### StorageType
`"ambient"` | `"refrigerated"` | `"frozen"` | `"controlled"`

### StockStatus (read-only, computed by backend)
`"critical"` | `"low"` | `"adequate"` | `"surplus"`

### RiskLevel
`"low"` | `"medium"` | `"high"` | `"critical"`

### AlertLevel
`"normal"` | `"warning"` | `"imminent"` | `"critical"`

### AlertType
`"shortage"` | `"production"` | `"distribution"` | `"price"` | `"quality"` | `"import"` | `"weather"`

### AlertStatus
`"active"` | `"acknowledged"` | `"responding"` | `"resolved"` | `"escalated"` | `"false_alarm"`

### PlanStatus
`"draft"` | `"pending_approval"` | `"approved"` | `"active"` | `"completed"` | `"cancelled"`

### PopulationType
`"elderly"` | `"children"` | `"pregnant"` | `"immunocompromised"` | `"healthcare_worker"` | `"essential_worker"` | `"disabled"` | `"low_income"` | `"general"`

### SiteType
`"rooftop_garden"` | `"vertical_farm"` | `"community_garden"` | `"hydroponics"` | `"aquaponics"` | `"greenhouse"` | `"vacant_lot"` | `"peri_urban"`

### ProjectStatus
`"proposed"` | `"planning"` | `"approved"` | `"under_construction"` | `"operational"` | `"suspended"` | `"closed"`

### OptimizeFor
`"time"` | `"cost"` | `"balanced"`

---

## 4. Agricultural Production

**Prefix:** `/agricultural`

### 4.1 Regions

#### Create Region
```
POST /agricultural/regions
```
```json
{
  "name": "Delhi NCR",
  "country": "India",
  "region_code": "IN-DL",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "area_sq_km": 1484,
  "population": 20000000,
  "climate_zone": "semi-arid",
  "population_density": 13478.0,
  "urban_percentage": 97.5,
  "arable_land_sq_km": 200,
  "irrigation_coverage": 0.85,
  "agricultural_workforce": 50000,
  "drought_risk": 0.6,
  "flood_risk": 0.3
}
```
**Required:** `name`, `country`, `region_code`, `latitude` (-90 to 90), `longitude` (-180 to 180)

**Response:** `RegionResponse` (includes auto-generated `id`, `is_active`, `created_at`, `updated_at`)

#### List Regions
```
GET /agricultural/regions?country=India&is_active=true&page=1&page_size=20
```
**Response:** Paginated (see [Pagination](#12-pagination))

#### Get Region
```
GET /agricultural/regions/{region_id}
```

#### Update Region
```
PATCH /agricultural/regions/{region_id}
```
```json
{
  "population": 21000000,
  "drought_risk": 0.7
}
```
Only include fields you want to change.

---

### 4.2 Crops

#### Create Crop
```
POST /agricultural/crops
```
```json
{
  "name": "Rice",
  "scientific_name": "Oryza sativa",
  "crop_type": "staple_grain",
  "calories_per_100g": 130,
  "protein_g": 2.7,
  "carbs_g": 28,
  "fat_g": 0.3,
  "fiber_g": 0.4,
  "shelf_life_days": 365,
  "requires_cold_chain": false,
  "growing_season": "wet",
  "days_to_harvest": 120,
  "avg_yield_kg_per_hectare": 4500
}
```
**Required:** `name`, `crop_type` (see [CropType enum](#croptype))

#### List Crops
```
GET /agricultural/crops?crop_type=staple_grain&is_active=true
```

#### Get Crop
```
GET /agricultural/crops/{crop_id}
```

---

### 4.3 Production Records

#### Record Production
```
POST /agricultural/production
```
```json
{
  "region_id": 1,
  "crop_id": 1,
  "year": 2025,
  "season": "wet",
  "planted_area_hectares": 50000,
  "harvested_area_hectares": 48000,
  "production_tonnes": 216000,
  "yield_kg_per_hectare": 4500,
  "loss_percentage": 4.0,
  "drought_affected": false,
  "flood_affected": false
}
```
**Required:** `region_id`, `crop_id`, `year` (2000-2100)

#### Get Production by Region
```
GET /agricultural/production/{region_id}?crop_id=1&year=2025&season=wet
```

#### Production Summary
```
GET /agricultural/production/{region_id}/summary?year=2025
```
**Note:** `year` is required (2000-2100).

---

### 4.4 Harvest Forecasts

#### Create Forecast
```
POST /agricultural/forecasts
```
```json
{
  "region_id": 1,
  "crop_id": 1,
  "target_date": "2025-09-01T00:00:00",
  "predicted_yield_tonnes": 200000,
  "predicted_yield_lower": 180000,
  "predicted_yield_upper": 220000,
  "confidence_score": 0.85,
  "weather_risk": 0.3,
  "labor_risk": 0.1
}
```
**Required:** `region_id`, `crop_id`, `target_date`, `predicted_yield_tonnes`

#### List Forecasts
```
GET /agricultural/forecasts?region_id=1&crop_id=1&target_date_from=2025-01-01T00:00:00&target_date_to=2025-12-31T23:59:59
```

#### Auto-Generate Forecast
```
POST /agricultural/forecasts/generate/{region_id}/{crop_id}?horizon_days=90
```
**Note:** `horizon_days` range is 30-365, default 90.

---

### 4.5 Weather Data

#### Record Weather Manually
```
POST /agricultural/weather
```
```json
{
  "region_id": 1,
  "recorded_at": "2025-08-15T12:00:00",
  "temperature_c": 38.5,
  "temperature_min_c": 30.0,
  "temperature_max_c": 42.0,
  "rainfall_mm": 0.0,
  "humidity_percentage": 25.0,
  "wind_speed_kmh": 15.0,
  "is_drought": true,
  "is_heatwave": true
}
```
**Required:** `region_id`, `recorded_at`

#### Get Weather History
```
GET /agricultural/weather/{region_id}?days_back=30
```
`days_back`: 1-365, default 30

#### Weather Summary
```
GET /agricultural/weather/{region_id}/summary?start_date=2025-01-01T00:00:00&end_date=2025-06-30T23:59:59
```
Both `start_date` and `end_date` are **required**.

#### Fetch Live Weather (OpenWeatherMap API)
```
POST /agricultural/weather/{region_id}/fetch?save_to_db=true
```
Fetches real-time weather from OpenWeatherMap for the region's lat/lon. If `save_to_db=true` (default), persists the record.

**Response:**
```json
{
  "region_id": 1,
  "region_name": "Delhi NCR",
  "temperature_c": 35.2,
  "temperature_min_c": 33.0,
  "temperature_max_c": 37.5,
  "feels_like_c": 38.1,
  "humidity_percentage": 45.0,
  "rainfall_mm": 0.0,
  "wind_speed_kmh": 12.5,
  "wind_direction": "SW",
  "cloud_cover_percentage": 20,
  "pressure_hpa": 1010,
  "description": "few clouds",
  "is_drought": false,
  "is_flood": false,
  "is_frost": false,
  "is_heatwave": false,
  "saved_to_db": true,
  "weather_record_id": 42,
  "fetched_at": "2025-08-15T12:00:00"
}
```

#### Get Weather Forecast (5-day)
```
GET /agricultural/weather/{region_id}/forecast
```
**Response:**
```json
{
  "region_id": 1,
  "region_name": "Delhi NCR",
  "entries": [
    {
      "datetime_utc": "2025-08-15T15:00:00",
      "temperature_c": 36.0,
      "temperature_min_c": 34.0,
      "temperature_max_c": 38.0,
      "humidity_percentage": 40,
      "rainfall_mm": 0.0,
      "wind_speed_kmh": 10.0,
      "description": "clear sky",
      "icon": "01d"
    }
  ],
  "fetched_at": "2025-08-15T12:00:00"
}
```

---

### 4.6 Crop Health

#### Record Crop Health
```
POST /agricultural/crop-health
```
```json
{
  "region_id": 1,
  "recorded_at": "2025-08-15T00:00:00",
  "ndvi": 0.72,
  "evi": 0.45,
  "crop_stress_index": 0.3,
  "disease_risk": 0.15,
  "vegetation_coverage_percentage": 68.0
}
```
**Required:** `region_id`, `recorded_at`
**Constraints:** `ndvi` (-1 to 1), `crop_stress_index` (0 to 1), `disease_risk` (0 to 1), `vegetation_coverage_percentage` (0 to 100)

#### Get Crop Health History
```
GET /agricultural/crop-health/{region_id}?days_back=30
```

#### Crop Health Analysis
```
GET /agricultural/crop-health/{region_id}/analysis
```

---

## 5. Distribution Network

**Prefix:** `/distribution`

### 5.1 Transportation Corridors

#### Create Corridor
```
POST /distribution/corridors
```
```json
{
  "name": "NH-44 Delhi-Punjab",
  "corridor_code": "COR-NH44-DL-PB",
  "corridor_type": "highway",
  "start_region_id": 1,
  "end_region_id": 2,
  "length_km": 450,
  "daily_capacity_tonnes": 5000,
  "cold_chain_capable": true
}
```
**Required:** `name`, `corridor_code`, `corridor_type`

#### List Corridors
```
GET /distribution/corridors?corridor_type=highway&region_id=1&is_active=true&page=1&page_size=20
```
**Response:** Paginated

#### Get / Update Corridor
```
GET /distribution/corridors/{corridor_id}
PATCH /distribution/corridors/{corridor_id}
```

---

### 5.2 Distribution Centers

#### Create Center
```
POST /distribution/centers
```
```json
{
  "name": "Delhi Central Warehouse",
  "center_code": "DC-DL-001",
  "region_id": 1,
  "latitude": 28.6139,
  "longitude": 77.2090,
  "address": "123 Supply Chain Road, New Delhi",
  "total_capacity_tonnes": 10000,
  "cold_storage_capacity_tonnes": 2000,
  "staff_count": 50,
  "vehicles_available": 20
}
```
**Required:** `name`, `center_code`, `region_id`, `latitude`, `longitude`

#### List Centers
```
GET /distribution/centers?region_id=1&operational_status=operational&is_active=true&page=1&page_size=20
```
**Response:** Paginated

#### Get / Update Center
```
GET /distribution/centers/{center_id}
PATCH /distribution/centers/{center_id}
```

#### Find Nearby Centers
```
GET /distribution/centers/nearby?latitude=28.6&longitude=77.2&radius_km=100&limit=10
```
**Required:** `latitude` (-90 to 90), `longitude` (-180 to 180)
**Defaults:** `radius_km=50` (1-500), `limit=10` (1-50)

---

### 5.3 Transport Routes

#### Create Route Manually
```
POST /distribution/routes
```
```json
{
  "name": "Delhi to Punjab Express",
  "route_code": "RT-DL-PB-001",
  "corridor_id": 1,
  "origin_center_id": 1,
  "destination_center_id": 2,
  "origin_region_id": 1,
  "destination_region_id": 2,
  "distance_km": 450,
  "estimated_time_hours": 8.5,
  "daily_capacity_tonnes": 500,
  "cold_chain_capable": true,
  "is_primary_route": true
}
```
**Required:** `name`, `route_code`

#### List Routes
```
GET /distribution/routes?origin_region_id=1&destination_region_id=2&cold_chain_capable=true&is_active=true
```

#### Get Route
```
GET /distribution/routes/{route_id}
```

#### Auto-Generate Routes (Google Maps API)
```
POST /distribution/routes/auto-generate
```
```json
{
  "center_ids": [1, 2, 3],
  "include_reverse": true,
  "max_routes": 50
}
```
Uses Google Maps Directions API to calculate real distances and travel times between all pairs of distribution centers. Skips routes that already exist.

**Response:**
```json
{
  "total_pairs_considered": 6,
  "routes_created": 6,
  "routes_skipped": 0,
  "results": [
    {
      "origin_center_id": 1,
      "origin_name": "Delhi Central Warehouse",
      "destination_center_id": 2,
      "destination_name": "Punjab Distribution Hub",
      "distance_km": 312.5,
      "duration_hours": 5.2,
      "polyline": "encoded_polyline_string",
      "route_id": 10,
      "status": "created"
    }
  ]
}
```

You can also specify `region_ids` instead of `center_ids` to auto-generate routes for all centers in those regions.

#### Optimize Route (Basic)
```
POST /distribution/routes/optimize
```
```json
{
  "origin_region_id": 1,
  "destination_region_id": 2,
  "cargo_tonnes": 100,
  "requires_cold_chain": false,
  "max_alternatives": 3,
  "avoid_disruptions": true
}
```
**Required:** `origin_region_id`, `destination_region_id`, `cargo_tonnes`

**Response:**
```json
{
  "origin": "Delhi NCR",
  "destination": "Punjab",
  "cargo_tonnes": 100,
  "recommended_route": {
    "route_id": 1,
    "route_name": "Delhi to Punjab Express",
    "distance_km": 312.5,
    "estimated_time_hours": 5.2,
    "estimated_cost": 15625.0,
    "cold_chain_capable": true,
    "disruption_risk": "low",
    "waypoints": []
  },
  "alternative_routes": [],
  "analysis_timestamp": "2025-08-15T12:00:00"
}
```

#### Smart Route Optimization (with Google Maps)
```
POST /distribution/routes/optimize-smart
```
```json
{
  "origin_region_id": 1,
  "destination_region_id": 2,
  "cargo_tonnes": 100,
  "requires_cold_chain": false,
  "max_alternatives": 3,
  "avoid_disruptions": true,
  "use_google_maps": true,
  "optimize_for": "balanced"
}
```
When `use_google_maps` is `true`, uses Google Maps Distance Matrix API for real-time routing. `optimize_for` options: `"time"`, `"cost"`, `"balanced"` (default).

---

### 5.4 Route Disruptions

#### Create Disruption
```
POST /distribution/disruptions
```
```json
{
  "disruption_type": "weather",
  "severity": "critical",
  "title": "Fire blocks NH-44 corridor",
  "route_id": 1,
  "region_id": 1,
  "description": "Forest fire has blocked the primary highway",
  "capacity_reduction_percentage": 100,
  "delay_hours": 48
}
```
**Required:** `disruption_type`, `severity`, `title`

#### List Disruptions
```
GET /distribution/disruptions?region_id=1&disruption_type=weather&severity=critical
```

#### Get Disruption
```
GET /distribution/disruptions/{disruption_id}
```

#### Resolve Disruption
```
POST /distribution/disruptions/{disruption_id}/resolve?resolution_notes=Fire+contained
```

#### Disruption Summary Dashboard
```
GET /distribution/disruptions/summary
```
**Response:**
```json
{
  "total_active": 3,
  "by_severity": {"critical": 1, "high": 1, "medium": 1},
  "by_type": {"weather": 2, "infrastructure": 1},
  "affected_regions": [1, 2],
  "total_capacity_reduction": 250
}
```

---

### 5.5 Cold Chain Facilities

#### Create Facility
```
POST /distribution/cold-chain
```
```json
{
  "name": "Delhi Cold Storage Unit A",
  "facility_code": "CC-DL-001",
  "region_id": 1,
  "latitude": 28.61,
  "longitude": 77.21,
  "total_capacity_tonnes": 500,
  "freezer_capacity_tonnes": 200,
  "chiller_capacity_tonnes": 300,
  "power_source": "grid+solar",
  "backup_power_hours": 48
}
```
**Required:** `name`, `facility_code`, `region_id`, `latitude`, `longitude`

#### List / Capacity
```
GET /distribution/cold-chain?region_id=1&is_active=true
GET /distribution/cold-chain/capacity?region_id=1
```

---

### 5.6 Network Status

```
GET /distribution/status
```
**Response:**
```json
{
  "total_corridors": 5,
  "operational_corridors": 4,
  "total_routes": 12,
  "operational_routes": 10,
  "active_disruptions": 2,
  "network_capacity_utilization": 65.3,
  "cold_chain_capacity_utilization": 42.1
}
```

---

## 6. Food Inventory

**Prefix:** `/inventory`

### 6.1 Food Categories

#### Create Category
```
POST /inventory/categories
```
```json
{
  "name": "Rice & Wheat",
  "category_type": "staple_grains",
  "description": "Primary staple grains",
  "storage_type": "ambient",
  "avg_shelf_life_days": 365,
  "caloric_density": 3500,
  "nutritional_priority": 1,
  "daily_per_capita_kg": 0.4,
  "minimum_per_capita_kg": 0.2
}
```
**Required:** `name`, `category_type`

#### List / Get Categories
```
GET /inventory/categories?is_active=true
GET /inventory/categories/{category_id}
```

---

### 6.2 Food Inventory

#### Create Inventory Record
```
POST /inventory/
```
```json
{
  "region_id": 1,
  "category_id": 1,
  "quantity_tonnes": 5000,
  "consumption_rate_tonnes_per_day": 50,
  "minimum_stock_tonnes": 1000,
  "target_stock_tonnes": 8000,
  "local_production_tonnes": 3000,
  "imported_tonnes": 2000
}
```
**Required:** `region_id`, `category_id`, `quantity_tonnes` (>= 0)

#### Get Inventory by Region
```
GET /inventory/region/{region_id}?category_id=1
```

#### Region Inventory Summary
```
GET /inventory/region/{region_id}/summary
```
**Response:**
```json
{
  "region_id": 1,
  "region_name": "Delhi NCR",
  "total_inventory_tonnes": 15000,
  "days_of_supply": 45.2,
  "stock_status": "adequate",
  "categories_critical": 0,
  "categories_low": 1
}
```

#### Update Inventory
```
PATCH /inventory/{inventory_id}
```
```json
{
  "quantity_tonnes": 4500,
  "consumption_rate_tonnes_per_day": 55
}
```
Use `quantity_change_tonnes` for incremental updates (positive = add, negative = subtract).

---

### 6.3 Warehouse Stocks

#### Create / Get / Update
```
POST /inventory/warehouse-stocks
GET /inventory/warehouse-stocks/{center_id}?category_id=1
PATCH /inventory/warehouse-stocks/{stock_id}
```

---

### 6.4 Consumption Patterns

#### Record Consumption
```
POST /inventory/consumption
```
```json
{
  "region_id": 1,
  "category_id": 1,
  "period_start": "2025-08-01T00:00:00",
  "period_end": "2025-08-07T23:59:59",
  "period_type": "weekly",
  "total_consumption_tonnes": 350,
  "per_capita_kg": 0.025,
  "households_covered": 200000
}
```
**Required:** `region_id`, `category_id`, `period_start`, `period_end`, `period_type` (`"daily"` | `"weekly"` | `"monthly"`), `total_consumption_tonnes`

#### Get Consumption Data
```
GET /inventory/consumption/{region_id}?category_id=1&period_type=weekly
```

#### Detect Anomalies
```
GET /inventory/consumption/{region_id}/anomalies
```

---

## 7. Food Dependency

**Prefix:** `/dependency`

### 7.1 Dependency Profiles

#### Create Profile
```
POST /dependency/profiles
```
```json
{
  "region_id": 1,
  "import_dependency_pct": 60,
  "domestic_production_pct": 30,
  "aid_dependency_pct": 10,
  "strategic_reserve_days": 45,
  "minimum_reserve_days": 14,
  "num_import_sources": 5,
  "primary_port_name": "Mumbai Port",
  "population_at_risk": 500000,
  "vulnerabilities": ["Single port dependency", "Seasonal flooding"],
  "recommendations": ["Diversify import sources", "Increase strategic reserves"]
}
```
**Required:** `region_id`
**Constraints:** percentages are 0-100

#### List Profiles
```
GET /dependency/profiles?risk_level=high&min_risk_score=50&page=1&page_size=20
```
**Response:** Paginated

#### Get Full Profile
```
GET /dependency/profiles/{region_id}
```
Returns a comprehensive `DependencyProfile` with risk analysis.

#### Update Profile
```
PATCH /dependency/profiles/{region_id}
```

---

### 7.2 Import Sources

#### Create / List / Update
```
POST /dependency/import-sources
GET /dependency/import-sources?dependency_id=1&source_country=Thailand&food_type=rice
PATCH /dependency/import-sources/{source_id}
```

---

### 7.3 Food Imports

#### Record Import
```
POST /dependency/imports
```
```json
{
  "region_id": 1,
  "import_date": "2025-08-15T00:00:00",
  "food_type": "rice",
  "source_country": "Thailand",
  "quantity_tonnes": 5000,
  "value_usd": 2500000,
  "port_of_entry": "Mumbai Port",
  "transport_mode": "sea"
}
```
**Required:** `region_id`, `import_date`, `food_type`, `source_country`, `quantity_tonnes` (> 0)

#### List Imports
```
GET /dependency/imports?region_id=1&source_country=Thailand&start_date=2025-01-01T00:00:00&end_date=2025-12-31T23:59:59&page=1&page_size=20
```
**Response:** Paginated

#### Import Summary
```
GET /dependency/imports/{region_id}/summary?start_date=2025-01-01T00:00:00&end_date=2025-12-31T23:59:59
```
Both dates are **required**.

---

### 7.4 Vulnerability Assessments

#### Create / List
```
POST /dependency/assessments
GET /dependency/assessments?region_id=1&min_score=50&limit=20
```

---

### 7.5 Risk Analysis

#### Get Risk Analysis
```
GET /dependency/risk-analysis/{region_id}
```
Returns comprehensive risk breakdown with critical dependencies and mitigation recommendations.

#### Simulate Import Disruption
```
POST /dependency/simulate-disruption?region_id=1&source_country=Thailand&disruption_pct=100
```
**Required query params:** `region_id`, `source_country`
**Default:** `disruption_pct=100` (0-100)

**Response:**
```json
{
  "scenario_name": "Thailand import disruption",
  "description": "100% disruption of imports from Thailand",
  "affected_sources": ["Thai Rice Co"],
  "impact_tonnes": 5000,
  "impact_days_supply": 15,
  "mitigation_options": [...],
  "estimated_recovery_days": 60
}
```

---

## 8. Shortage Alerts

**Prefix:** `/alerts`

### 8.1 Alert CRUD

#### Create Alert
```
POST /alerts/
```
```json
{
  "region_id": 1,
  "alert_type": "shortage",
  "alert_level": "warning",
  "title": "Rice supply running low in Delhi NCR",
  "category_id": 1,
  "description": "Current rice inventory will last only 10 days",
  "food_items_affected": ["rice", "wheat"],
  "days_until_shortage": 10,
  "current_inventory_tonnes": 500,
  "current_days_supply": 10,
  "consumption_rate_tonnes_day": 50,
  "population_affected": 5000000,
  "confidence_score": 0.85,
  "recommended_actions": [
    {"action": "Emergency procurement", "priority": 1},
    {"action": "Activate reserves", "priority": 2}
  ]
}
```
**Required:** `region_id`, `alert_type`, `alert_level`, `title`

#### List Alerts
```
GET /alerts/?region_id=1&alert_type=shortage&alert_level=critical&status=active&is_active=true&page=1&page_size=20
```
**Response:** Paginated

#### Get Alert
```
GET /alerts/{alert_id}
```

#### Update Alert
```
PATCH /alerts/{alert_id}?changed_by=admin
```
```json
{
  "alert_level": "critical",
  "description": "Situation has worsened"
}
```

---

### 8.2 Alert Actions

#### Acknowledge
```
POST /alerts/{alert_id}/acknowledge?acknowledged_by=john.doe
```

#### Escalate
```
POST /alerts/{alert_id}/escalate?escalated_by=john.doe&reason=Situation+critical&escalate_to=team_lead&escalate_to=director
```
**Note:** `escalate_to` is a list — repeat the param for multiple values.

#### Resolve
```
POST /alerts/{alert_id}/resolve?resolved_by=john.doe&resolution_notes=Supply+restored
```

#### View History
```
GET /alerts/{alert_id}/history
```

---

### 8.3 Critical Alerts & Dashboard

#### Get Critical Alerts Only
```
GET /alerts/critical?region_id=1
```

#### Alert Dashboard
```
GET /alerts/dashboard
```
**Response:**
```json
{
  "total_active_alerts": 5,
  "alerts_by_level": {"critical": 1, "warning": 3, "imminent": 1},
  "alerts_by_type": {"shortage": 3, "weather": 2},
  "alerts_by_region": {"1": 3, "2": 2},
  "critical_alerts": [...],
  "recent_alerts": [...],
  "trend_7_days": {"2025-08-09": 1, "2025-08-10": 2}
}
```

---

### 8.4 Predictions

#### Predict Shortages
```
GET /alerts/predictions/shortages?region_id=1
```

#### Auto-Generate Alerts
```
POST /alerts/predictions/auto-generate
```
Scans all inventory and auto-creates alerts for regions at risk. No request body needed.

#### Risk Assessment
```
GET /alerts/predictions/risk-assessment/{region_id}
```

---

### 8.5 Alert Subscriptions

#### Create Subscription
```
POST /alerts/subscriptions
```
```json
{
  "subscriber_name": "Emergency Team",
  "subscriber_email": "emergency@example.com",
  "subscriber_organization": "City Gov",
  "region_ids": [1, 2],
  "alert_types": ["shortage", "weather"],
  "minimum_alert_level": "warning",
  "notify_email": true,
  "notify_sms": false,
  "immediate_notifications": true
}
```
**Required:** `subscriber_name`

#### List Subscriptions
```
GET /alerts/subscriptions?is_active=true
```

---

## 9. Distribution Plans

**Prefix:** `/distribution-plans`

### 9.1 Plans

#### Create Plan
```
POST /distribution-plans/
```
```json
{
  "plan_name": "Delhi Emergency Food Distribution",
  "region_id": 1,
  "alert_id": 5,
  "trigger_reason": "Fire disaster displaced 15M people",
  "activation_date": "2025-08-15T00:00:00",
  "duration_days": 30,
  "population_covered": 5000000,
  "households_covered": 1000000,
  "total_food_tonnes": 15000,
  "total_budget_usd": 5000000,
  "food_allocation": {"1": 8000, "2": 4000, "3": 3000},
  "priority_weights": {
    "elderly": 1.5,
    "children": 1.4,
    "pregnant": 1.3,
    "general": 1.0
  }
}
```
**Required:** `plan_name`, `region_id`

The `food_allocation` keys are category IDs (as strings). The `priority_weights` keys are population types.

#### List Plans
```
GET /distribution-plans/?region_id=1&status=active&page=1&page_size=20
```
**Response:** Paginated

#### Get Plan
```
GET /distribution-plans/{plan_id}
```

#### Update Plan
```
PATCH /distribution-plans/{plan_id}
```

#### Approve Plan
```
POST /distribution-plans/{plan_id}/approve?approved_by=director
```

#### Activate Plan
```
POST /distribution-plans/{plan_id}/activate
```

#### Plan Analytics
```
GET /distribution-plans/{plan_id}/analytics
```

---

### 9.2 Distribution Points

#### Create Point
```
POST /distribution-plans/points
```
```json
{
  "point_name": "Community Center A",
  "region_id": 1,
  "latitude": 28.62,
  "longitude": 77.22,
  "plan_id": 1,
  "center_id": 1,
  "address": "123 Main St",
  "point_type": "fixed",
  "assigned_population": 50000,
  "coverage_radius_km": 5.0,
  "daily_capacity_beneficiaries": 2000,
  "storage_capacity_tonnes": 50,
  "coordinator_name": "Jane Smith",
  "coordinator_phone": "+91-9876543210"
}
```
**Required:** `point_name`, `region_id`, `latitude`, `longitude`, `plan_id`

#### List Points for a Plan
```
GET /distribution-plans/{plan_id}/points?operational_status=active&is_active=true
```

#### Optimize Point Locations
```
POST /distribution-plans/optimize-points
```
```json
{
  "region_id": 1,
  "population_data": {"elderly": 200000, "children": 500000, "general": 3000000},
  "available_food": {"1": 8000, "2": 4000},
  "distribution_centers": [1, 2],
  "max_distribution_points": 50,
  "optimization_goal": "coverage"
}
```

---

### 9.3 Ration Allocations

#### Create Allocation
```
POST /distribution-plans/allocations
```
```json
{
  "plan_id": 1,
  "population_type": "elderly",
  "allocation_date": "2025-08-15",
  "period_start": "2025-08-15T00:00:00",
  "period_end": "2025-08-21T23:59:59",
  "population_count": 200000,
  "ration_composition": {"rice_kg": 5, "wheat_kg": 3, "oil_liters": 1},
  "total_ration_kg": 9,
  "calories_per_ration": 2200,
  "daily_caloric_target": 2000
}
```
**Required:** `plan_id`, `population_type`, `allocation_date`, `ration_composition`, `total_ration_kg`, `calories_per_ration`

#### Auto-Calculate Rations
```
POST /distribution-plans/{plan_id}/calculate-rations
```
```json
{
  "1": 8000.0,
  "2": 4000.0
}
```
Request body is a dict of `{category_id: available_tonnes}`.

---

### 9.4 Vulnerable Populations

#### Register Vulnerable Population
```
POST /distribution-plans/vulnerable-populations
```
```json
{
  "region_id": 1,
  "population_type": "elderly",
  "total_count": 200000,
  "households_count": 150000,
  "registered_count": 180000,
  "daily_caloric_need": 1800,
  "special_dietary_needs": ["low sodium", "soft foods"],
  "priority_level": 1,
  "mobility_limited_pct": 30.0,
  "requires_home_delivery_pct": 15.0
}
```
**Required:** `region_id`, `population_type`, `total_count`, `priority_level` (1-5)

#### Get by Region
```
GET /distribution-plans/vulnerable-populations/{region_id}
```

#### Population Counts
```
GET /distribution-plans/vulnerable-populations/{region_id}/counts
```

---

### 9.5 Distribution Records

#### Record Distribution
```
POST /distribution-plans/records
```
```json
{
  "plan_id": 1,
  "distribution_point_id": 1,
  "allocation_id": 1,
  "household_size": 4,
  "population_type": "general",
  "items_distributed": {"rice_kg": 5, "wheat_kg": 3},
  "total_weight_kg": 8
}
```
**Required:** `plan_id`, `distribution_point_id`, `items_distributed`, `total_weight_kg`

---

### 9.6 Coverage Analysis

```
GET /distribution-plans/coverage/{region_id}?plan_id=1
```
**Response:**
```json
{
  "region_id": 1,
  "total_population": 20000000,
  "covered_population": 5000000,
  "coverage_percentage": 25.0,
  "coverage_by_type": {"elderly": 90.0, "children": 85.0, "general": 20.0},
  "underserved_areas": [...],
  "recommendations": ["Add distribution points in south Delhi"]
}
```

---

## 10. Agricultural Resilience

**Prefix:** `/resilience`

### 10.1 Urban Agriculture Sites

#### Create / List / Get / Update
```
POST /resilience/urban-agriculture
GET /resilience/urban-agriculture?region_id=1&site_type=vertical_farm&status=operational&page=1&page_size=20
GET /resilience/urban-agriculture/{site_id}
PATCH /resilience/urban-agriculture/{site_id}
```

#### Regional Summary
```
GET /resilience/urban-agriculture/summary/{region_id}
```

---

### 10.2 Crop Diversification

```
POST /resilience/diversification
GET /resilience/diversification?region_id=1&status=approved
GET /resilience/diversification/{plan_id}
POST /resilience/diversification/generate/{region_id}  (auto-generates recommendations)
```

---

### 10.3 Resilience Recommendations

```
POST /resilience/recommendations
GET /resilience/recommendations?region_id=1&category=infrastructure&status=pending&limit=50
POST /resilience/recommendations/generate/{region_id}  (auto-generates)
```

---

### 10.4 Land Conversion Opportunities

```
POST /resilience/land-conversion
GET /resilience/land-conversion?region_id=1&current_use=vacant&min_feasibility=0.5
```

---

### 10.5 Resilience Assessments

```
GET /resilience/assessment/{region_id}       — SWOT-style assessment
GET /resilience/summary/{region_id}          — quick summary with score and trend
```

---

## 11. Fire Disaster Simulation

**Prefix:** `/fire-disaster`

This is the **core pipeline endpoint** — a single POST that runs an automated 8-step disaster response.

### Run Simulation

```
POST /fire-disaster/simulate
```

```json
{
  "latitude": 28.6139,
  "longitude": 77.2090,
  "radius_km": 200,
  "fire_intensity": 0.8,
  "displacement_pct": 0.4
}
```

| Field | Type | Required | Range | Default | Description |
|-------|------|----------|-------|---------|-------------|
| `latitude` | float | Yes | -90 to 90 | — | Fire origin latitude |
| `longitude` | float | Yes | -180 to 180 | — | Fire origin longitude |
| `radius_km` | float | No | 5 to 500 | 50 | Scan radius for affected regions |
| `fire_intensity` | float | No | 0.1 to 1.0 | 0.7 | Severity (0.1=minor, 1.0=catastrophic) |
| `displacement_pct` | float | No | 0.0 to 1.0 | 0.4 | Fraction of population displaced |

### Response Structure

```json
{
  "scenario_id": "FIRE-20250815-abc123",
  "fire_location": {"latitude": 28.6139, "longitude": 77.2090},
  "started_at": "2025-08-15T12:00:00",
  "completed_at": "2025-08-15T12:00:01",
  "duration_seconds": 0.58,

  "step_1_weather": {
    "temperature_c": 42.0,
    "humidity_pct": 20.0,
    "wind_speed_kmh": 25.0,
    "wind_direction": "SW",
    "rainfall_mm": 0.0,
    "description": "clear sky",
    "fire_weather_risk": "extreme"
  },

  "step_2_zones": {
    "total_regions_scanned": 3,
    "affected_zones": [
      {
        "region_id": 1,
        "region_name": "Delhi NCR",
        "distance_km": 0.0,
        "severity": "critical",
        "population": 20000000,
        "wind_exposed": true
      }
    ]
  },

  "step_3_disruptions": {
    "routes_scanned": 12,
    "disruptions_created": 4,
    "disruptions": [
      {
        "disruption_id": 10,
        "route_id": 1,
        "route_name": "Delhi-Punjab Route",
        "severity": "blocked",
        "status": "active"
      }
    ]
  },

  "step_4_displacement": {
    "total_displaced": 8000000,
    "entries": [
      {
        "from_region_id": 1,
        "from_region_name": "Delhi NCR",
        "to_region_id": 3,
        "to_region_name": "Maharashtra",
        "displaced_count": 5000000
      }
    ]
  },

  "step_5_supply": {
    "regions_updated": 3,
    "entries": [
      {
        "region_id": 3,
        "region_name": "Maharashtra",
        "original_population": 12000000,
        "effective_population": 17000000,
        "demand_multiplier": 1.42,
        "estimated_days_of_supply": 28.5
      }
    ]
  },

  "step_6_alerts": {
    "alerts_generated": 2,
    "alerts": [
      {
        "alert_id": 15,
        "alert_code": "ALT-FIRE-001",
        "region_id": 1,
        "region_name": "Delhi NCR",
        "level": "critical",
        "title": "Fire disaster: critical shortage in Delhi NCR"
      }
    ]
  },

  "step_7_reroute": {
    "blocked_routes": 4,
    "alternative_routes_created": 2,
    "alternatives": [
      {
        "route_id": 20,
        "origin": "Punjab Hub",
        "destination": "Maharashtra Hub",
        "distance_km": 1650.0,
        "duration_hours": 24.5
      }
    ]
  },

  "step_8_distribution": {
    "plans_created": 2,
    "plans": [
      {
        "plan_id": 5,
        "plan_code": "DP-FIRE-001",
        "region_id": 3,
        "region_name": "Maharashtra",
        "population_covered": 17000000,
        "food_allocated_tonnes": 680.0,
        "distribution_points": 5,
        "priority_groups": ["elderly", "children", "pregnant"]
      }
    ]
  },

  "summary": {
    "total_affected_population": 20000000,
    "total_displaced": 8000000,
    "disruptions_created": 4,
    "alerts_raised": 2,
    "alternative_routes": 2,
    "distribution_plans": 2
  }
}
```

### Pipeline Steps Explained

| Step | What It Does | Data Written to DB |
|------|-------------|-------------------|
| 1. Weather Check | Fetches live weather from OpenWeatherMap at fire coordinates. Calculates fire weather risk (low/moderate/high/extreme) based on temperature, humidity, and wind. | None |
| 2. Flag Zones | Finds all regions within `radius_km` using haversine distance. Assigns severity: critical (<30% of radius), high (<60%), moderate (<100%). Checks if wind direction exposes the zone. | None |
| 3. Create Disruptions | Finds all transport routes touching affected regions. Creates `RouteDisruption` records with severity: blocked (critical zones), restricted (high), impaired (moderate). | `RouteDisruption` |
| 4. Displace Population | Models population movement from affected zones to unaffected regions. Displacement scaled by severity (critical=100%, high=60%, moderate=30% of `displacement_pct`). | None |
| 5. Recalculate Supply | For regions receiving displaced people, calculates new effective population and demand multiplier. Estimates days of supply based on current inventory. | None |
| 6. Generate Alerts | Creates `ShortageAlert` records for affected regions. Alert level based on days of supply: <7 = CRITICAL, <14 = IMMINENT, <30 = WARNING. | `ShortageAlert` |
| 7. Reroute | Finds blocked routes. Uses Google Maps Directions API to find alternative routes bypassing affected regions. Creates new `TransportRoute` records. | `TransportRoute` |
| 8. Optimize Distribution | Creates `DistributionPlan` records for all regions receiving displaced population. Allocates food based on effective population and priority groups. | `DistributionPlan` |

### Django Integration Example

```python
# views.py
import requests
from django.http import JsonResponse

def simulate_fire(request):
    if request.method == "POST":
        data = json.loads(request.body)
        response = requests.post(
            f"{settings.SENTINEL_API_BASE}/fire-disaster/simulate",
            json={
                "latitude": data["latitude"],
                "longitude": data["longitude"],
                "radius_km": data.get("radius_km", 50),
                "fire_intensity": data.get("fire_intensity", 0.7),
                "displacement_pct": data.get("displacement_pct", 0.4),
            }
        )
        return JsonResponse(response.json())
```

---

## 12. Pagination

Paginated endpoints return this structure:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

**Query params:** `page` (default 1, min 1), `page_size` (default 20, max varies by endpoint — typically 20-100).

**Paginated endpoints:**
- `GET /agricultural/regions`
- `GET /distribution/corridors`
- `GET /distribution/centers`
- `GET /dependency/profiles`
- `GET /dependency/imports`
- `GET /alerts/`
- `GET /distribution-plans/`
- `GET /resilience/urban-agriculture`

---

## 13. Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created (some POST endpoints) |
| `400` | Bad request — invalid input, validation error |
| `404` | Resource not found |
| `422` | Validation error — Pydantic schema validation failed |
| `500` | Internal server error |

### Error Response Format

```json
{
  "detail": "Region with id 999 not found"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "latitude"],
      "msg": "ensure this value is greater than or equal to -90",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### Django Error Handling

```python
import requests

def api_call(path, method="get", **kwargs):
    try:
        r = getattr(requests, method)(f"{settings.SENTINEL_API_BASE}{path}", **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise Http404("Resource not found")
        elif e.response.status_code == 422:
            errors = e.response.json().get("detail", [])
            # Map to Django form errors
            raise ValidationError(errors)
        else:
            raise
```

---

## 14. Django Integration Guide

### Recommended Architecture

```
your_django_project/
├── sentinel/                    # Django app for SENTINEL integration
│   ├── api_client.py           # HTTP client for all API calls
│   ├── views.py                # Django views calling the API
│   ├── urls.py                 # URL routing
│   ├── forms.py                # Django forms for data input
│   └── templates/
│       └── sentinel/
│           ├── dashboard.html
│           ├── regions/
│           ├── distribution/
│           ├── alerts/
│           └── fire_simulation/
```

### API Client Class

```python
# sentinel/api_client.py
import requests
from django.conf import settings


class SentinelAPIClient:
    """Client for SENTINEL-HEALTH Module 3 API."""

    def __init__(self):
        self.base_url = settings.SENTINEL_API_BASE  # "http://localhost:8023/api/v1"
        self.timeout = 30  # seconds (fire simulation may take longer)

    def _request(self, method, path, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        url = f"{self.base_url}{path}"
        response = getattr(requests, method)(url, **kwargs)
        response.raise_for_status()
        return response.json()

    # --- Regions ---
    def list_regions(self, page=1, page_size=20, **filters):
        params = {"page": page, "page_size": page_size, **filters}
        return self._request("get", "/agricultural/regions", params=params)

    def get_region(self, region_id):
        return self._request("get", f"/agricultural/regions/{region_id}")

    def create_region(self, data):
        return self._request("post", "/agricultural/regions", json=data)

    # --- Weather ---
    def fetch_live_weather(self, region_id, save_to_db=True):
        return self._request(
            "post",
            f"/agricultural/weather/{region_id}/fetch",
            params={"save_to_db": save_to_db}
        )

    def get_weather_forecast(self, region_id):
        return self._request("get", f"/agricultural/weather/{region_id}/forecast")

    # --- Distribution ---
    def list_centers(self, page=1, page_size=20, **filters):
        params = {"page": page, "page_size": page_size, **filters}
        return self._request("get", "/distribution/centers", params=params)

    def find_nearby_centers(self, lat, lon, radius_km=50):
        return self._request("get", "/distribution/centers/nearby", params={
            "latitude": lat, "longitude": lon, "radius_km": radius_km
        })

    def auto_generate_routes(self, center_ids, include_reverse=True):
        return self._request("post", "/distribution/routes/auto-generate", json={
            "center_ids": center_ids, "include_reverse": include_reverse
        })

    # --- Alerts ---
    def get_alert_dashboard(self):
        return self._request("get", "/alerts/dashboard")

    def get_critical_alerts(self, region_id=None):
        params = {"region_id": region_id} if region_id else {}
        return self._request("get", "/alerts/critical", params=params)

    def auto_generate_alerts(self):
        return self._request("post", "/alerts/predictions/auto-generate")

    # --- Fire Disaster ---
    def simulate_fire(self, latitude, longitude, radius_km=50,
                      fire_intensity=0.7, displacement_pct=0.4):
        return self._request("post", "/fire-disaster/simulate", json={
            "latitude": latitude,
            "longitude": longitude,
            "radius_km": radius_km,
            "fire_intensity": fire_intensity,
            "displacement_pct": displacement_pct,
        }, timeout=60)  # pipeline may take longer

    # --- Inventory ---
    def get_inventory_summary(self, region_id):
        return self._request("get", f"/inventory/region/{region_id}/summary")

    # --- Network Status ---
    def get_network_status(self):
        return self._request("get", "/distribution/status")
```

### Example View — Fire Disaster

```python
# sentinel/views.py
from django.shortcuts import render
from django.http import JsonResponse
from .api_client import SentinelAPIClient

api = SentinelAPIClient()


def fire_simulation_view(request):
    if request.method == "POST":
        result = api.simulate_fire(
            latitude=float(request.POST["latitude"]),
            longitude=float(request.POST["longitude"]),
            radius_km=float(request.POST.get("radius_km", 50)),
            fire_intensity=float(request.POST.get("fire_intensity", 0.7)),
            displacement_pct=float(request.POST.get("displacement_pct", 0.4)),
        )
        return render(request, "sentinel/fire_simulation/results.html", {
            "result": result,
            "summary": result["summary"],
            "weather": result["step_1_weather"],
            "zones": result["step_2_zones"]["affected_zones"],
            "alerts": result["step_6_alerts"]["alerts"],
            "plans": result["step_8_distribution"]["plans"],
        })
    return render(request, "sentinel/fire_simulation/form.html")


def dashboard_view(request):
    alerts = api.get_alert_dashboard()
    network = api.get_network_status()
    return render(request, "sentinel/dashboard.html", {
        "alerts": alerts,
        "network": network,
    })
```

### Key Map Integration Notes

For the map-based fire simulation UI:

1. **User clicks on map** → captures `latitude` and `longitude`
2. **Slider controls** for `radius_km` (5-500), `fire_intensity` (0.1-1.0), `displacement_pct` (0-1.0)
3. **POST to `/fire-disaster/simulate`** with these values
4. **Display results on map:**
   - Fire origin marker (red)
   - Affected zones as circles/polygons colored by severity (critical=red, high=orange, moderate=yellow)
   - Disrupted routes as dashed red lines
   - Alternative routes as green lines
   - Distribution centers as blue markers
   - Distribution points as green markers
5. **Side panel** shows the summary stats, alerts list, and distribution plans

### CORS

The backend already has CORS configured to allow all origins (`allow_origins=["*"]`). No additional CORS setup is needed on the Django side.

---

## Endpoint Count Summary

| Module | Prefix | Endpoints |
|--------|--------|-----------|
| Global | `/` | 4 |
| Agricultural Production | `/agricultural` | 20 |
| Distribution Network | `/distribution` | 18 |
| Food Inventory | `/inventory` | 12 |
| Food Dependency | `/dependency` | 14 |
| Shortage Alerts | `/alerts` | 15 |
| Distribution Plans | `/distribution-plans` | 16 |
| Agricultural Resilience | `/resilience` | 15 |
| Fire Disaster | `/fire-disaster` | 1 |
| **Total** | | **115** |

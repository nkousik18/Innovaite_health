# SENTINEL-HEALTH: Database & API Structure

## Database Overview

**Engine:** PostgreSQL 14+ with async driver (`asyncpg`)
**ORM:** SQLAlchemy 2.0 (async sessions)
**Migrations:** Alembic
**Cache:** Redis 7+

All tables inherit `id` (Integer PK, auto-increment), `created_at`, and `updated_at` from a shared base model.

---

## Entity-Relationship Diagram (Simplified)

```
regions ──────────────────────────────────────────────────────────────
  │ 1:N          1:N        1:N         1:1          1:N          1:N
  ▼              ▼          ▼           ▼            ▼            ▼
agricultural   food      distribution  regional    shortage    distribution
_production  _inventory  _centers    _dependencies  _alerts      _plans
  │                         │           │                         │
  │                         │           │ 1:N                     │ 1:N
  ▼                         ▼           ▼                         ▼
harvest                 warehouse    import                  distribution
_forecasts              _stocks      _sources                _points
                                        │                         │
                                        │ 1:N                     │ 1:N
                                        ▼                         ▼
                                    food_imports             ration_allocations
```

---

## Database Tables

### 1. Agricultural Domain

#### `regions`
Central reference table for all geographic regions.

| Column | Type | Constraints | Description |
|---|---|---|---|
| name | String(255) | NOT NULL, indexed | Region display name |
| country | String(100) | NOT NULL, indexed | Country code/name |
| region_code | String(50) | UNIQUE, NOT NULL | Machine-readable identifier |
| latitude / longitude | Float | NOT NULL | Center-point GPS coordinates |
| area_sq_km | Float | — | Total land area |
| population | Integer | — | Total population |
| population_density | Float | — | People per sq km |
| arable_land_sq_km | Float | — | Farmable land area |
| irrigation_coverage | Float | — | % of land with irrigation |
| climate_zone | String(50) | — | Köppen climate classification |
| drought_risk / flood_risk / conflict_risk | Float (0–1) | — | Risk scores |
| geometry | JSON | — | GeoJSON polygon boundary |
| is_active | Boolean | default=True | Soft delete flag |

#### `crops`
Reference table for crop types and nutritional data.

| Column | Type | Constraints | Description |
|---|---|---|---|
| name | String(100) | UNIQUE, NOT NULL | Common crop name |
| crop_type | Enum | NOT NULL | STAPLE_GRAIN, PROTEIN, VEGETABLE, FRUIT, LEGUME, TUBER, OIL_SEED, OTHER |
| calories_per_100g | Float | — | Energy density |
| protein_g / carbs_g / fat_g / fiber_g | Float | — | Macronutrient profile |
| shelf_life_days | Integer | — | Days before spoilage |
| requires_cold_chain | Boolean | default=False | Needs refrigerated transport |
| growing_season | Enum | — | SPRING, SUMMER, FALL, WINTER, WET, DRY, YEAR_ROUND |
| days_to_harvest | Integer | — | Planting-to-harvest duration |
| avg_yield_kg_per_hectare | Float | — | Expected yield benchmark |

#### `agricultural_production`
Historical crop output records per region per year.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Region reference |
| crop_id | FK → crops | NOT NULL | Crop reference |
| year | Integer | NOT NULL | Production year |
| season | Enum | — | Growing season |
| planted_area_hectares | Float | — | Area planted |
| harvested_area_hectares | Float | — | Area successfully harvested |
| production_tonnes | Float | — | Total output |
| yield_kg_per_hectare | Float | — | Output per unit area |
| loss_percentage | Float (0–100) | — | Post-harvest loss |
| drought_affected / flood_affected | Boolean | default=False | Weather impact flags |
| weather_impact_score | Float (-1 to 1) | — | Net weather effect on yield |

**Indexes:** `(region_id, year)`, `(crop_id, year)`

#### `harvest_forecasts`
AI-generated yield predictions.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Target region |
| crop_id | FK → crops | NOT NULL | Target crop |
| forecast_date | DateTime | NOT NULL | When prediction was made |
| target_date | DateTime | NOT NULL | Predicted harvest date |
| predicted_yield_tonnes | Float | NOT NULL | Point estimate |
| predicted_yield_lower / _upper | Float | — | Confidence interval bounds |
| confidence_score | Float (0–1) | — | Model confidence |
| weather_risk / labor_risk / input_supply_risk | Float (0–1) | — | Risk factor scores |
| model_name / model_version | String | — | Traceability fields |

**Indexes:** `(region_id, crop_id)`, `(target_date)`

#### `weather_data`
Time-series weather observations per region.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Region reference |
| recorded_at | DateTime | NOT NULL | Observation timestamp |
| temperature_c / min / max | Float | — | Temperature readings |
| rainfall_mm | Float | — | Precipitation |
| humidity_percentage | Float | — | Relative humidity |
| is_drought / is_flood / is_frost / is_heatwave | Boolean | default=False | Extreme weather flags |

**Indexes:** `(region_id, recorded_at)`

#### `crop_health_indicators`
Satellite-derived vegetation health metrics.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Region reference |
| recorded_at | DateTime | NOT NULL | Observation date |
| ndvi | Float (-1 to 1) | — | Normalized Difference Vegetation Index |
| crop_stress_index | Float (0–1) | — | Composite stress metric |
| disease_risk / pest_risk | Float (0–1) | — | Biotic threat scores |
| satellite_name | String(50) | — | Data source satellite |

**Indexes:** `(region_id, recorded_at)`

---

### 2. Inventory Domain

#### `food_categories`
Reference table for food classification and storage requirements.

| Column | Type | Constraints | Description |
|---|---|---|---|
| name | String(100) | UNIQUE, NOT NULL | Category name |
| category_type | Enum | NOT NULL | STAPLE_GRAINS, PROTEIN, VEGETABLES, FRUITS, DAIRY, OILS_FATS, SHELF_STABLE, BEVERAGES, INFANT_FOOD, MEDICAL_NUTRITION |
| storage_type | Enum | default=AMBIENT | AMBIENT, REFRIGERATED, FROZEN, CONTROLLED |
| avg_shelf_life_days | Integer | — | Typical shelf life |
| caloric_density | Float | — | kcal per kg |
| daily_per_capita_kg | Float | — | Recommended daily intake |

#### `food_inventory`
Regional food stock levels over time.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Region reference |
| category_id | FK → food_categories | NOT NULL | Food category |
| recorded_at | DateTime | NOT NULL | Snapshot timestamp |
| quantity_tonnes | Float | NOT NULL | Current stock level |
| days_of_supply | Float | — | Computed: stock / consumption rate |
| consumption_rate_tonnes_per_day | Float | — | Daily drawdown rate |
| stock_status | String(20) | — | critical / low / adequate / surplus |
| local_production_tonnes | Float | — | Domestically produced portion |
| imported_tonnes | Float | — | Imported portion |

**Indexes:** `(region_id, category_id)`, `(recorded_at)`

#### `warehouse_stocks`
Per-facility, per-category granular stock tracking.

| Column | Type | Constraints | Description |
|---|---|---|---|
| distribution_center_id | FK → distribution_centers | NOT NULL | Facility reference |
| category_id | FK → food_categories | NOT NULL | Food category |
| quantity_tonnes | Float | NOT NULL | Current quantity |
| current_temp_c | Float | — | Real-time temperature |
| temp_in_range | Boolean | default=True | Temperature compliance |
| quality_hold | Boolean | default=False | Quarantine flag |
| inbound_today / outbound_today | Float | — | Daily throughput |

**Indexes:** `(distribution_center_id)`, `(recorded_at)`

#### `consumption_patterns`
Aggregated consumption data with anomaly flags.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Region reference |
| category_id | FK → food_categories | NOT NULL | Food category |
| period_start / period_end | DateTime | NOT NULL | Observation window |
| period_type | String(20) | — | daily / weekly / monthly |
| total_consumption_tonnes | Float | — | Aggregate consumption |
| consumption_trend | String(20) | — | increasing / stable / decreasing |
| anomaly_detected | Boolean | default=False | Unusual pattern flag |
| anomaly_score | Float (0–1) | — | Anomaly severity |

**Indexes:** `(region_id, category_id)`, `(period_start)`

---

### 3. Distribution Network Domain

#### `transportation_corridors`
Major logistics routes (highways, rail, waterways, air).

| Column | Type | Constraints | Description |
|---|---|---|---|
| name | String(255) | NOT NULL | Corridor name |
| corridor_code | String(50) | UNIQUE, NOT NULL | Identifier |
| corridor_type | Enum | NOT NULL | HIGHWAY, RAIL, WATERWAY, AIR, PIPELINE |
| start_region_id / end_region_id | FK → regions | — | Terminus regions |
| length_km | Float | — | Total length |
| daily_capacity_tonnes | Float | — | Throughput capacity |
| cold_chain_capable | Boolean | default=False | Supports refrigerated cargo |
| operational_status | String(50) | default='operational' | Current status |

#### `distribution_centers`
Warehousing and logistics hubs.

| Column | Type | Constraints | Description |
|---|---|---|---|
| name | String(255) | NOT NULL | Facility name |
| center_code | String(50) | UNIQUE, NOT NULL | Identifier |
| region_id | FK → regions | NOT NULL | Host region |
| latitude / longitude | Float | NOT NULL | GPS coordinates |
| total_capacity_tonnes | Float | — | Max storage |
| current_inventory_tonnes | Float | — | Current load |
| cold_storage_capacity_tonnes | Float | — | Refrigerated capacity |
| vehicles_available | Integer | — | Fleet size |
| operational_status | String(50) | default='operational' | Current status |

**Indexes:** `(region_id)`, `(latitude, longitude)`

#### `transport_routes`
Specific routes between distribution centers along corridors.

| Column | Type | Constraints | Description |
|---|---|---|---|
| route_code | String(50) | UNIQUE, NOT NULL | Identifier |
| corridor_id | FK → transportation_corridors | — | Parent corridor |
| origin_center_id / destination_center_id | FK → distribution_centers | — | Endpoints |
| origin_region_id / destination_region_id | FK → regions | — | Region endpoints |
| distance_km | Float | — | Route length |
| estimated_time_hours | Float | — | Transit time |
| daily_capacity_tonnes | Float | — | Throughput |
| cold_chain_capable | Boolean | default=False | Refrigerated support |
| is_primary_route | Boolean | default=False | Preferred route flag |

**Indexes:** `(origin_region_id, destination_region_id)`

#### `route_disruptions`
Active and historical disruption events.

| Column | Type | Constraints | Description |
|---|---|---|---|
| corridor_id | FK → transportation_corridors | — | Affected corridor |
| route_id | FK → transport_routes | — | Affected route |
| disruption_type | Enum | NOT NULL | LOCKDOWN, INFRASTRUCTURE, WEATHER, CONFLICT, FUEL_SHORTAGE, BORDER_CLOSURE, CIVIL_UNREST, ACCIDENT, MAINTENANCE |
| severity | Enum | NOT NULL | LOW, MEDIUM, HIGH, CRITICAL |
| title | String(255) | NOT NULL | Disruption headline |
| started_at | DateTime | NOT NULL | Start timestamp |
| expected_end_at / actual_end_at | DateTime | — | Duration tracking |
| capacity_reduction_percentage | Float | — | Impact on throughput |

**Indexes:** `(is_active)`, `(disruption_type, severity)`

#### `cold_chain_facilities`
Specialized cold storage infrastructure.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Host region |
| distribution_center_id | FK → distribution_centers | — | Parent facility |
| total_capacity_tonnes | Float | — | Total cold storage |
| freezer_capacity / chiller_capacity / cool_room_capacity | Float | — | Zone capacities |
| backup_power_hours | Float | — | Backup generator runtime |
| temperature_alert | Boolean | default=False | Active temp excursion |

---

### 4. Dependency & Risk Domain

#### `regional_dependencies`
One-per-region import dependency profile.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | UNIQUE, NOT NULL | Target region |
| import_dependency_pct | Float | — | % of food imported |
| domestic_production_pct | Float | — | % produced locally |
| aid_dependency_pct | Float | — | % from aid programs |
| strategic_reserve_days | Float | — | Current reserve duration |
| num_import_sources | Integer | — | Supplier diversity count |
| single_source_dependency | Boolean | default=False | Over-reliance flag |
| port_dependency | Boolean | default=False | Maritime reliance flag |
| risk_score | Float (0–100) | — | Composite risk score |
| overall_risk_level | Enum | — | LOW, MEDIUM, HIGH, CRITICAL |

**Indexes:** `(overall_risk_level)`

#### `import_sources`
Per-source, per-food-type import profiles.

| Column | Type | Constraints | Description |
|---|---|---|---|
| dependency_id | FK → regional_dependencies | NOT NULL | Parent profile |
| source_country | String(100) | NOT NULL | Exporting country |
| food_type | String(100) | NOT NULL | Food category |
| is_primary_source | Boolean | default=False | Main supplier flag |
| annual_volume_tonnes | Float | — | Yearly import volume |
| share_of_imports_pct | Float (0–100) | — | % of total imports |
| reliability_score | Float (0–1) | — | Delivery reliability |
| political_risk / logistics_risk / price_volatility | Float (0–1) | — | Risk dimensions |

**Indexes:** `(source_country)`, `(food_type)`

#### `food_imports`
Individual import shipment records.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Destination region |
| source_id | FK → import_sources | — | Source profile link |
| import_date | DateTime | NOT NULL | Arrival date |
| food_type | String(100) | NOT NULL | Commodity type |
| source_country | String(100) | NOT NULL | Origin country |
| quantity_tonnes | Float | NOT NULL | Shipment size |
| customs_cleared | Boolean | default=False | Customs status |
| delay_days | Integer | default=0 | Days delayed |

**Indexes:** `(region_id, import_date)`, `(source_country)`

#### `vulnerability_assessments`
Periodic region-level vulnerability scoring.

| Column | Type | Constraints | Description |
|---|---|---|---|
| dependency_id | FK → regional_dependencies | NOT NULL | Parent profile |
| region_id | FK → regions | NOT NULL | Target region |
| overall_score | Float (0–100) | NOT NULL | Composite vulnerability |
| production_score / import_score / distribution_score / storage_score / economic_score | Float (0–100) | — | Dimension scores |
| climate_risk / conflict_risk / economic_risk / health_risk | Float | — | Risk factors |
| trend_direction | String(20) | — | improving / stable / declining |
| status | String(20) | — | draft / final / approved |

**Indexes:** `(region_id, assessment_date)`, `(overall_score)`

---

### 5. Alerts Domain

#### `shortage_alerts`
Predictive and manually created food shortage alerts.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Affected region |
| category_id | FK → food_categories | — | Affected food type |
| alert_code | String(50) | UNIQUE, NOT NULL | Identifier |
| alert_type | Enum | NOT NULL | SHORTAGE, PRODUCTION, DISTRIBUTION, PRICE, QUALITY, IMPORT, WEATHER |
| alert_level | Enum | NOT NULL | NORMAL, WARNING, IMMINENT, CRITICAL |
| status | Enum | default=ACTIVE | ACTIVE, ACKNOWLEDGED, RESPONDING, RESOLVED, ESCALATED, FALSE_ALARM |
| title | String(255) | NOT NULL | Alert headline |
| predicted_shortage_date | DateTime | — | Projected stockout date |
| days_until_shortage | Integer | — | Time to stockout |
| current_days_supply | Float | — | Current runway |
| confidence_score | Float (0–1) | — | Model confidence |
| population_affected | Integer | — | People impacted |
| recommended_actions | JSON | — | Suggested interventions |

**Indexes:** `(region_id, alert_level)`, `(status)`, `(alert_type, created_at)`

#### `alert_history`
Audit trail of alert level/status changes.

| Column | Type | Constraints | Description |
|---|---|---|---|
| alert_id | FK → shortage_alerts | NOT NULL | Parent alert |
| changed_at | DateTime | NOT NULL | Timestamp |
| changed_by | String(100) | — | User/system identifier |
| previous_level / new_level | Enum | — | Level transition |
| previous_status / new_status | Enum | — | Status transition |
| change_reason | Text | — | Justification |

#### `alert_subscriptions`
Notification preferences for stakeholders.

| Column | Type | Constraints | Description |
|---|---|---|---|
| subscriber_name | String(100) | NOT NULL | Contact name |
| subscriber_email | String(255) | — | Email address |
| region_ids | JSON | — | Regions of interest |
| minimum_alert_level | Enum | default=WARNING | Lowest level to notify |
| notify_email / notify_sms / notify_webhook | Boolean | — | Channel preferences |

#### `alert_actions`
Recommended and tracked response actions per alert.

| Column | Type | Constraints | Description |
|---|---|---|---|
| alert_id | FK → shortage_alerts | NOT NULL | Parent alert |
| action_type | String(50) | NOT NULL | Action category |
| action_title | String(255) | NOT NULL | Action description |
| priority | Integer | — | Urgency ranking |
| status | String(50) | default='recommended' | Progress status |
| assigned_to | String(100) | — | Responsible party |
| effectiveness_score | Float (0–1) | — | Post-action evaluation |

---

### 6. Distribution Plans Domain

#### `distribution_plans`
Crisis food distribution plans tied to regions and alerts.

| Column | Type | Constraints | Description |
|---|---|---|---|
| plan_code | String(50) | UNIQUE, NOT NULL | Identifier |
| plan_name | String(255) | NOT NULL | Plan title |
| region_id | FK → regions | NOT NULL | Target region |
| alert_id | FK → shortage_alerts | — | Triggering alert |
| status | Enum | default=DRAFT | DRAFT, PENDING_APPROVAL, APPROVED, ACTIVE, COMPLETED, CANCELLED |
| population_covered | Integer | — | People served |
| total_food_tonnes | Float | — | Total food allocated |
| total_budget_usd | Float | — | Budget |
| completion_pct | Float | default=0 | Progress tracker |
| food_distributed_tonnes | Float | default=0 | Actual output |
| beneficiaries_served | Integer | default=0 | Actual reach |

**Indexes:** `(region_id, status)`, `(activation_date, end_date)`

#### `distribution_points`
Physical locations where food is distributed to beneficiaries.

| Column | Type | Constraints | Description |
|---|---|---|---|
| plan_id | FK → distribution_plans | NOT NULL | Parent plan |
| center_id | FK → distribution_centers | — | Hosting facility |
| region_id | FK → regions | NOT NULL | Location region |
| point_code | String(50) | UNIQUE, NOT NULL | Identifier |
| latitude / longitude | Float | NOT NULL | GPS location |
| assigned_population | Integer | — | People assigned |
| daily_capacity_beneficiaries | Integer | — | Daily throughput |
| operational_status | String(50) | default='planned' | Current status |

**Indexes:** `(plan_id)`, `(latitude, longitude)`

#### `ration_allocations`
Per-population-group food allocation plans.

| Column | Type | Constraints | Description |
|---|---|---|---|
| plan_id | FK → distribution_plans | NOT NULL | Parent plan |
| distribution_point_id | FK → distribution_points | — | Distribution site |
| population_type | Enum | NOT NULL | ELDERLY, CHILDREN, PREGNANT, IMMUNOCOMPROMISED, HEALTHCARE_WORKER, ESSENTIAL_WORKER, DISABLED, LOW_INCOME, GENERAL |
| ration_composition | JSON | — | Food items and quantities |
| total_ration_kg | Float | — | Weight per ration |
| calories_per_ration | Integer | — | Energy per ration |
| daily_caloric_target | Integer | — | Target daily intake |
| rations_planned / rations_distributed | Integer | — | Plan vs actual |

**Indexes:** `(plan_id, allocation_date)`, `(population_type)`

#### `vulnerable_populations`
Demographic data for priority-based distribution.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Region reference |
| population_type | Enum | NOT NULL | Demographic group |
| total_count | Integer | — | Population size |
| daily_caloric_need | Integer | — | kcal requirement |
| priority_level | Integer | — | Distribution priority (1 = highest) |
| mobility_limited_pct | Float | — | % needing home delivery |

**Indexes:** `(region_id, population_type)`

#### `distribution_records`
Individual distribution transaction records (audit trail).

| Column | Type | Constraints | Description |
|---|---|---|---|
| plan_id | FK → distribution_plans | NOT NULL | Parent plan |
| distribution_point_id | FK → distribution_points | NOT NULL | Distribution site |
| transaction_code | String(50) | UNIQUE | Transaction ID |
| beneficiary_id_hash | String(64) | — | Anonymized beneficiary |
| items_distributed | JSON | — | Items given |
| total_weight_kg | Float | — | Total weight |

---

### 7. Resilience Domain

#### `urban_agriculture_sites`
Urban farming sites contributing to local food production.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Host region |
| site_code | String(50) | UNIQUE, NOT NULL | Identifier |
| site_type | Enum | NOT NULL | ROOFTOP_GARDEN, VERTICAL_FARM, COMMUNITY_GARDEN, HYDROPONICS, AQUAPONICS, GREENHOUSE, VACANT_LOT, PERI_URBAN |
| latitude / longitude | Float | NOT NULL | GPS location |
| total_area_sqm / cultivable_area_sqm | Float | — | Area metrics |
| production_capacity_tonnes_year | Float | — | Max annual output |
| current_production_tonnes_year | Float | — | Actual output |
| households_supplied | Integer | — | Families served |
| status | Enum | default=PROPOSED | PROPOSED → PLANNING → APPROVED → UNDER_CONSTRUCTION → OPERATIONAL → SUSPENDED/CLOSED |

**Indexes:** `(region_id)`, `(site_type)`, `(status)`

#### `crop_diversification_plans`
Plans to diversify regional crop portfolios for resilience.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Target region |
| current_crop_mix / target_crop_mix | JSON | — | Before/after crop proportions |
| current_diversity_index / target_diversity_index | Float (0–1) | — | Simpson's Index |
| vulnerable_crops / recommended_crops | JSON | — | Crop analysis |
| investment_required_usd | Float | — | Cost estimate |

**Indexes:** `(region_id)`, `(status)`

#### `resilience_recommendations`
AI-generated resilience improvement recommendations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Target region |
| category | String(100) | NOT NULL | Recommendation domain |
| title | String(255) | NOT NULL | Recommendation headline |
| priority | Integer | — | Urgency ranking |
| impact_score / feasibility_score | Float (0–1) | — | Assessment scores |
| estimated_cost_usd / expected_benefit_usd | Float | — | Financial analysis |
| confidence_score | Float | — | Model confidence |

**Indexes:** `(region_id)`, `(category)`, `(priority)`

#### `land_conversion_opportunities`
Identified sites for agricultural land conversion.

| Column | Type | Constraints | Description |
|---|---|---|---|
| region_id | FK → regions | NOT NULL | Host region |
| latitude / longitude | Float | NOT NULL | GPS location |
| current_use | String(100) | — | Current land use |
| area_sqm | Float | — | Available area |
| soil_quality | String(20) | — | Soil assessment |
| recommended_use | String(100) | — | Proposed use |
| production_potential_tonnes_year | Float | — | Expected yield |
| feasibility_score | Float (0–1) | — | Viability rating |

**Indexes:** `(region_id)`, `(current_use)`

---

## API Structure

**Base URL:** `http://localhost:8023/api/v1`
**Auth:** None (development) — designed for OAuth2/JWT in production
**Format:** JSON request/response, Pydantic-validated
**Pagination:** `?page=1&page_size=20` on list endpoints

### System Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | API info and documentation links |
| GET | `/health` | Health check (status, version, environment) |
| GET | `/integration/module1` | Module 1 (Early Warning) integration status |
| GET | `/integration/module2` | Module 2 (Supply Chain) integration status |

---

### 1. Agricultural Production — `/api/v1/agricultural`

| Method | Path | Description |
|---|---|---|
| POST | `/regions` | Create a geographic region |
| GET | `/regions` | List regions (filter: `country`, `is_active`) |
| GET | `/regions/{region_id}` | Get region details |
| PATCH | `/regions/{region_id}` | Update region data |
| POST | `/crops` | Create a crop definition |
| GET | `/crops` | List crops (filter: `crop_type`, `is_active`) |
| GET | `/crops/{crop_id}` | Get crop details |
| POST | `/production` | Record production data |
| GET | `/production/{region_id}` | Get production records (filter: `crop_id`, `year`, `season`) |
| GET | `/production/{region_id}/summary` | Aggregate production summary for a year |
| POST | `/forecasts` | Manually create a harvest forecast |
| GET | `/forecasts` | List forecasts (filter: `region_id`, `crop_id`, date range) |
| **POST** | **`/forecasts/generate/{region_id}/{crop_id}`** | **AI-generated yield forecast** (query: `horizon_days`) |
| POST | `/weather` | Record weather observation |
| GET | `/weather/{region_id}` | Get recent weather (query: `days_back`) |
| GET | `/weather/{region_id}/summary` | Weather summary for date range |
| POST | `/crop-health` | Record satellite crop health data |
| GET | `/crop-health/{region_id}` | Get crop health history (query: `days_back`) |
| GET | `/crop-health/{region_id}/analysis` | **AI-based crop health analysis** |

---

### 2. Food Inventory — `/api/v1/inventory`

| Method | Path | Description |
|---|---|---|
| POST | `/categories` | Create a food category |
| GET | `/categories` | List food categories |
| GET | `/categories/{category_id}` | Get category details |
| POST | `/` | Record inventory snapshot |
| GET | `/region/{region_id}` | Get current inventory (filter: `category_id`) |
| GET | `/region/{region_id}/summary` | Inventory summary with stock status |
| PATCH | `/{inventory_id}` | Update inventory record |
| POST | `/warehouse-stocks` | Record warehouse stock level |
| GET | `/warehouse-stocks/{center_id}` | Get stocks for a distribution center |
| PATCH | `/warehouse-stocks/{stock_id}` | Update warehouse stock |
| POST | `/consumption` | Record consumption pattern data |
| GET | `/consumption/{region_id}` | Get consumption patterns (filter: `category_id`, `period_type`) |
| GET | `/consumption/{region_id}/anomalies` | **Detect consumption anomalies** |

---

### 3. Distribution Network — `/api/v1/distribution`

| Method | Path | Description |
|---|---|---|
| POST | `/corridors` | Create a transportation corridor |
| GET | `/corridors` | List corridors (filter: `corridor_type`, `region_id`) |
| GET | `/corridors/{corridor_id}` | Get corridor details |
| PATCH | `/corridors/{corridor_id}` | Update corridor |
| POST | `/centers` | Create a distribution center |
| GET | `/centers` | List centers (filter: `region_id`, `operational_status`) |
| GET | `/centers/{center_id}` | Get center details |
| PATCH | `/centers/{center_id}` | Update center |
| GET | `/centers/nearby` | **Find centers by GPS proximity** (query: `lat`, `lon`, `radius_km`) |
| POST | `/routes` | Create a transport route |
| GET | `/routes` | List routes (filter: `origin`, `destination`, `corridor_id`, `cold_chain`) |
| GET | `/routes/{route_id}` | Get route details |
| **POST** | **`/routes/optimize`** | **AI-optimized route selection** (body: origin, destination, cargo, constraints) |
| POST | `/disruptions` | Report a disruption |
| GET | `/disruptions` | List active disruptions (filter: `region_id`, `type`, `severity`) |
| GET | `/disruptions/{disruption_id}` | Get disruption details |
| POST | `/disruptions/{disruption_id}/resolve` | Resolve a disruption |
| GET | `/disruptions/summary` | Active disruption summary |
| POST | `/cold-chain` | Create cold chain facility |
| GET | `/cold-chain` | List cold chain facilities |
| GET | `/cold-chain/capacity` | Cold chain capacity summary |
| GET | `/status` | **Overall network health status** |

---

### 4. Dependency Analysis — `/api/v1/dependency`

| Method | Path | Description |
|---|---|---|
| POST | `/profiles` | Create regional dependency profile |
| GET | `/profiles` | List profiles (filter: `risk_level`, `min_risk_score`) |
| GET | `/profiles/{region_id}` | Get comprehensive dependency profile |
| PATCH | `/profiles/{region_id}` | Update profile |
| POST | `/import-sources` | Create import source record |
| GET | `/import-sources` | List sources (filter: `dependency_id`, `country`, `food_type`) |
| PATCH | `/import-sources/{source_id}` | Update source |
| POST | `/imports` | Record a food import shipment |
| GET | `/imports` | List imports (filter: `region_id`, `country`, `food_type`, date range) |
| GET | `/imports/{region_id}/summary` | Import volume summary for date range |
| POST | `/assessments` | Create vulnerability assessment |
| GET | `/assessments` | List assessments (filter: `region_id`, `min_score`) |
| **GET** | **`/risk-analysis/{region_id}`** | **AI-powered comprehensive risk analysis** |
| **POST** | **`/simulate-disruption`** | **Disruption scenario simulation** (body: `region_id`, `source_country`, `disruption_pct`) |

---

### 5. Shortage Alerts — `/api/v1/alerts`

| Method | Path | Description |
|---|---|---|
| POST | `/` | Create a shortage alert |
| GET | `/` | List alerts (filter: `region_id`, `type`, `level`, `status`) |
| GET | `/critical` | Get all critical active alerts |
| GET | `/dashboard` | **Alert dashboard** (counts, trends, critical highlights) |
| GET | `/{alert_id}` | Get alert details |
| PATCH | `/{alert_id}` | Update alert |
| POST | `/{alert_id}/acknowledge` | Acknowledge an alert |
| POST | `/{alert_id}/escalate` | Escalate to higher authority |
| POST | `/{alert_id}/resolve` | Mark alert resolved |
| GET | `/{alert_id}/history` | Alert audit trail |
| **GET** | **`/predictions/shortages`** | **AI-predicted shortage detection** across all regions |
| **POST** | **`/predictions/auto-generate`** | **Auto-generate alerts from AI predictions** |
| **GET** | **`/predictions/risk-assessment/{region_id}`** | **Comprehensive shortage risk assessment** |
| POST | `/subscriptions` | Subscribe to alerts |
| GET | `/subscriptions` | List subscriptions |

---

### 6. Distribution Plans — `/api/v1/distribution-plans`

| Method | Path | Description |
|---|---|---|
| POST | `/` | Create a distribution plan |
| GET | `/` | List plans (filter: `region_id`, `status`) |
| GET | `/{plan_id}` | Get plan details |
| PATCH | `/{plan_id}` | Update plan |
| POST | `/{plan_id}/approve` | Approve a plan |
| POST | `/{plan_id}/activate` | Activate a plan |
| GET | `/{plan_id}/analytics` | Plan performance analytics |
| POST | `/points` | Create a distribution point |
| GET | `/{plan_id}/points` | List points for a plan |
| **POST** | **`/optimize-points`** | **AI-optimized distribution point placement** |
| POST | `/allocations` | Create ration allocation |
| **POST** | **`/{plan_id}/calculate-rations`** | **AI-calculated optimal rations** by population group |
| POST | `/vulnerable-populations` | Register vulnerable population |
| GET | `/vulnerable-populations/{region_id}` | List vulnerable populations |
| GET | `/vulnerable-populations/{region_id}/counts` | Population counts by type |
| POST | `/records` | Record a distribution transaction |
| GET | `/coverage/{region_id}` | **Coverage analysis** for a region |

---

### 7. Resilience Planning — `/api/v1/resilience`

| Method | Path | Description |
|---|---|---|
| POST | `/urban-agriculture` | Create urban agriculture site |
| GET | `/urban-agriculture` | List sites (filter: `region_id`, `type`, `status`) |
| GET | `/urban-agriculture/{site_id}` | Get site details |
| PATCH | `/urban-agriculture/{site_id}` | Update site |
| GET | `/urban-agriculture/summary/{region_id}` | Urban agriculture summary |
| POST | `/diversification` | Create crop diversification plan |
| GET | `/diversification` | List diversification plans |
| GET | `/diversification/{plan_id}` | Get plan details |
| **POST** | **`/diversification/generate/{region_id}`** | **AI-generated diversification recommendations** |
| POST | `/recommendations` | Create resilience recommendation |
| GET | `/recommendations` | List recommendations (filter: `region_id`, `category`, `status`) |
| **POST** | **`/recommendations/generate/{region_id}`** | **AI-generated resilience recommendations** |
| POST | `/land-conversion` | Create land conversion opportunity |
| GET | `/land-conversion` | List conversion opportunities |
| **GET** | **`/assessment/{region_id}`** | **Comprehensive resilience assessment** (SWOT + scoring) |
| GET | `/summary/{region_id}` | Regional resilience summary |

---

## Response Conventions

**Pagination** (list endpoints):
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

**Error responses:**
```json
{
  "error": "Resource not found",
  "status_code": 404,
  "path": "/api/v1/alerts/999"
}
```

**AI-powered endpoints** (bolded in tables above) run ML models or statistical algorithms server-side and return predictions, scores, or optimization results alongside confidence metrics.

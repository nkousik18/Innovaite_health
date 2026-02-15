# SENTINEL-HEALTH: AI & ML Solution Architecture

## Overview

This document describes the artificial intelligence and machine learning techniques used across the SENTINEL-HEALTH food security platform. The system combines **statistical forecasting**, **rule-based risk classification**, **geospatial analysis**, **optimization algorithms**, and **anomaly detection** to predict and manage food crises during pandemic scenarios.

---

## 1. Agricultural Yield Forecasting

**Service:** `agricultural_service.py`

### Technique: Linear Trend Regression + Environmental Adjustment

- **Algorithm:** `numpy.polyfit()` (degree-1 polynomial) on historical yield data to extract a linear production trend.
- **Environmental Multipliers:** The raw forecast is adjusted by two multiplicative factors:
  - **Weather Factor** — Reduces the prediction under drought (0.7x), flood (0.8x), or heatwave (0.85x) conditions.
  - **Crop Health Factor** — Uses **NDVI** (Normalized Difference Vegetation Index) from satellite imagery. Healthy vegetation (NDVI > 0.6) applies a 1.0x multiplier; stressed vegetation (NDVI < 0.3) drops to 0.7x.
- **Confidence Scoring:** Based on the number of historical data points — 5+ years yields high confidence; fewer years reduce it.

### Why This Approach

Linear regression is interpretable, fast, and works well with limited agricultural datasets. The environmental multipliers incorporate domain expertise (agronomists' knowledge) as explicit adjustment factors rather than requiring labeled training data for weather-crop interactions.

---

## 2. Predictive Shortage Detection

**Service:** `shortage_service.py`

### Technique: Multi-Factor Risk Scoring + Threshold Classification

- **Days-of-Supply Calculation:** `current_inventory / daily_consumption_rate` gives a projected date when stocks run out.
- **Alert Tier Classification:**
  - **Critical (Red):** < 7 days of supply
  - **Imminent (Orange):** < 15 days of supply
  - **Warning (Yellow):** < 30 days of supply
- **Risk Factor Analysis:** The system scans for compounding risk factors:
  - Harvest forecast deviation > -20%
  - Active distribution corridor disruptions
  - Consumption anomalies (e.g., panic buying spikes)
  - Weather or labor risks flagged by upstream services
- **Confidence Scoring:** Starts at a 0.7 base and adjusts for data freshness (recent data adds +0.1, stale data subtracts -0.1) and consumption rate data availability (+0.1). Bounded to [0.3, 0.95].

### Why This Approach

Threshold-based alerting is standard in humanitarian logistics (WFP, FAO) and ensures **explainability** — decision-makers need to know *why* an alert fired, not just that a model predicted it. The multi-factor risk analysis captures supply-side, demand-side, and logistics risks simultaneously.

---

## 3. Distribution Point Optimization

**Service:** `optimization_service.py`

### Technique: K-Means-Inspired Centroid Placement + Greedy Allocation

- **Point Placement:** A simplified k-means approach distributes `n` food distribution points in a circular pattern around the region center, using trigonometric spacing. Each point is assigned a coverage population proportional to its geographic proximity.
- **Coverage Analysis:** Population coverage is measured as `served_population / total_population`. Areas > 10 km from any distribution point are flagged as underserved.
- **Ration Optimization:** A **greedy algorithm** allocates food sequentially by priority:
  1. Vulnerable populations (elderly, children, immunocompromised) — priority weight 1.0
  2. Healthcare workers — priority weight 1.0
  3. Essential workers — priority weight 0.8
  4. General population — priority weight 0.7
- Each ration is composed to meet a daily caloric target (2000 kcal adult, 1500 kcal child, 2500 kcal healthcare worker) using template-based food-type compositions.
- **Efficiency Score:** `(food_utilization_ratio + coverage_score) / 2`

### Why This Approach

Full k-means or facility-location solvers (e.g., Google OR-Tools) are available as optional dependencies but the simplified approach runs without heavy optimization libraries. The greedy priority-based allocation mirrors real humanitarian distribution protocols used by agencies like the WFP.

---

## 4. Regional Food Dependency & Risk Analysis

**Service:** `dependency_service.py`

### Technique: Composite Risk Scoring (0–100) + Scenario Simulation

- **Risk Score Components (max 100 points):**

  | Factor | Max Points | Logic |
  |---|---|---|
  | Import dependency | 30 | `min(30, import_pct * 0.5)` |
  | Reserve days | 30 | Tiered: <7d → 30, <15d → 25, <30d → 15, <45d → 5 |
  | Source diversity | 20 | 1 source → 20, 2 → 15, 3–4 → 10 |
  | Cold storage gap | 10 | Based on capacity deficit |
  | Population at risk | 10 | Based on vulnerable population share |

- **Weighted Political/Logistics Risk:** For each import source, political and logistics risk are weighted by that source's share of total imports: `sum(risk_i * share_i) / total_share`.
- **Disruption Simulation:** Three scenario types are modeled:
  - Primary source disruption (e.g., border closure)
  - Port disruption
  - Regional instability
  - Each scenario outputs probability, impact in tonnes, and impact in days-of-supply.

### Why This Approach

Composite scoring with transparent weights allows policymakers to see exactly which factors drive risk. Scenario simulation enables "what-if" planning without requiring probabilistic ML models, which would need large historical disruption datasets that rarely exist for food security.

---

## 5. Agricultural Resilience Assessment

**Service:** `resilience_service.py`

### Technique: Simpson's Diversity Index + Weighted Composite Scoring

- **Crop Diversity:** Simpson's Diversity Index: `D = 1 - Σ(p_i²)` where `p_i` is the proportion of each crop. Higher D means more diversified and resilient agriculture.
- **Resilience Sub-Scores (4 dimensions):**
  - **Production:** Weighted by arable land utilization, irrigation coverage, urban agriculture presence, and climate risk.
  - **Distribution:** Penalizes single-source dependency and port reliance; rewards multi-source imports.
  - **Storage:** Tiered scoring based on strategic reserve days (>90d → high, <14d → critical).
  - **Economic:** Penalizes high import dependency (>50%) and aid dependency (>30%).
- **Overall Score:** Mean of the four sub-scores.
- **Automated SWOT Analysis:** Threshold-based extraction of strengths (e.g., production resilience > 0.6), weaknesses, opportunities, and threats.
- **Recommendation Engine:** Rule-based, generating prioritized action items (e.g., "Increase irrigation coverage" if < 50%, "Build 30-day strategic reserves" if < 30 days).

### Why This Approach

Simpson's Index is a well-established ecological diversity metric adapted for crop portfolio analysis. The composite scoring framework makes resilience assessments actionable and comparable across regions.

---

## 6. Route Optimization & Disruption Assessment

**Service:** `distribution_service.py`

### Technique: Haversine Distance + Multi-Factor Route Scoring + Graph Search

- **Geospatial Distance:** Haversine formula calculates great-circle distance between GPS coordinates for finding nearby distribution centers and estimating transport times.
- **Route Scoring:** Each candidate route is scored (0–100) based on:
  - Transit time (penalty: `-2 per hour`)
  - Cost (penalty: `-cost/100`)
  - Capacity sufficiency (penalty: `-30` if insufficient)
  - Primary route bonus (`+10`), cold chain capability (`+15`)
  - Operational status (penalty: `-25` if degraded)
- **Multi-Hop Routing:** A simplified graph search finds indirect routes through intermediate regions (max 2 hops) when direct corridors are disrupted.
- **Disruption Mapping:** Active disruptions are classified by severity (Low → delayed, Medium → impaired, High → restricted, Critical → blocked).

### Why This Approach

The Haversine formula is the standard for geographic distance calculations. The scoring heuristic is fast and transparent — critical for real-time logistics decisions during crises where sub-second response times matter.

---

## Technology Stack

| Category | Libraries | Purpose |
|---|---|---|
| Core ML | `scikit-learn`, `numpy`, `scipy` | Statistical analysis, regression, clustering |
| Gradient Boosting | `xgboost` | Available for advanced prediction models |
| Optimization | `pulp` | Linear programming for resource allocation |
| Geospatial | `shapely` | Geometric calculations and spatial analysis |
| Data Processing | `pandas` | Tabular data manipulation and aggregation |
| Time Series | `prophet` (optional) | Advanced time-series forecasting |
| Deep Learning | `tensorflow` (optional) | Neural network models for complex pattern recognition |

---

## Design Principles

1. **Explainability over accuracy** — Every prediction and alert can be traced to specific input factors. Decision-makers in food crises need to understand *why*, not just *what*.
2. **Graceful degradation** — The system works with minimal data (rule-based fallbacks) and improves as more data becomes available (ML models).
3. **Domain-aligned thresholds** — Alert levels (7/15/30 days) and priority classes match established humanitarian logistics standards (WFP, FAO).
4. **Modularity** — Each service is independently deployable and testable. ML models can be swapped without changing the API contract.

# SENTINEL-HEALTH Module 3: Food Security & Dependency Management

## Overview

This module provides comprehensive food security monitoring and crisis management capabilities for the SENTINEL-HEALTH platform. It combines predictive analytics, logistics optimization, and epidemiological awareness to prevent food security crises during pandemic situations.

## Features

### 1. Agricultural Production Monitoring
- Crop production tracking and historical analysis
- AI-powered harvest yield forecasting
- Weather data integration and impact assessment
- Crop health monitoring via satellite imagery (NDVI)

### 2. Distribution Network Analysis
- Transportation corridor management
- Distribution center operations tracking
- Route optimization with disruption awareness
- Cold chain capacity monitoring

### 3. Food Inventory Management
- Real-time inventory level tracking
- Days-of-supply calculations
- Warehouse stock management
- Consumption pattern analysis with anomaly detection

### 4. Regional Food Dependency Analysis
- Import dependency profiling
- Source reliability assessment
- Vulnerability assessments
- Disruption scenario simulation

### 5. Predictive Shortage Alerting
- Multi-level alert system (Warning/Imminent/Critical)
- AI-based shortage prediction (14-30 days advance warning)
- Alert lifecycle management
- Notification subscriptions

### 6. Distribution Optimization
- Crisis distribution planning
- Optimal point placement
- Priority-based ration allocation
- Vulnerable population targeting

### 7. Agricultural Resilience Planning
- Urban agriculture site management
- Crop diversification recommendations
- Land conversion opportunity identification
- Long-term resilience assessments

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 7+

### Installation

```bash
# Navigate to module directory
cd backend/module3

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
python main.py
```

### API Documentation

Once running, access:
- Swagger UI: http://localhost:8003/docs
- ReDoc: http://localhost:8003/redoc
- OpenAPI JSON: http://localhost:8003/openapi.json

## API Endpoints

### Agricultural Production
- `POST /api/v1/agricultural/regions` - Create region
- `GET /api/v1/agricultural/production/{region_id}` - Get production data
- `POST /api/v1/agricultural/forecasts/generate/{region_id}/{crop_id}` - Generate forecast

### Distribution Network
- `GET /api/v1/distribution/status` - Network status
- `POST /api/v1/distribution/routes/optimize` - Route optimization
- `POST /api/v1/distribution/disruptions` - Report disruption

### Food Inventory
- `POST /api/v1/inventory/` - Record inventory
- `GET /api/v1/inventory/region/{region_id}/summary` - Inventory summary

### Dependency Analysis
- `GET /api/v1/dependency/profiles/{region_id}` - Dependency profile
- `GET /api/v1/dependency/risk-analysis/{region_id}` - Risk analysis
- `POST /api/v1/dependency/simulate-disruption` - Scenario simulation

### Shortage Alerts
- `GET /api/v1/alerts/dashboard` - Alert dashboard
- `GET /api/v1/alerts/predictions/shortages` - Detect shortages
- `POST /api/v1/alerts/predictions/auto-generate` - Auto-generate alerts

### Distribution Plans
- `POST /api/v1/distribution-plans/` - Create plan
- `POST /api/v1/distribution-plans/optimize-points` - Optimize distribution points
- `POST /api/v1/distribution-plans/{plan_id}/calculate-rations` - Calculate rations

### Resilience
- `GET /api/v1/resilience/assessment/{region_id}` - Resilience assessment
- `POST /api/v1/resilience/recommendations/generate/{region_id}` - Generate recommendations

## Alert Levels

| Level | Days of Supply | Color | Action |
|-------|---------------|-------|--------|
| Warning | < 30 days | Yellow | Notify agencies, activate contingency |
| Imminent | < 15 days | Orange | Emergency procurement, ration planning |
| Critical | < 7 days | Red | Emergency airlifts, military coordination |

## Architecture

```
module3/
├── api/                    # API routes
│   ├── agricultural.py
│   ├── distribution.py
│   ├── inventory.py
│   ├── dependency.py
│   ├── alerts.py
│   ├── distribution_plans.py
│   └── resilience.py
├── models/                 # SQLAlchemy models
│   ├── agricultural.py
│   ├── distribution.py
│   ├── inventory.py
│   ├── dependency.py
│   ├── alerts.py
│   ├── distribution_plan.py
│   └── resilience.py
├── schemas/                # Pydantic schemas
├── services/               # Business logic
│   ├── agricultural_service.py
│   ├── distribution_service.py
│   ├── dependency_service.py
│   ├── shortage_service.py
│   ├── optimization_service.py
│   └── resilience_service.py
├── config.py              # Configuration
├── main.py                # Application entry point
└── requirements.txt       # Dependencies
```

## Integration with Other Modules

- **Module 1 (Early Warning Detection)**: Receives outbreak alerts to anticipate food supply disruptions
- **Module 2 (Supply Chain Optimization)**: Coordinates medical and food supply logistics

## License

Copyright 2024 SENTINEL-HEALTH Team. All rights reserved.

# SENTINEL-HEALTH: Project Structure & Setup Guide

## Project Overview

SENTINEL-HEALTH is a pandemic-aware food security platform that monitors agricultural production, predicts food shortages, optimizes crisis distribution, and assesses regional resilience. Built with **FastAPI**, **PostgreSQL**, **Redis**, and **scikit-learn/XGBoost** on the backend.

---

## Directory Structure

```
Innovaite_health/
├── backend/          # Server-side application code
├── frontend/         # Client-side UI (planned)
├── database/         # Database migrations and seed data
├── ml/               # Standalone ML model training and evaluation
├── docs/             # Project documentation
├── scripts/          # DevOps, data ingestion, and utility scripts
├── tests/            # Integration and end-to-end test suites
└── deployment/       # Docker, CI/CD, and infrastructure configs
```

### `backend/`

Contains all API modules. Currently houses **Module 3 (Food Security & Dependency Management)**.

| Sub-folder | Purpose |
|---|---|
| `backend/module3/api/` | FastAPI route handlers — one file per domain (agricultural, distribution, inventory, dependency, alerts, distribution_plans, resilience). |
| `backend/module3/models/` | SQLAlchemy ORM models mapping to PostgreSQL tables (regions, crops, corridors, inventories, alerts, distribution plans, resilience sites). |
| `backend/module3/schemas/` | Pydantic request/response schemas for API validation and serialization. |
| `backend/module3/services/` | Core business logic and AI/ML algorithms (forecasting, optimization, risk scoring, shortage prediction). |
| `backend/module3/config.py` | Application settings loaded from environment variables via `pydantic-settings`. |
| `backend/module3/main.py` | FastAPI app entry point — lifespan management, middleware, exception handlers, health checks. |

### `frontend/`

Reserved for the dashboard UI (React/Next.js planned). Will consume the backend REST API to display maps, alert dashboards, distribution plans, and resilience reports.

### `database/`

Houses database migration scripts (Alembic) and seed/fixture data for development and testing.

### `ml/`

Standalone machine learning experimentation — model training notebooks, evaluation scripts, and serialized model artifacts. Production inference runs inside `backend/module3/services/`.

### `docs/`

Project documentation including this file, API references, and the AI/ML solution document.

### `scripts/`

Utility and automation scripts: data ingestion pipelines, database setup helpers, deployment automation, and cron job definitions.

### `tests/`

Test suites (pytest) for unit, integration, and end-to-end testing of the backend API and services.

### `deployment/`

Infrastructure-as-code and deployment configurations: Dockerfiles, docker-compose, Kubernetes manifests, and CI/CD pipeline definitions.

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis 7+

### Quick Start

```bash
# 1. Clone and navigate
cd backend/module3

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your database URL, Redis URL, and API keys

# 5. Initialize database
alembic upgrade head

# 6. Start the server
python main.py
```

### Key Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/sentinel_food_security` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/3` | Redis cache URL |
| `API_PORT` | `8023` | Server port |
| `WEATHER_API_KEY` | — | OpenWeatherMap API key (optional) |
| `SATELLITE_API_KEY` | — | Sentinel Hub API key for NDVI data (optional) |

### API Documentation

Once running, visit:

- **Swagger UI**: `http://localhost:8023/docs`
- **ReDoc**: `http://localhost:8023/redoc`

### Integration Points

| Module | Port | Role |
|---|---|---|
| Module 1 | 8001 | Early Warning Detection — sends outbreak alerts that trigger food disruption assessments |
| Module 2 | 8002 | Supply Chain Optimization — coordinates medical and food logistics |
| Module 3 | 8023 | Food Security & Dependency Management (this module) |

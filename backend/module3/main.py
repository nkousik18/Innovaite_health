"""
SENTINEL-HEALTH Module 3: Food Security & Dependency Management

Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from config import get_settings
from models.base import init_db, engine
from api import api_router

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting SENTINEL-HEALTH Module 3: Food Security")
    logger.info(f"Environment: {settings.environment}")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
        logger.warning("API will start but database operations will fail until DB is configured")

    yield

    # Shutdown
    logger.info("Shutting down SENTINEL-HEALTH Module 3")
    try:
        await engine.dispose()
    except Exception:
        pass


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## SENTINEL-HEALTH Module 3: Food Security & Dependency Management

    This module provides comprehensive food security monitoring and management capabilities:

    ### Features

    * **Agricultural Production Monitoring** - Track crop production, harvest forecasts, weather impacts
    * **Distribution Network Analysis** - Manage transportation corridors, distribution centers, routes
    * **Food Inventory Management** - Monitor regional food stocks and consumption patterns
    * **Dependency Analysis** - Assess regional food dependencies and import risks
    * **Shortage Alerting** - Predictive shortage detection with multi-level alerts
    * **Distribution Optimization** - Optimize food distribution during crises
    * **Agricultural Resilience** - Long-term food security planning and recommendations

    ### Alert Levels

    * **Warning (Yellow)** - Pre-shortage warning (30 days supply)
    * **Imminent (Orange)** - Shortage imminent (15 days supply)
    * **Critical (Red)** - Critical shortage (7 days supply)
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else None,
            "path": str(request.url.path)
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat()
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "description": "Food Security & Dependency Management Module",
        "documentation": "/docs",
        "health_check": "/health",
        "api_prefix": settings.api_prefix
    }


# Include API router
app.include_router(api_router, prefix=settings.api_prefix)


# Module integration endpoints
@app.get("/integration/module1", tags=["Integration"])
async def get_module1_status() -> Dict[str, Any]:
    """Get status from Module 1 (Early Warning Detection)."""
    # In production, this would call the Module 1 API
    return {
        "module": "Module 1 - Early Warning Detection",
        "status": "integration_placeholder",
        "url": settings.module1_url
    }


@app.get("/integration/module2", tags=["Integration"])
async def get_module2_status() -> Dict[str, Any]:
    """Get status from Module 2 (Supply Chain Optimization)."""
    # In production, this would call the Module 2 API
    return {
        "module": "Module 2 - Supply Chain Optimization",
        "status": "integration_placeholder",
        "url": settings.module2_url
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )

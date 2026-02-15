"""
Fire Disaster API Router

Single endpoint that runs the full automated response pipeline.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from .schemas import FireDisasterRequest, FireDisasterResponse
from .service import FireDisasterService

router = APIRouter()


@router.post(
    "/simulate",
    response_model=FireDisasterResponse,
    summary="Run fire disaster simulation pipeline",
    description=(
        "Given a fire location (lat/lon), runs the full 8-step automated "
        "response pipeline: weather check, flag zones, create disruptions, "
        "displace population, recalculate supply, generate alerts, reroute, "
        "and optimise distribution."
    ),
)
async def simulate_fire_disaster(
    request: FireDisasterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = FireDisasterService(db)
    try:
        result = await service.run_pipeline(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

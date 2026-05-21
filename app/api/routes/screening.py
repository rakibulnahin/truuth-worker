from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_screening_service
from app.schemas.screening import ScreeningRunRequest
from app.services.screening_service import ScreeningService

router = APIRouter(prefix="/screening", tags=["screening"])


@router.post("/runs")
async def run_screening(
    request: ScreeningRunRequest,
    service: ScreeningService = Depends(get_screening_service),
):
    return await service.run_screening(request)


@router.get("/runs/{run_id}")
async def get_screening_run(
    run_id: str,
    service: ScreeningService = Depends(get_screening_service),
):
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Screening run not found")
    return run

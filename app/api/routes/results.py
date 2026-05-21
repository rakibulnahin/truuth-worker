from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_screening_service
from app.schemas.screening import ReviewActionRequest
from app.services.screening_service import ScreeningService

router = APIRouter(tags=["results"])


@router.get("/results/{run_id}")
async def get_results(
    run_id: str,
    service: ScreeningService = Depends(get_screening_service),
):
    results = await service.get_results(run_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results found for run")
    return results


@router.get("/dashboard/runs/{run_id}")
async def get_dashboard_run(
    run_id: str,
    service: ScreeningService = Depends(get_screening_service),
):
    dashboard = await service.get_dashboard_run(run_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Screening run not found")
    return dashboard


@router.post("/results/{result_id}/review")
async def review_result(
    result_id: str,
    request: ReviewActionRequest,
    service: ScreeningService = Depends(get_screening_service),
):
    result = await service.review_result(result_id, request)
    if not result:
        raise HTTPException(status_code=404, detail="Screening result not found")
    return result

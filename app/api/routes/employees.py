from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_candidate_service
from app.schemas.candidates import EmployeeCreate
from app.services.candidate_service import CandidateService

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("")
async def create_employee(
    request: EmployeeCreate,
    service: CandidateService = Depends(get_candidate_service),
):
    return await service.create_employee(request)


@router.get("")
async def list_employees(service: CandidateService = Depends(get_candidate_service)):
    return await service.list_employees()


@router.get("/{employee_id}")
async def get_employee(
    employee_id: str,
    service: CandidateService = Depends(get_candidate_service),
):
    employee = await service.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

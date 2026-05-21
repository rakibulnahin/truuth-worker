from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_candidate_service
from app.schemas.candidates import CandidateCreate, EmployeeDocument, ResumeUploadMockRequest
from app.services.candidate_service import CandidateService

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("")
async def create_candidate(
    request: CandidateCreate,
    service: CandidateService = Depends(get_candidate_service),
):
    return await service.create_candidate(request)


@router.post("/mock-resume-upload")
async def mock_resume_upload(
    request: ResumeUploadMockRequest,
    service: CandidateService = Depends(get_candidate_service),
):
    return await service.mock_resume_upload(request)


@router.get("")
async def list_candidates(service: CandidateService = Depends(get_candidate_service)):
    return await service.list_candidates()


@router.get("/{candidate_id}")
async def get_candidate(
    candidate_id: str,
    service: CandidateService = Depends(get_candidate_service),
):
    candidate = await service.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.post("/{candidate_id}/promote", response_model=EmployeeDocument)
async def promote_candidate(
    candidate_id: str,
    department: str | None = None,
    role: str | None = None,
    service: CandidateService = Depends(get_candidate_service),
):
    employee = await service.promote_candidate(candidate_id, department=department, role=role)
    if not employee:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return employee

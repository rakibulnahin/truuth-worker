from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_payload_service
from app.schemas.payloads import PayloadBuildRequest
from app.services.payload_service import PayloadService

router = APIRouter(prefix="/payloads", tags=["payloads"])


@router.post("")
async def build_payload(
    request: PayloadBuildRequest,
    service: PayloadService = Depends(get_payload_service),
):
    return await service.build_payload(request)


@router.get("/{payload_run_id}")
async def get_payload(
    payload_run_id: str,
    service: PayloadService = Depends(get_payload_service),
):
    payload = await service.get_payload(payload_run_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Payload run not found")
    return payload


@router.get("/{payload_run_id}/export")
async def export_payload(
    payload_run_id: str,
    service: PayloadService = Depends(get_payload_service),
):
    payload = await service.get_payload(payload_run_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Payload run not found")
    return {
        "payload_run_id": payload.payload_run.id,
        "entries": [
            {
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "identity": entry.identity,
            }
            for entry in payload.entries
        ],
    }

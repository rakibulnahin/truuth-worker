from fastapi import APIRouter, Depends, Request

from app.api.dependencies import (
    get_audit_service,
    get_candidate_service,
    get_store,
    get_task_service,
    get_webhook_service,
)
from app.repositories.store import RepositoryStore
from app.schemas.common import ExecutionState, MessageResponse
from app.schemas.ops import ScheduleCreate, ScheduleDocument
from app.services.audit_service import AuditService
from app.services.candidate_service import CandidateService
from app.services.task_service import TaskService
from app.services.webhook_service import WebhookService

router = APIRouter(tags=["operations"])


@router.post("/seed")
async def seed_demo_data(service: CandidateService = Depends(get_candidate_service)):
    candidates = await service.seed_demo_data()
    return {"candidate_count": len(candidates), "candidates": candidates}


@router.post("/demo/reset")
async def reset_demo_data(
    reseed: bool = True,
    store: RepositoryStore = Depends(get_store),
    service: CandidateService = Depends(get_candidate_service),
):
    deleted_counts = await store.delete_all()
    candidates = await service.seed_demo_data() if reseed else []
    return {
        "message": "Demo data reset",
        "deleted_counts": deleted_counts,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


@router.get("/vendors")
async def list_vendors():
    return {
        "vendors": [
            {"name": "mock_adverse_media", "screening_type": "adverse_media", "mode": "mock"},
            {"name": "mock_pep_sanctions", "screening_type": "pep_sanctions", "mode": "mock"},
        ]
    }


@router.get("/vendors/executions")
async def list_vendor_executions(store: RepositoryStore = Depends(get_store)):
    return await store.vendor_executions.list()


@router.post("/schedules")
async def create_schedule(
    request: ScheduleCreate,
    store: RepositoryStore = Depends(get_store),
):
    return await store.schedules.create(ScheduleDocument(**request.model_dump()))


@router.get("/schedules")
async def list_schedules(store: RepositoryStore = Depends(get_store)):
    return await store.schedules.list()


@router.post("/schedules/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: str,
    store: RepositoryStore = Depends(get_store),
    tasks: TaskService = Depends(get_task_service),
):
    schedule = await store.schedules.get(schedule_id)
    if not schedule:
        return MessageResponse(message=f"Schedule {schedule_id} not found")
    task = await tasks.enqueue(
        task_type="scheduled_screening",
        execution_id=schedule_id,
        idempotency_key=f"schedule:{schedule_id}",
        payload_snapshot={
            "schedule_id": schedule_id,
            "include_all_employees": schedule.include_all_employees,
            "target_employee_ids": schedule.target_employee_ids,
        },
    )
    return {"message": "Schedule trigger queued for demo", "task": task}


@router.get("/tasks")
async def list_tasks(tasks: TaskService = Depends(get_task_service)):
    return await tasks.list_tasks()


@router.get("/tasks/retryable")
async def list_retryable_tasks(tasks: TaskService = Depends(get_task_service)):
    return await tasks.list_retryable()


@router.post("/tasks/{task_id}/execute")
async def execute_task_placeholder(task_id: str, tasks: TaskService = Depends(get_task_service)):
    task = await tasks.execute_placeholder(task_id)
    if not task:
        return MessageResponse(message=f"Task {task_id} not found")
    return task


@router.post("/tasks/{task_id}/fail")
async def fail_task(task_id: str, reason: str, tasks: TaskService = Depends(get_task_service)):
    task = await tasks.mark_failed(task_id, reason)
    if not task:
        return MessageResponse(message=f"Task {task_id} not found")
    return task


@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str, tasks: TaskService = Depends(get_task_service)):
    task = await tasks.retry(task_id)
    if not task:
        return MessageResponse(message=f"Task {task_id} not found")
    return task


@router.post("/webhooks/vendors/{vendor_name}")
async def receive_vendor_webhook(
    vendor_name: str,
    request: Request,
    webhooks: WebhookService = Depends(get_webhook_service),
):
    payload = await request.json()
    return await webhooks.receive_vendor_event(vendor_name, payload)


@router.get("/audit/logs")
async def list_audit_logs(store: RepositoryStore = Depends(get_store)):
    return await store.audit_logs.list()


@router.get("/errors")
async def list_error_logs(store: RepositoryStore = Depends(get_store)):
    return await store.error_logs.list()


@router.post("/audit/demo-error")
async def create_demo_error(audit: AuditService = Depends(get_audit_service)):
    try:
        raise ValueError("Demo error boundary event")
    except Exception as exc:
        return await audit.log_error(
            component="demo",
            operation="demo_error",
            error=exc,
            error_code="DEMO_001",
        )

from fastapi import Request

from app.repositories.store import RepositoryStore
from app.services.audit_service import AuditService
from app.services.candidate_service import CandidateService
from app.services.payload_service import PayloadService
from app.services.screening_service import ScreeningService
from app.services.task_service import TaskService
from app.services.webhook_service import WebhookService


def get_store(request: Request) -> RepositoryStore:
    return request.app.state.store


def get_candidate_service(request: Request) -> CandidateService:
    return CandidateService(get_store(request))


def get_payload_service(request: Request) -> PayloadService:
    return PayloadService(get_store(request))


def get_screening_service(request: Request) -> ScreeningService:
    return ScreeningService(get_store(request))


def get_audit_service(request: Request) -> AuditService:
    return AuditService(get_store(request))


def get_task_service(request: Request) -> TaskService:
    return TaskService(get_store(request))


def get_webhook_service(request: Request) -> WebhookService:
    return WebhookService(get_store(request))

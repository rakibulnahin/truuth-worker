from dataclasses import dataclass

from app.core.config import Settings
from app.repositories.base import InMemoryRepository, Repository
from app.repositories.mongo import MongoRepository
from app.repositories.postgres import PostgresDocumentRepository, create_postgres_engine
from app.schemas.audit import AuditLogDocument, ErrorLogDocument
from app.schemas.candidates import CandidateDocument, EmployeeDocument
from app.schemas.ops import ScheduleDocument, WebhookEventDocument
from app.schemas.payloads import PayloadEntryDocument, PayloadRunDocument
from app.schemas.screening import (
    NormalizedScreeningResult,
    ScreeningRunDocument,
    VendorExecutionDocument,
)
from app.schemas.tasks import TaskRunDocument


@dataclass
class RepositoryStore:
    candidates: Repository[CandidateDocument]
    employees: Repository[EmployeeDocument]
    payload_runs: Repository[PayloadRunDocument]
    payload_entries: Repository[PayloadEntryDocument]
    screening_runs: Repository[ScreeningRunDocument]
    screening_results: Repository[NormalizedScreeningResult]
    vendor_executions: Repository[VendorExecutionDocument]
    task_runs: Repository[TaskRunDocument]
    schedules: Repository[ScheduleDocument]
    webhook_events: Repository[WebhookEventDocument]
    audit_logs: Repository[AuditLogDocument]
    error_logs: Repository[ErrorLogDocument]

    async def delete_all(self) -> dict[str, int]:
        deleted_counts: dict[str, int] = {}
        for name, repository in self.__dict__.items():
            deleted_counts[name] = await repository.delete_all()
        return deleted_counts


async def build_repository_store(settings: Settings) -> RepositoryStore:
    if settings.repository_backend == "postgres" and settings.database_url:
        engine = create_postgres_engine(settings.database_url)
        repositories = RepositoryStore(
            candidates=PostgresDocumentRepository(engine, "candidates", CandidateDocument),
            employees=PostgresDocumentRepository(engine, "employees", EmployeeDocument),
            payload_runs=PostgresDocumentRepository(engine, "payload_runs", PayloadRunDocument),
            payload_entries=PostgresDocumentRepository(engine, "payload_entries", PayloadEntryDocument),
            screening_runs=PostgresDocumentRepository(engine, "screening_runs", ScreeningRunDocument),
            screening_results=PostgresDocumentRepository(engine, "screening_results", NormalizedScreeningResult),
            vendor_executions=PostgresDocumentRepository(engine, "vendor_executions", VendorExecutionDocument),
            task_runs=PostgresDocumentRepository(engine, "task_runs", TaskRunDocument),
            schedules=PostgresDocumentRepository(engine, "schedules", ScheduleDocument),
            webhook_events=PostgresDocumentRepository(engine, "webhook_events", WebhookEventDocument),
            audit_logs=PostgresDocumentRepository(engine, "audit_logs", AuditLogDocument),
            error_logs=PostgresDocumentRepository(engine, "error_logs", ErrorLogDocument),
        )
        for repository in repositories.__dict__.values():
            await repository.ensure_table()
        return repositories

    if settings.repository_backend == "mongo" and settings.mongodb_uri:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_database]
        return RepositoryStore(
            candidates=MongoRepository(db.candidates, CandidateDocument),
            employees=MongoRepository(db.employees, EmployeeDocument),
            payload_runs=MongoRepository(db.payload_runs, PayloadRunDocument),
            payload_entries=MongoRepository(db.payload_entries, PayloadEntryDocument),
            screening_runs=MongoRepository(db.screening_runs, ScreeningRunDocument),
            screening_results=MongoRepository(db.screening_results, NormalizedScreeningResult),
            vendor_executions=MongoRepository(db.vendor_executions, VendorExecutionDocument),
            task_runs=MongoRepository(db.task_runs, TaskRunDocument),
            schedules=MongoRepository(db.schedules, ScheduleDocument),
            webhook_events=MongoRepository(db.webhook_events, WebhookEventDocument),
            audit_logs=MongoRepository(db.audit_logs, AuditLogDocument),
            error_logs=MongoRepository(db.error_logs, ErrorLogDocument),
        )

    return RepositoryStore(
        candidates=InMemoryRepository(),
        employees=InMemoryRepository(),
        payload_runs=InMemoryRepository(),
        payload_entries=InMemoryRepository(),
        screening_runs=InMemoryRepository(),
        screening_results=InMemoryRepository(),
        vendor_executions=InMemoryRepository(),
        task_runs=InMemoryRepository(),
        schedules=InMemoryRepository(),
        webhook_events=InMemoryRepository(),
        audit_logs=InMemoryRepository(),
        error_logs=InMemoryRepository(),
    )

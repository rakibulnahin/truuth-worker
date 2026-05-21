from app.core.error_codes import ErrorCodes
from app.repositories.store import RepositoryStore
from app.schemas.common import ExecutionState, new_id
from app.schemas.payloads import (
    PayloadBuildRequest,
    PayloadEntryDocument,
    PayloadExport,
    PayloadRunDocument,
)
from app.services.audit_service import AuditService


class PayloadService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store
        self.audit = AuditService(store)

    async def build_payload(self, request: PayloadBuildRequest) -> PayloadExport:
        batch_id = request.batch_id or new_id()
        chunk_size = max(request.chunk_size, 1)
        run = await self.store.payload_runs.create(
            PayloadRunDocument(
                status=ExecutionState.RUNNING,
                requested_candidate_ids=request.candidate_ids,
                requested_employee_ids=request.employee_ids,
                include_all_employees=request.include_all_employees,
                whitelist_ids=request.whitelist_ids,
                batch_id=batch_id,
                chunk_size=chunk_size,
                metadata={"notes": request.notes},
            )
        )
        await self.audit.log(
            operation="payload_generation_started",
            status="RUNNING",
            execution_id=run.id,
            candidate_ids=request.candidate_ids,
            employee_ids=request.employee_ids,
            batch_id=batch_id,
            chunk_size=chunk_size,
        )

        try:
            entries: list[PayloadEntryDocument] = []
            whitelist = set(request.whitelist_ids)

            def chunk_number(index: int) -> int:
                return (index // chunk_size) + 1

            for candidate_id in request.candidate_ids:
                if candidate_id in whitelist:
                    continue
                candidate = await self.store.candidates.get(candidate_id)
                if candidate:
                    entries.append(
                        await self.store.payload_entries.create(
                            PayloadEntryDocument(
                                payload_run_id=run.id,
                                batch_id=batch_id,
                                chunk_number=chunk_number(len(entries)),
                                entity_type="candidate",
                                entity_id=candidate.id,
                                identity=candidate.identity,
                            )
                        )
                    )

            employees = await self.store.employees.list() if request.include_all_employees else []
            for employee_id in request.employee_ids:
                employee = await self.store.employees.get(employee_id)
                if employee:
                    employees.append(employee)

            seen_employees: set[str] = set()
            for employee in employees:
                if employee.id in whitelist or employee.id in seen_employees:
                    continue
                seen_employees.add(employee.id)
                entries.append(
                    await self.store.payload_entries.create(
                        PayloadEntryDocument(
                            payload_run_id=run.id,
                            batch_id=batch_id,
                            chunk_number=chunk_number(len(entries)),
                            entity_type="employee",
                            entity_id=employee.id,
                            identity=employee.identity,
                        )
                    )
                )

            run = await self.store.payload_runs.update(
                run.id,
                {
                    "status": ExecutionState.COMPLETED,
                    "entry_count": len(entries),
                    "chunk_count": chunk_number(len(entries) - 1) if entries else 0,
                },
            )
            await self.audit.log(
                operation="payload_generation_completed",
                status="COMPLETED",
                execution_id=run.id if run else None,
                entry_count=len(entries),
                chunk_count=chunk_number(len(entries) - 1) if entries else 0,
            )
            return PayloadExport(payload_run=run, entries=entries)  # type: ignore[arg-type]
        except Exception as exc:
            await self.store.payload_runs.update(run.id, {"status": ExecutionState.FAILED})
            await self.audit.log_error(
                component="payload",
                operation="payload_generation",
                error=exc,
                execution_id=run.id,
                error_code=ErrorCodes.PAYLOAD_BUILD_FAILED,
                payload_snapshot=request.model_dump(),
            )
            raise

    async def get_payload(self, payload_run_id: str) -> PayloadExport | None:
        run = await self.store.payload_runs.get(payload_run_id)
        if not run:
            return None
        entries = await self.store.payload_entries.find(
            lambda entry: entry.payload_run_id == payload_run_id
        )
        return PayloadExport(payload_run=run, entries=entries)

from app.core.error_codes import ErrorCodes
from app.adapters.base import VendorAdapter
from app.adapters.mock_adverse_media import MockAdverseMediaAdapter
from app.adapters.mock_pep_sanctions import MockPepSanctionsAdapter
from app.repositories.store import RepositoryStore
from app.schemas.common import ExecutionState, ScreeningType
from app.schemas.payloads import PayloadBuildRequest
from app.schemas.screening import (
    DashboardRunResponse,
    ScreeningRunDocument,
    ScreeningRunRequest,
    ReviewActionRequest,
    VendorExecutionDocument,
)
from app.services.audit_service import AuditService
from app.services.payload_service import PayloadService


class ScreeningService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store
        self.payload_service = PayloadService(store)
        self.audit = AuditService(store)
        self.adapters: list[VendorAdapter] = [
            MockAdverseMediaAdapter(),
            MockPepSanctionsAdapter(),
        ]

    async def run_screening(self, request: ScreeningRunRequest) -> ScreeningRunDocument:
        payload = None
        if request.payload_run_id:
            payload = await self.payload_service.get_payload(request.payload_run_id)
        elif request.build_payload:
            payload = await self.payload_service.build_payload(
                PayloadBuildRequest(
                    candidate_ids=request.candidate_ids,
                    employee_ids=request.employee_ids,
                    include_all_employees=request.include_all_employees,
                )
            )

        if not payload:
            raise ValueError("payload_run_id or build_payload=true is required")

        run = await self.store.screening_runs.create(
            ScreeningRunDocument(
                payload_run_id=payload.payload_run.id,
                batch_id=payload.payload_run.batch_id,
                status=ExecutionState.RUNNING,
                metadata={
                    "payload_entry_count": len(payload.entries),
                    "payload_chunk_count": payload.payload_run.chunk_count,
                },
            )
        )
        await self.audit.log(
            operation="screening_run_started",
            status="RUNNING",
            execution_id=run.id,
            payload_run_id=payload.payload_run.id,
            entry_count=len(payload.entries),
        )

        result_count = 0
        failure_count = 0
        for adapter in self.adapters:
            vendor_execution = await self.store.vendor_executions.create(
                VendorExecutionDocument(
                    run_id=run.id,
                    payload_run_id=payload.payload_run.id,
                    vendor=adapter.vendor_name,
                    screening_type=(
                        ScreeningType.ADVERSE_MEDIA
                        if adapter.vendor_name == "mock_adverse_media"
                        else ScreeningType.PEP_SANCTIONS
                    ),
                    status=ExecutionState.SUBMITTED,
                )
            )
            try:
                external_id = await adapter.submit_payload(payload.entries)
                raw_response = await adapter.poll_results(external_id, payload.entries)
                normalized = await adapter.normalize_results(run.id, raw_response, payload.entries)
                for result in normalized:
                    await self.store.screening_results.create(result)
                    result_count += 1
                await self.store.vendor_executions.update(
                    vendor_execution.id,
                    {
                        "status": ExecutionState.COMPLETED,
                        "external_execution_id": external_id,
                        "raw_response": raw_response,
                    },
                )
                await self.audit.log(
                    operation="vendor_execution_completed",
                    status="COMPLETED",
                    execution_id=run.id,
                    vendor=adapter.vendor_name,
                    result_count=len(normalized),
                )
            except Exception as exc:
                failure_count += 1
                await self.store.vendor_executions.update(
                    vendor_execution.id,
                    {"status": ExecutionState.FAILED},
                )
                await self.audit.log_error(
                    component="vendor",
                    operation=f"{adapter.vendor_name}_execution",
                    error=exc,
                    execution_id=run.id,
                    error_code=ErrorCodes.VENDOR_SUBMISSION_FAILED,
                    payload_snapshot={"payload_run_id": payload.payload_run.id},
                )

        final_state = ExecutionState.PARTIAL_FAILURE if failure_count and result_count else (
            ExecutionState.FAILED if failure_count else ExecutionState.COMPLETED
        )
        updated = await self.store.screening_runs.update(
            run.id,
            {
                "status": final_state,
                "result_count": result_count,
                "metadata": {
                    **run.metadata,
                    "vendor_failure_count": failure_count,
                },
            },
        )
        await self.audit.log(
            operation="screening_run_finished",
            status=final_state.value,
            execution_id=run.id,
            result_count=result_count,
            vendor_failure_count=failure_count,
        )
        return updated  # type: ignore[return-value]

    async def get_run(self, run_id: str) -> ScreeningRunDocument | None:
        return await self.store.screening_runs.get(run_id)

    async def get_results(self, run_id: str):
        return await self.store.screening_results.find(lambda result: result.run_id == run_id)

    async def review_result(
        self,
        result_id: str,
        request: ReviewActionRequest,
    ):
        result = await self.store.screening_results.get(result_id)
        if not result:
            return None

        review = {
            "action": request.action,
            "reviewer": request.reviewer,
            "note": request.note,
        }
        updated = await self.store.screening_results.update(
            result_id,
            {
                "metadata": {
                    **result.metadata,
                    "review": review,
                }
            },
        )
        await self.audit.log(
            operation="screening_result_reviewed",
            status="COMPLETED",
            execution_id=result.run_id,
            entity_type=result.entity_type,
            entity_id=result.entity_id,
            result_id=result_id,
            review=review,
        )
        return updated

    async def get_dashboard_run(self, run_id: str) -> DashboardRunResponse | None:
        run = await self.get_run(run_id)
        if not run:
            return None
        results = await self.get_results(run_id)
        alerts = len([result for result in results if result.match_status in {"ALERT", "MATCH"}])
        high = len([result for result in results if result.risk_level == "high"])
        return DashboardRunResponse(
            run=run,
            summary={
                "total_results": len(results),
                "alerts_or_matches": alerts,
                "high_risk": high,
                "clear": len(results) - alerts,
            },
            results=results,
        )

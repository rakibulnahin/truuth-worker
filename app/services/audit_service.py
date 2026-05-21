from app.core.error_codes import ErrorCodes, error_detail
from app.core.request_context import current_correlation_id
from app.repositories.store import RepositoryStore
from app.schemas.audit import AuditLogDocument, ErrorLogDocument


class AuditService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store

    async def log(self, operation: str, status: str, **details) -> AuditLogDocument:
        log = AuditLogDocument(operation=operation, status=status, details=details)
        return await self.store.audit_logs.create(log)

    async def log_error(
        self,
        component: str,
        operation: str,
        error: Exception,
        execution_id: str | None = None,
        error_code: ErrorCodes | str = ErrorCodes.WORKFLOW_FAILED,
        payload_snapshot: dict | None = None,
    ) -> ErrorLogDocument:
        detail = error_detail(error_code)
        error_code_value = error_code.value if isinstance(error_code, ErrorCodes) else error_code
        error_log = ErrorLogDocument(
            execution_id=execution_id,
            correlation_id=current_correlation_id(),
            component=component,
            operation=operation,
            error_code=error_code_value,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=detail["severity"],
            payload_snapshot={
                "category": detail["category"],
                "standard_message": detail["message"],
                **(payload_snapshot or {}),
            },
        )
        await self.log(
            operation=operation,
            status="FAILED",
            error_code=error_code_value,
            category=detail["category"],
            message=str(error),
        )
        return await self.store.error_logs.create(error_log)

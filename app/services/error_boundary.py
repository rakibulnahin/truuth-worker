from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.error_codes import ErrorCodes
from app.services.audit_service import AuditService

T = TypeVar("T")


class WorkflowException(Exception):
    pass


class ErrorBoundary:
    def __init__(self, audit_service: AuditService) -> None:
        self.audit_service = audit_service

    async def execute(
        self,
        operation_name: str,
        handler: Callable[..., Awaitable[T]],
        *args,
        execution_id: str | None = None,
        component: str = "workflow",
        error_code: ErrorCodes | str = ErrorCodes.WORKFLOW_FAILED,
        **kwargs,
    ) -> T:
        try:
            return await handler(*args, **kwargs)
        except Exception as exc:
            await self.audit_service.log_error(
                component=component,
                operation=operation_name,
                error=exc,
                execution_id=execution_id,
                error_code=error_code,
            )
            raise WorkflowException(str(exc)) from exc

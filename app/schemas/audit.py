from typing import Any

from pydantic import Field

from app.schemas.common import BaseDocument


class AuditLogDocument(BaseDocument):
    execution_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    operation: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorLogDocument(BaseDocument):
    execution_id: str | None = None
    correlation_id: str | None = None
    component: str
    operation: str
    error_code: str
    error_type: str
    error_message: str
    severity: str = "ERROR"
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)
    resolved: bool = False

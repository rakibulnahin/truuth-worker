from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import BaseDocument, ExecutionState


class TaskRunDocument(BaseDocument):
    task_type: str
    status: ExecutionState = ExecutionState.PENDING
    execution_id: str | None = None
    idempotency_key: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: datetime | None = None
    last_failure_reason: str | None = None
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)

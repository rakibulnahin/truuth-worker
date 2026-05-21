from pydantic import BaseModel, Field

from app.schemas.common import BaseDocument, ExecutionState


class ScheduleDocument(BaseDocument):
    name: str
    frequency: str
    cron_expression: str | None = None
    status: str = "ACTIVE"
    include_all_employees: bool = True
    target_employee_ids: list[str] = Field(default_factory=list)


class ScheduleCreate(BaseModel):
    name: str
    frequency: str = "monthly"
    cron_expression: str | None = None
    include_all_employees: bool = True
    target_employee_ids: list[str] = Field(default_factory=list)


class WebhookEventDocument(BaseDocument):
    vendor: str
    event_type: str
    status: ExecutionState = ExecutionState.PENDING
    payload: dict = Field(default_factory=dict)

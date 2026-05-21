from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import BaseDocument, ExecutionState, RiskLevel, ScreeningType


class Finding(BaseModel):
    source: str
    title: str
    url: str | None = None
    matched_name: str | None = None
    match_score: float = 0
    severity: str | None = None
    details: str | None = None


class NormalizedScreeningResult(BaseDocument):
    run_id: str
    payload_entry_id: str
    entity_id: str
    entity_type: str
    vendor: str
    screening_type: ScreeningType
    match_status: str
    risk_score: float
    risk_level: RiskLevel
    findings: list[Finding] = Field(default_factory=list)
    completed_at: str | None = None


class VendorExecutionDocument(BaseDocument):
    run_id: str
    payload_run_id: str
    vendor: str
    screening_type: ScreeningType
    status: ExecutionState = ExecutionState.PENDING
    external_execution_id: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class ScreeningRunRequest(BaseModel):
    payload_run_id: str | None = None
    build_payload: bool = False
    candidate_ids: list[str] = Field(default_factory=list)
    employee_ids: list[str] = Field(default_factory=list)
    include_all_employees: bool = False


class ScreeningRunDocument(BaseDocument):
    payload_run_id: str
    batch_id: str | None = None
    status: ExecutionState = ExecutionState.PENDING
    result_count: int = 0


class DashboardRunResponse(BaseModel):
    run: ScreeningRunDocument
    summary: dict[str, int | float]
    results: list[NormalizedScreeningResult]


class ReviewActionRequest(BaseModel):
    action: str
    reviewer: str = "demo-analyst"
    note: str | None = None

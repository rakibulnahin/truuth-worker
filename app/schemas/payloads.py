from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.candidates import NormalizedIdentity
from app.schemas.common import BaseDocument, ExecutionState


class PayloadBuildRequest(BaseModel):
    include_all_employees: bool = False
    candidate_ids: list[str] = Field(default_factory=list)
    employee_ids: list[str] = Field(default_factory=list)
    whitelist_ids: list[str] = Field(default_factory=list)
    batch_id: str | None = None
    chunk_size: int = 500
    notes: str | None = None


class PayloadEntryDocument(BaseDocument):
    payload_run_id: str
    batch_id: str | None = None
    chunk_number: int = 1
    entity_type: Literal["candidate", "employee"]
    entity_id: str
    identity: NormalizedIdentity
    status: ExecutionState = ExecutionState.PENDING


class PayloadRunDocument(BaseDocument):
    status: ExecutionState = ExecutionState.PENDING
    requested_candidate_ids: list[str] = Field(default_factory=list)
    requested_employee_ids: list[str] = Field(default_factory=list)
    include_all_employees: bool = False
    whitelist_ids: list[str] = Field(default_factory=list)
    batch_id: str | None = None
    chunk_size: int = 500
    chunk_count: int = 0
    entry_count: int = 0


class PayloadExport(BaseModel):
    payload_run: PayloadRunDocument
    entries: list[PayloadEntryDocument]

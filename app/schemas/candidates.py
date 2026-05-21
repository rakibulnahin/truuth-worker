from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import BaseDocument, EntityStatus


class NormalizedIdentity(BaseModel):
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: str | None = None
    nationality: str | None = None
    aliases: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    identifiers: dict[str, Any] = Field(default_factory=dict)


class CandidateCreate(BaseModel):
    identity: NormalizedIdentity
    source: str = "manual"


class CandidateDocument(BaseDocument):
    identity: NormalizedIdentity
    source: str = "manual"
    status: EntityStatus = EntityStatus.ACTIVE
    promoted_employee_id: str | None = None


class EmployeeCreate(BaseModel):
    identity: NormalizedIdentity
    candidate_id: str | None = None
    department: str | None = None
    role: str | None = None


class EmployeeDocument(BaseDocument):
    identity: NormalizedIdentity
    candidate_id: str | None = None
    department: str | None = None
    role: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE


class ResumeUploadMockRequest(BaseModel):
    file_name: str
    extracted_full_name: str
    email: str | None = None
    phone: str | None = None

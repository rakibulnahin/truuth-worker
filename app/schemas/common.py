from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EntityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    FAILED = "FAILED"


class ExecutionState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class ScreeningType(str, Enum):
    ADVERSE_MEDIA = "adverse_media"
    PEP_SANCTIONS = "pep_sanctions"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BaseDocument(BaseModel):
    id: str = Field(default_factory=new_id)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    message: str

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

CASE_TYPES = {"RFQ", "INQUIRY", "PROJECT", "SERVICE", "OTHER"}
CASE_STATUSES = {"OPEN", "IN_PROGRESS", "WAITING_CUSTOMER", "QUOTED", "WON", "LOST", "CLOSED"}
PRIORITIES = {"LOW", "NORMAL", "HIGH", "CRITICAL"}

class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    case_type: str = Field(default="INQUIRY", max_length=50)
    description: str | None = None
    status: str = Field(default="OPEN", max_length=50)
    priority: str = Field(default="NORMAL", max_length=20)
    assigned_to: int | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()

    @field_validator("case_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in CASE_TYPES:
            raise ValueError(f"case_type must be one of: {', '.join(sorted(CASE_TYPES))}")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in CASE_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(CASE_STATUSES))}")
        return value

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in PRIORITIES:
            raise ValueError(f"priority must be one of: {', '.join(sorted(PRIORITIES))}")
        return value

class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    case_type: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: int | None = None

class CaseOut(BaseModel):
    id: int
    customer_id: int
    case_number: str
    title: str
    case_type: str
    description: str | None
    status: str
    priority: str
    assigned_to: int | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

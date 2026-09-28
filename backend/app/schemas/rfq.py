from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RFQ_STATUSES = {"NEW","UNDER_REVIEW","WAITING_CLARIFICATION","SUPPLIER_INQUIRY","PRICING","QUOTED","WON","LOST","CLOSED"}
CONDITIONS = {"NEW","USED_SERVICEABLE","REFURBISHED","ANY","OTHER"}
CONDITION_SOURCES = {"CUSTOMER","DEFAULT_RULE","USER"}
VERIFICATION_STATUSES = {"PENDING","CONFIRMED","REJECTED","NEEDS_CLARIFICATION"}

class RFQCreate(BaseModel):
    customer_rfq_number: str | None = None
    title: str | None = Field(default=None, max_length=255)
    request_date: date | None = None
    required_date: date | None = None
    site_id: int | None = None
    currency: str | None = Field(default=None, max_length=10)
    delivery_location: str | None = Field(default=None, max_length=255)
    incoterm: str | None = Field(default=None, max_length=20)
    source_rfq_url: str | None = Field(default=None, max_length=1000)
    notes: str | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.request_date and self.required_date and self.required_date < self.request_date:
            raise ValueError("required_date cannot be before request_date")
        return self

class RFQUpdate(RFQCreate):
    status: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, value):
        value = value.strip().upper()
        if value not in RFQ_STATUSES: raise ValueError("Invalid RFQ status")
        return value

class RFQOut(BaseModel):
    id: int; case_id: int; customer_id: int; site_id: int | None
    customer_rfq_number: str | None; title: str | None
    request_date: date | None; required_date: date | None
    currency: str | None; delivery_location: str | None; incoterm: str | None
    status: str; source_rfq_url: str | None; notes: str | None
    created_at: datetime; updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RFQLineCreate(BaseModel):
    line_number: int = Field(gt=0)
    description_original: str | None = None
    description_normalized: str | None = None
    part_id: int | None = None; equipment_id: int | None = None; equipment_model_id: int | None = None
    manufacturer: str | None = Field(default=None, max_length=255)
    customer_part_number: str | None = Field(default=None, max_length=255)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=50)
    condition_required: str | None = None
    condition_source: str | None = None
    documents_required: str | None = None
    technical_requirements: str | None = None
    delivery_requirement: str | None = None
    status: str = "NEW"
    verification_status: str = "PENDING"
    notes: str | None = None

    @field_validator("condition_required")
    @classmethod
    def condition(cls, value):
        if value is None: return value
        value=value.strip().upper()
        if value not in CONDITIONS: raise ValueError("Invalid condition_required")
        return value
    @field_validator("condition_source")
    @classmethod
    def validate_condition_source(cls, value):
        if value is None: return value
        value=value.strip().upper()
        if value not in CONDITION_SOURCES: raise ValueError("Invalid condition_source")
        return value
    @field_validator("verification_status")
    @classmethod
    def verification(cls, value):
        value=value.strip().upper()
        if value not in VERIFICATION_STATUSES: raise ValueError("Invalid verification_status")
        return value

class RFQLineUpdate(RFQLineCreate):
    line_number: int | None = Field(default=None, gt=0)

class RFQLineOut(BaseModel):
    id: int; rfq_id: int; line_number: int
    description_original: str | None; description_normalized: str | None
    part_id: int | None; equipment_id: int | None; equipment_model_id: int | None
    manufacturer: str | None; customer_part_number: str | None; quantity: Decimal | None; unit: str | None
    condition_required: str | None; condition_source: str | None
    documents_required: str | None; technical_requirements: str | None; delivery_requirement: str | None
    status: str; verification_status: str; notes: str | None
    created_at: datetime; updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CandidateField(BaseModel):
    field_name: str
    value: str | None
    confidence: float = Field(ge=0, le=1)
    source: str
    needs_confirmation: bool = True
    original_value: str | None = None
    translated_value: str | None = None
    normalized_value: str | None = None
    translation_status: str = "NOT_REQUIRED"
    translation_confidence: float = Field(default=1.0, ge=0, le=1)
    translation_source: str | None = None

class CandidateLine(BaseModel):
    line_number: int
    fields: list[CandidateField]

class RFQIntakePreview(BaseModel):
    source_file_name: str
    extraction_method: str
    fields: list[CandidateField]
    lines: list[CandidateLine]
    warnings: list[str] = []

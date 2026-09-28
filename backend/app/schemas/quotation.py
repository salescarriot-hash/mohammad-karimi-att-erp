from datetime import date
from pydantic import BaseModel, Field

class QuotationCreate(BaseModel):
    rfq_id: int
    quotation_number: str = Field(min_length=1, max_length=100)
    quotation_date: date | None = None
    valid_until: date | None = None
    currency: str | None = None
    incoterm: str | None = None
    delivery_location: str | None = None
    payment_terms: str | None = None
    delivery_time: str | None = None
    warranty: str | None = None
    origin: str | None = None
    price_basis: str | None = "PRICING_ENGINE"
    customer_notes: str | None = None
    internal_notes: str | None = None
    include_line_ids: list[int] | None = None

class QuotationUpdate(BaseModel):
    status: str | None = Field(default=None, pattern=r"^(DRAFT|UNDER_REVIEW|PENDING_APPROVAL|APPROVED|SENT|CUSTOMER_ACCEPTED|CUSTOMER_REJECTED|EXPIRED|CANCELLED)$")
    valid_until: date | None = None
    incoterm: str | None = None
    delivery_location: str | None = None
    payment_terms: str | None = None
    delivery_time: str | None = None
    warranty: str | None = None
    origin: str | None = None
    customer_notes: str | None = None
    internal_notes: str | None = None

class QuotationLineUpdate(BaseModel):
    manual_selling_price: float | None = Field(default=None, ge=0)
    override_reason: str | None = None
    delivery_time: str | None = None
    warranty: str | None = None
    notes: str | None = None

class QuotationLineReprice(BaseModel):
    basis_type: str = Field(pattern=r"^(TARGET_PURCHASE_PRICE|ACTUAL_PURCHASE_PRICE)$")
    purchase_price: float = Field(gt=0)
    purchase_currency: str = Field(min_length=1, max_length=10)
    exchange_rate: float = Field(gt=0)
    exchange_rate_date: date | None = None
    target_currency: str = Field(min_length=1, max_length=10)
    freight_cost: float = Field(default=0, ge=0)
    insurance_cost: float = Field(default=0, ge=0)
    customs_cost: float = Field(default=0, ge=0)
    clearance_cost: float = Field(default=0, ge=0)
    local_delivery_cost: float = Field(default=0, ge=0)
    financial_cost: float = Field(default=0, ge=0)
    other_cost: float = Field(default=0, ge=0)
    margin_type: str = Field(default="MARKUP", pattern=r"^(MARKUP|GROSS_MARGIN)$")
    margin_value: float = Field(default=0.05, ge=0)
    rounding_method: str = Field(default="NONE", pattern=r"^(NONE|NEAREST_100|NEAREST_1000|NEAREST_10000|NEAREST_100000)$")
    rounding_value: float | None = Field(default=None, gt=0)
    incoterm: str | None = None
    notes: str | None = None

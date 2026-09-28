from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field

class SupplierCreate(BaseModel):
    name: str
    name_en: str | None = None
    supplier_type: str | None = None
    country: str | None = None
    city: str | None = None
    website: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    address: str | None = None
    notes: str | None = None
    verification_status: str = "PENDING"

class SupplierOut(SupplierCreate):
    id: int
    status: str
    class Config:
        from_attributes = True

class SupplierSearchOut(BaseModel):
    supplier_id: int
    supplier_name: str
    supplier_type: str | None
    country: str | None
    match_score: int
    match_reasons: list[str]
    verification_status: str

class SupplierQuoteCreate(BaseModel):
    supplier_id: int
    rfq_id: int
    quote_number: str | None = None
    quote_date: date | None = None
    valid_until: date | None = None
    currency: str | None = None
    incoterm: str | None = None
    delivery_time: str | None = None
    payment_terms: str | None = None
    origin: str | None = None
    warranty: str | None = None
    source_file: str | None = None
    source_url: str | None = None
    notes: str | None = None

class SupplierQuoteLineCreate(BaseModel):
    rfq_line_id: int
    supplier_part_number: str | None = None
    description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    condition: str | None = None
    brand: str | None = None
    manufacturer: str | None = None
    lead_time: str | None = None
    availability: str | None = None
    technical_compliance: str = "NOT_REVIEWED"
    deviation: str | None = None
    notes: str | None = None

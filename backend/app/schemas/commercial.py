from datetime import date
from pydantic import BaseModel, Field

class MarketPriceCreate(BaseModel):
    part_id: int | None = None
    supplier_id: int | None = None
    source_type: str
    source_name: str | None = None
    source_url: str | None = None
    condition: str | None = None
    brand: str | None = None
    part_number: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float = Field(gt=0)
    currency: str | None = None
    incoterm: str | None = None
    lead_time: str | None = None
    availability: str | None = None
    observed_date: date | None = None
    confidence: str = "MEDIUM"
    verification_status: str = "PENDING"
    notes: str | None = None

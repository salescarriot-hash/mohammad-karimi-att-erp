from datetime import datetime
from pydantic import BaseModel

class SupplierOutreachCreate(BaseModel):
    supplier_id: int
    rfq_id: int
    sent_at: datetime | None = None
    response_at: datetime | None = None
    status: str = "SENT"
    channel: str | None = None
    requested_line_count: int | None = None
    responded_line_count: int | None = None
    notes: str | None = None

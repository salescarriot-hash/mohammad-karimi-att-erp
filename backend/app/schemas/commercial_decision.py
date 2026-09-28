from pydantic import BaseModel, Field

class CommercialDecisionCreate(BaseModel):
    selected_supplier_quote_line_id: int | None = None
    decision_status: str = Field(pattern=r"^(PENDING|PROCEED|HOLD|REJECT)$")
    target_purchase_price: float | None = Field(default=None, gt=0)
    target_currency: str | None = None
    technical_status: str | None = None
    commercial_notes: str | None = None
    decided_by: int | None = None

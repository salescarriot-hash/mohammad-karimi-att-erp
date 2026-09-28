from datetime import date
from pydantic import BaseModel, Field

class PricingCalculate(BaseModel):
    basis_type: str = Field(default="TARGET_PURCHASE_PRICE", pattern=r"^(TARGET_PURCHASE_PRICE|ACTUAL_PURCHASE_PRICE|MANUAL)$")
    purchase_price: float = Field(gt=0)
    purchase_currency: str = Field(min_length=1, max_length=10)
    exchange_rate: float = Field(default=1, gt=0, description="purchase currency to target currency")
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
    created_by: int | None = None

class PricingSettingUpdate(BaseModel):
    default_margin_type: str = Field(pattern=r"^(MARKUP|GROSS_MARGIN)$")
    default_margin_value: float = Field(ge=0)
    minimum_margin_type: str | None = Field(default=None, pattern=r"^(MARKUP|GROSS_MARGIN)$")
    minimum_margin_value: float | None = Field(default=None, ge=0)
    default_currency: str = Field(min_length=1, max_length=10)
    rounding_method: str = Field(pattern=r"^(NONE|NEAREST_100|NEAREST_1000|NEAREST_10000|NEAREST_100000)$")
    rounding_value: float | None = Field(default=None, gt=0)
    default_incoterm: str | None = None

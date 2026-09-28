from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.pricing.intelligence import build_scenarios

router = APIRouter(prefix='/pricing-intelligence', tags=['Pricing Intelligence'])

class ScenarioRequest(BaseModel):
    purchase_price: float = Field(gt=0)
    purchase_currency: str = Field(min_length=1, max_length=10)
    exchange_rate: float = Field(gt=0)
    target_currency: str = Field(min_length=1, max_length=10)
    freight_cost: float = Field(default=0, ge=0)
    insurance_cost: float = Field(default=0, ge=0)
    customs_cost: float = Field(default=0, ge=0)
    clearance_cost: float = Field(default=0, ge=0)
    local_delivery_cost: float = Field(default=0, ge=0)
    financial_cost: float = Field(default=0, ge=0)
    other_cost: float = Field(default=0, ge=0)
    margin_type: str = Field(default='MARKUP', pattern=r'^(MARKUP|GROSS_MARGIN)$')
    margin_values: list[float] = Field(default=[0.05, 0.10, 0.15], min_length=1, max_length=10)
    exchange_rates: list[float] | None = Field(default=None, max_length=10)
    rounding_method: str = Field(default='NONE', pattern=r'^(NONE|NEAREST_100|NEAREST_1000|NEAREST_10000|NEAREST_100000)$')
    rounding_value: float | None = Field(default=None, gt=0)
    incoterm: str | None = None

@router.post('/scenarios')
def scenarios(payload: ScenarioRequest):
    if payload.margin_type == 'GROSS_MARGIN' and any(x >= 1 for x in payload.margin_values):
        raise HTTPException(400, 'GROSS_MARGIN values must be less than 1')
    if payload.exchange_rates and any(x <= 0 for x in payload.exchange_rates):
        raise HTTPException(400, 'Exchange rates must be greater than zero')
    return build_scenarios(payload.model_dump(), payload.margin_values, payload.exchange_rates)

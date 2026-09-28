from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.rfq import RFQLine
from app.models.commercial_decision import CommercialDecision
from app.models.supplier import SupplierQuoteLine
from app.models.pricing import PricingCalculation, PricingSetting
from app.schemas.pricing import PricingCalculate, PricingSettingUpdate
from app.pricing.engine import calculate

router = APIRouter(prefix="/pricing", tags=["Pricing"])

def serialize(x):
    return {c.name: (float(getattr(x,c.name)) if isinstance(getattr(x,c.name), Decimal) else getattr(x,c.name).isoformat() if hasattr(getattr(x,c.name), "isoformat") else getattr(x,c.name)) for c in x.__table__.columns}

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    row = db.scalars(select(PricingSetting).order_by(PricingSetting.id)).first()
    return serialize(row) if row else None

@router.put("/settings")
def update_settings(payload: PricingSettingUpdate, db: Session = Depends(get_db)):
    row = db.scalars(select(PricingSetting).order_by(PricingSetting.id)).first()
    now = datetime.now(timezone.utc)
    data = payload.model_dump()
    if row is None:
        row = PricingSetting(id=1, created_at=now, updated_at=now, **data)
        db.add(row)
    else:
        for k,v in data.items(): setattr(row,k,v)
        row.updated_at = now
    db.commit(); db.refresh(row)
    return serialize(row)

@router.post("/rfq-lines/{line_id}/calculate")
def calculate_price(line_id: int, payload: PricingCalculate, db: Session = Depends(get_db)):
    line = db.get(RFQLine, line_id)
    if not line: raise HTTPException(404, "RFQ line not found")
    try:
        pp, landed, selling, final, increment = calculate(
            payload.purchase_price, payload.exchange_rate,
            [payload.freight_cost, payload.insurance_cost, payload.customs_cost, payload.clearance_cost,
             payload.local_delivery_cost, payload.financial_cost, payload.other_cost],
            payload.margin_type, payload.margin_value, payload.rounding_method, payload.rounding_value)
    except ValueError as e:
        raise HTTPException(400, str(e))
    now = datetime.now(timezone.utc)
    row = PricingCalculation(rfq_line_id=line_id, **payload.model_dump(exclude={"purchase_price","exchange_rate"}),
        purchase_price=payload.purchase_price, exchange_rate=payload.exchange_rate,
        landed_cost=landed, calculated_selling_price=selling, final_selling_price=final,
        rounding_value=increment, created_at=now)
    db.add(row); db.commit(); db.refresh(row)
    result = serialize(row)
    result["purchase_cost_in_target_currency"] = float(pp)
    return result

@router.post("/rfq-lines/{line_id}/from-decision")
def calculate_from_decision(line_id: int, payload: PricingCalculate, db: Session = Depends(get_db)):
    """Create a pricing calculation only from the latest PROCEED commercial decision.

    TARGET_PURCHASE_PRICE uses the approved target from the decision.
    ACTUAL_PURCHASE_PRICE uses the selected supplier quote line price.
    User still supplies exchange rate, logistics costs and margin; nothing is silently guessed.
    """
    line = db.get(RFQLine, line_id)
    if not line:
        raise HTTPException(404, "RFQ line not found")
    decision = db.scalars(
        select(CommercialDecision)
        .where(CommercialDecision.rfq_line_id == line_id)
        .order_by(CommercialDecision.id.desc())
    ).first()
    if not decision or decision.decision_status != "PROCEED":
        raise HTTPException(409, "Pricing requires a latest PROCEED commercial decision")
    selected = None
    purchase_price = payload.purchase_price
    purchase_currency = payload.purchase_currency
    basis = payload.basis_type
    if basis == "TARGET_PURCHASE_PRICE":
        if decision.target_purchase_price is None or not decision.target_currency:
            raise HTTPException(409, "PROCEED decision has no target purchase price/currency")
        purchase_price = float(decision.target_purchase_price)
        purchase_currency = decision.target_currency
    elif basis == "ACTUAL_PURCHASE_PRICE":
        if decision.selected_supplier_quote_line_id is None:
            raise HTTPException(409, "PROCEED decision has no selected supplier quote line")
        selected = db.get(SupplierQuoteLine, decision.selected_supplier_quote_line_id)
        if not selected or selected.rfq_line_id != line_id or selected.unit_price is None:
            raise HTTPException(409, "Selected supplier quote line has no valid unit price")
        purchase_price = float(selected.unit_price)
        from app.models.supplier import SupplierQuote
        quote = db.get(SupplierQuote, selected.supplier_quote_id)
        purchase_currency = quote.currency
        if not purchase_currency:
            raise HTTPException(409, "Selected supplier quote has no currency")
    else:
        raise HTTPException(400, "Pricing from decision supports TARGET_PURCHASE_PRICE or ACTUAL_PURCHASE_PRICE")

    try:
        pp, landed, selling, final, increment = calculate(
            purchase_price, payload.exchange_rate,
            [payload.freight_cost, payload.insurance_cost, payload.customs_cost, payload.clearance_cost,
             payload.local_delivery_cost, payload.financial_cost, payload.other_cost],
            payload.margin_type, payload.margin_value, payload.rounding_method, payload.rounding_value)
    except ValueError as e:
        raise HTTPException(400, str(e))

    target_currency = payload.target_currency
    if not target_currency:
        raise HTTPException(400, "target_currency is required")
    now = datetime.now(timezone.utc)
    row = PricingCalculation(
        rfq_line_id=line_id, commercial_decision_id=decision.id, basis_type=basis,
        purchase_price=purchase_price, purchase_currency=purchase_currency,
        exchange_rate=payload.exchange_rate, exchange_rate_date=payload.exchange_rate_date,
        target_currency=target_currency, freight_cost=payload.freight_cost,
        insurance_cost=payload.insurance_cost, customs_cost=payload.customs_cost,
        clearance_cost=payload.clearance_cost, local_delivery_cost=payload.local_delivery_cost,
        financial_cost=payload.financial_cost, other_cost=payload.other_cost, landed_cost=landed,
        margin_type=payload.margin_type, margin_value=payload.margin_value,
        calculated_selling_price=selling, rounding_method=payload.rounding_method,
        rounding_value=increment, final_selling_price=final,
        incoterm=payload.incoterm, notes=payload.notes, created_by=payload.created_by, created_at=now)
    db.add(row); db.commit(); db.refresh(row)
    result = serialize(row)
    result["commercial_decision_id"] = decision.id
    result["decision_status"] = decision.decision_status
    result["purchase_cost_in_target_currency"] = float(pp)
    return result

@router.get("/rfq-lines/{line_id}/history")
def pricing_history(line_id: int, db: Session = Depends(get_db)):
    if not db.get(RFQLine, line_id): raise HTTPException(404, "RFQ line not found")
    rows = db.scalars(select(PricingCalculation).where(PricingCalculation.rfq_line_id == line_id).order_by(PricingCalculation.id.desc())).all()
    return [serialize(x) for x in rows]

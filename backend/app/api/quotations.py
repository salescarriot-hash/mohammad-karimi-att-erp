from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.quotation import Quotation, QuotationLine
from app.models.rfq import RFQ, RFQLine
from app.models.pricing import PricingCalculation
from app.models.commercial_decision import CommercialDecision
from app.models.customer import Customer
from app.schemas.quotation import QuotationCreate, QuotationUpdate, QuotationLineUpdate, QuotationLineReprice
from app.pricing.engine import calculate

router = APIRouter(prefix="/quotations", tags=["Quotations"])
ROOT = Path(__file__).resolve().parents[3]
GENERATED = ROOT / "storage" / "generated"
GENERATED.mkdir(parents=True, exist_ok=True)

def serialize(obj):
    return {c.name: (float(v) if isinstance(v, Decimal) else v.isoformat() if hasattr(v, "isoformat") else v) for c in obj.__table__.columns for v in [getattr(obj, c.name)]}

def latest_pricing(db, line_id, basis_type=None):
    stmt = select(PricingCalculation).where(PricingCalculation.rfq_line_id == line_id)
    if basis_type:
        stmt = stmt.where(PricingCalculation.basis_type == basis_type)
    return db.scalars(stmt.order_by(PricingCalculation.id.desc())).first()

def apply_pricing_snapshot(line, pricing, target_price=None, actual_price=None):
    line.pricing_calculation_id = pricing.id
    line.target_purchase_price = target_price
    line.actual_purchase_price = actual_price
    line.purchase_currency = pricing.purchase_currency
    line.exchange_rate = pricing.exchange_rate
    line.exchange_rate_date = pricing.exchange_rate_date
    line.freight_cost = pricing.freight_cost
    line.insurance_cost = pricing.insurance_cost
    line.customs_cost = pricing.customs_cost
    line.clearance_cost = pricing.clearance_cost
    line.local_delivery_cost = pricing.local_delivery_cost
    line.financial_cost = pricing.financial_cost
    line.other_cost = pricing.other_cost
    line.landed_cost = pricing.landed_cost
    line.margin_type = pricing.margin_type
    line.margin_value = pricing.margin_value
    line.calculated_selling_price = pricing.calculated_selling_price
    line.manual_selling_price = None
    line.final_selling_price = pricing.final_selling_price
    line.selling_total_price = pricing.final_selling_price * (line.quantity or Decimal("0"))
    line.currency = pricing.target_currency
    line.pricing_status = "CALCULATED"
    line.override_reason = None

def refresh_totals(db, q):
    lines = db.scalars(select(QuotationLine).where(QuotationLine.quotation_id == q.id)).all()
    q.subtotal = sum((x.selling_total_price or Decimal("0")) for x in lines)
    q.grand_total = q.subtotal - (q.discount or Decimal("0")) + (q.additional_cost or Decimal("0"))

@router.post("", status_code=201)
def create_quotation(payload: QuotationCreate, db: Session = Depends(get_db)):
    rfq = db.get(RFQ, payload.rfq_id)
    if not rfq: raise HTTPException(404, "RFQ not found")
    if db.scalars(select(Quotation).where(Quotation.quotation_number == payload.quotation_number)).first():
        raise HTTPException(409, "Quotation number already exists")
    now = datetime.now(timezone.utc)
    q = Quotation(quotation_number=payload.quotation_number, rfq_id=rfq.id, case_id=rfq.case_id, customer_id=rfq.customer_id,
        quotation_date=payload.quotation_date or date.today(), valid_until=payload.valid_until, currency=payload.currency or rfq.currency,
        incoterm=payload.incoterm or rfq.incoterm, delivery_location=payload.delivery_location or rfq.delivery_location,
        payment_terms=payload.payment_terms, delivery_time=payload.delivery_time, warranty=payload.warranty, origin=payload.origin,
        price_basis=payload.price_basis, customer_notes=payload.customer_notes, internal_notes=payload.internal_notes,
        status="DRAFT", subtotal=0, discount=0, additional_cost=0, grand_total=0, created_at=now, updated_at=now)
    db.add(q); db.flush()
    lines = db.scalars(select(RFQLine).where(RFQLine.rfq_id == rfq.id).order_by(RFQLine.line_number)).all()
    if payload.include_line_ids is not None: lines = [x for x in lines if x.id in payload.include_line_ids]
    pricing_rows = [(line, latest_pricing(db, line.id)) for line in lines]
    pricing_rows = [(line, p) for line, p in pricing_rows if p is not None]
    if not pricing_rows:
        raise HTTPException(400, "Quotation has no priced lines")
    # A customer quotation can only be created from an explicit commercial decision.
    for line, p in pricing_rows:
        decision = db.scalars(
            select(CommercialDecision)
            .where(CommercialDecision.rfq_line_id == line.id)
            .order_by(CommercialDecision.id.desc())
        ).first()
        if not decision or decision.decision_status != "PROCEED":
            raise HTTPException(409, f"RFQ line {line.line_number} has no latest PROCEED commercial decision")
        if p.commercial_decision_id != decision.id:
            raise HTTPException(409, f"Pricing for RFQ line {line.line_number} is not linked to its latest PROCEED decision; reprice from Commercial Decision first")
    expected_currency = payload.currency or pricing_rows[0][1].target_currency
    if payload.currency is None:
        q.currency = expected_currency
    mismatches = [line.line_number for line, p in pricing_rows if p.target_currency != expected_currency]
    if mismatches:
        raise HTTPException(400, f"Pricing currency mismatch on RFQ lines: {mismatches}; quotation currency must match pricing target currency")
    for line, p in pricing_rows:
        target = p.purchase_price if p.basis_type == "TARGET_PURCHASE_PRICE" else latest_pricing(db, line.id, "TARGET_PURCHASE_PRICE")
        target_price = target.purchase_price if target else None
        actual_price = p.purchase_price if p.basis_type == "ACTUAL_PURCHASE_PRICE" else None
        decision = db.scalars(
            select(CommercialDecision)
            .where(CommercialDecision.rfq_line_id == line.id)
            .order_by(CommercialDecision.id.desc())
        ).first()
        ql = QuotationLine(quotation_id=q.id, rfq_line_id=line.id, line_number=line.line_number,
            description=line.description_normalized or line.description_original, part_id=line.part_id,
            manufacturer=line.manufacturer, part_number=line.customer_part_number, quantity=line.quantity or Decimal("0"), unit=line.unit,
            condition=line.condition_required, supplier_quote_line_id=decision.selected_supplier_quote_line_id if decision else None,
            target_purchase_price=target_price, actual_purchase_price=actual_price,
            pricing_calculation_id=p.id, purchase_currency=p.purchase_currency, exchange_rate=p.exchange_rate,
            exchange_rate_date=p.exchange_rate_date, freight_cost=p.freight_cost, insurance_cost=p.insurance_cost,
            customs_cost=p.customs_cost, clearance_cost=p.clearance_cost, local_delivery_cost=p.local_delivery_cost,
            financial_cost=p.financial_cost, other_cost=p.other_cost, landed_cost=p.landed_cost,
            margin_type=p.margin_type, margin_value=p.margin_value, calculated_selling_price=p.calculated_selling_price,
            final_selling_price=p.final_selling_price, selling_total_price=p.final_selling_price * (line.quantity or Decimal("0")),
            currency=p.target_currency, pricing_status="CALCULATED", verification_status=line.verification_status,
            technical_compliance="NOT_REVIEWED", created_at=now, updated_at=now)
        db.add(ql)
    db.flush(); refresh_totals(db, q); q.updated_at=now
    db.commit(); db.refresh(q)
    return {**serialize(q), "lines":[serialize(x) for x in db.scalars(select(QuotationLine).where(QuotationLine.quotation_id==q.id).order_by(QuotationLine.line_number)).all()]}

@router.get("")
def list_quotations(rfq_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Quotation).order_by(Quotation.id.desc())
    if rfq_id: stmt = stmt.where(Quotation.rfq_id == rfq_id)
    return [serialize(x) for x in db.scalars(stmt).all()]

@router.get("/{quotation_id}")
def get_quotation(quotation_id: int, db: Session = Depends(get_db)):
    q = db.get(Quotation, quotation_id)
    if not q: raise HTTPException(404, "Quotation not found")
    lines = db.scalars(select(QuotationLine).where(QuotationLine.quotation_id == q.id).order_by(QuotationLine.line_number)).all()
    return {**serialize(q), "lines":[serialize(x) for x in lines]}

@router.patch("/{quotation_id}")
def update_quotation(quotation_id: int, payload: QuotationUpdate, db: Session = Depends(get_db)):
    q = db.get(Quotation, quotation_id)
    if not q: raise HTTPException(404, "Quotation not found")
    if q.status in {"APPROVED", "SENT", "CUSTOMER_ACCEPTED", "CUSTOMER_REJECTED", "CANCELLED"}:
        raise HTTPException(409, "Quotation header is locked after approval/closure")
    for k,v in payload.model_dump(exclude_none=True).items(): setattr(q,k,v)
    q.updated_at=datetime.now(timezone.utc); db.commit(); db.refresh(q); return serialize(q)

@router.patch("/{quotation_id}/lines/{line_id}")
def update_line(quotation_id: int, line_id: int, payload: QuotationLineUpdate, db: Session = Depends(get_db)):
    line = db.get(QuotationLine, line_id)
    if not line or line.quotation_id != quotation_id: raise HTTPException(404, "Quotation line not found")
    q=db.get(Quotation,quotation_id)
    if q.status in {"APPROVED", "SENT", "CUSTOMER_ACCEPTED", "CUSTOMER_REJECTED", "CANCELLED"}:
        raise HTTPException(409, "Quotation line is locked after approval/closure")
    if payload.manual_selling_price is not None:
        if not payload.override_reason: raise HTTPException(400, "override_reason is required for manual selling price")
        line.manual_selling_price=payload.manual_selling_price; line.final_selling_price=payload.manual_selling_price; line.pricing_status="MANUAL_OVERRIDE"
        line.selling_total_price=line.final_selling_price*(line.quantity or Decimal("0")); line.override_reason=payload.override_reason
    for k,v in payload.model_dump(exclude_none=True).items():
        if k != "manual_selling_price": setattr(line,k,v)
    refresh_totals(db,q); q.updated_at=datetime.now(timezone.utc); line.updated_at=q.updated_at
    db.commit(); db.refresh(line); return serialize(line)


@router.post("/{quotation_id}/lines/{line_id}/reprice")
def reprice_line(quotation_id: int, line_id: int, payload: QuotationLineReprice, db: Session = Depends(get_db)):
    q = db.get(Quotation, quotation_id)
    line = db.get(QuotationLine, line_id)
    if not q or not line or line.quotation_id != quotation_id:
        raise HTTPException(404, "Quotation line not found")
    if q.status in {"SENT", "CUSTOMER_ACCEPTED", "CUSTOMER_REJECTED", "CANCELLED"}:
        raise HTTPException(409, "Pricing cannot be changed after quotation is sent/closed")
    rfq_line = db.get(RFQLine, line.rfq_line_id)
    if not rfq_line:
        raise HTTPException(404, "RFQ line not found")
    try:
        _, landed, selling, final, increment = calculate(
            payload.purchase_price, payload.exchange_rate,
            [payload.freight_cost, payload.insurance_cost, payload.customs_cost, payload.clearance_cost,
             payload.local_delivery_cost, payload.financial_cost, payload.other_cost],
            payload.margin_type, payload.margin_value, payload.rounding_method, payload.rounding_value)
    except ValueError as e:
        raise HTTPException(400, str(e))
    now = datetime.now(timezone.utc)
    calc = PricingCalculation(
        rfq_line_id=rfq_line.id, basis_type=payload.basis_type, purchase_price=payload.purchase_price,
        purchase_currency=payload.purchase_currency, exchange_rate=payload.exchange_rate,
        exchange_rate_date=payload.exchange_rate_date, target_currency=payload.target_currency,
        freight_cost=payload.freight_cost, insurance_cost=payload.insurance_cost, customs_cost=payload.customs_cost,
        clearance_cost=payload.clearance_cost, local_delivery_cost=payload.local_delivery_cost,
        financial_cost=payload.financial_cost, other_cost=payload.other_cost, landed_cost=landed,
        margin_type=payload.margin_type, margin_value=payload.margin_value, calculated_selling_price=selling,
        rounding_method=payload.rounding_method, rounding_value=increment, final_selling_price=final,
        incoterm=payload.incoterm or q.incoterm, notes=payload.notes, created_at=now)
    db.add(calc); db.flush()
    target = latest_pricing(db, rfq_line.id, "TARGET_PURCHASE_PRICE")
    target_price = target.purchase_price if target else None
    actual_price = payload.purchase_price if payload.basis_type == "ACTUAL_PURCHASE_PRICE" else None
    if q.currency and q.currency != payload.target_currency:
        raise HTTPException(400, "Quotation currency must match pricing target currency")
    apply_pricing_snapshot(line, calc, target_price=target_price, actual_price=actual_price)
    line.updated_at = now
    q.updated_at = now
    refresh_totals(db, q)
    db.commit(); db.refresh(line)
    return {**serialize(line), "pricing_calculation_id": calc.id}

@router.post("/{quotation_id}/export-docx")
def export_docx(quotation_id: int, db: Session = Depends(get_db)):
    """Legacy export endpoint: render the active official quotation template.

    Customer-facing documents are only generated after quotation approval.
    Internal pricing/cost fields are never exposed by the template engine.
    """
    q = db.get(Quotation, quotation_id)
    if not q:
        raise HTTPException(404, "Quotation not found")
    if q.status not in {"APPROVED", "SENT"}:
        raise HTTPException(409, "Customer quotation can only be exported after approval")

    from app.services.template_engine import render_quotation
    import json

    meta = ROOT / "storage" / "templates" / "quotation_templates.json"
    if not meta.exists():
        raise HTTPException(409, "No quotation template is configured")
    try:
        rows = json.loads(meta.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(500, "Quotation template metadata is invalid")
    row = next((x for x in rows if x.get("active")), None)
    if not row:
        raise HTTPException(409, "No active quotation template is configured")
    template_path = ROOT / row["path"]
    if not template_path.exists():
        raise HTTPException(404, "Active quotation template file is missing")

    customer = db.get(Customer, q.customer_id)
    from app.models.customer import CustomerContact
    contact = db.get(CustomerContact, q.contact_id) if q.contact_id else None
    lines = db.scalars(select(QuotationLine).where(QuotationLine.quotation_id == q.id).order_by(QuotationLine.line_number)).all()
    out = GENERATED / f"{q.quotation_number}-{row['id']}.docx"
    render_quotation(template_path, out, q, lines, customer, contact)
    q.source_template = row["id"]
    db.commit()
    return FileResponse(out, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=out.name)

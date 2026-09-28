from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.commercial_decision import CommercialDecision
from app.models.rfq import RFQLine
from app.models.supplier import SupplierQuoteLine, SupplierQuote, Supplier
from app.schemas.commercial_decision import CommercialDecisionCreate
from app.api.commercial import analyze_rfq_line

router = APIRouter(prefix="/commercial-decisions", tags=["Commercial Decision"])

VALID_STATUSES = {"PENDING", "PROCEED", "HOLD", "REJECT"}
BLOCKING_COMPLIANCE = {"NON_COMPLIANT", "PARTIALLY_COMPLIANT"}


def _num(v):
    return float(v) if v is not None else None


def dump_decision(d):
    return {
        "id": d.id,
        "rfq_line_id": d.rfq_line_id,
        "selected_supplier_quote_line_id": d.selected_supplier_quote_line_id,
        "decision_status": d.decision_status,
        "target_purchase_price": _num(d.target_purchase_price),
        "target_currency": d.target_currency,
        "technical_status": d.technical_status,
        "commercial_notes": d.commercial_notes,
        "decided_by": d.decided_by,
        "decided_at": d.decided_at.isoformat() if d.decided_at else None,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    }


def quote_context(db, line_id):
    stmt = (
        select(SupplierQuoteLine, SupplierQuote, Supplier)
        .join(SupplierQuote, SupplierQuote.id == SupplierQuoteLine.supplier_quote_id)
        .join(Supplier, Supplier.id == SupplierQuote.supplier_id)
        .where(SupplierQuoteLine.rfq_line_id == line_id)
    )
    out = []
    for ql, q, s in db.execute(stmt).all():
        out.append({
            "quote_line_id": ql.id,
            "quote_id": q.id,
            "supplier_id": s.id,
            "supplier_name": s.name,
            "quote_number": q.quote_number,
            "quote_date": q.quote_date.isoformat() if q.quote_date else None,
            "valid_until": q.valid_until.isoformat() if q.valid_until else None,
            "currency": q.currency,
            "incoterm": q.incoterm,
            "payment_terms": q.payment_terms,
            "origin": q.origin,
            "warranty": q.warranty,
            "unit_price": _num(ql.unit_price),
            "total_price": _num(ql.total_price),
            "quantity": _num(ql.quantity),
            "unit": ql.unit,
            "condition": ql.condition,
            "brand": ql.brand,
            "manufacturer": ql.manufacturer,
            "supplier_part_number": ql.supplier_part_number,
            "lead_time": ql.lead_time,
            "availability": ql.availability,
            "technical_compliance": ql.technical_compliance,
            "deviation": ql.deviation,
            "quote_status": q.status,
            "selection_eligible": ql.technical_compliance not in BLOCKING_COMPLIANCE,
        })
    return out


def build_checks(line, quotes, analysis):
    target = analysis.get("target_purchase_price")
    currency = analysis.get("target_currency")
    return {
        "supplier_quote_available": len(quotes) > 0,
        "compliant_quote_available": any(q["selection_eligible"] for q in quotes),
        "target_purchase_price_available": target is not None,
        "target_purchase_price_confidence": analysis.get("data_confidence"),
        "target_currency": currency,
        "requested_condition": line.condition_required or "NEW",
        "technical_review_required_for_non_exact_pn": True,
        "notes": [
            "These are factual readiness checks, not an automatic commercial recommendation.",
            "A PROCEED decision requires an explicitly selected supplier quote line.",
            "Non-compliant and partially compliant quote lines cannot be selected.",
        ],
    }


@router.get("/rfq-lines/{line_id}/review")
def review(line_id: int, db: Session = Depends(get_db)):
    line = db.get(RFQLine, line_id)
    if not line:
        raise HTTPException(404, "RFQ line not found")
    analysis = analyze_rfq_line(line_id, None, db)
    quotes = quote_context(db, line_id)
    decisions = db.scalars(
        select(CommercialDecision)
        .where(CommercialDecision.rfq_line_id == line_id)
        .order_by(CommercialDecision.id.desc())
    ).all()
    return {
        "rfq_line": {
            "id": line.id,
            "rfq_id": line.rfq_id,
            "line_number": line.line_number,
            "description": line.description_original or line.description_normalized,
            "part_id": line.part_id,
            "customer_part_number": line.customer_part_number,
            "manufacturer": line.manufacturer,
            "quantity": _num(line.quantity),
            "unit": line.unit,
            "condition_required": line.condition_required or "NEW",
            "condition_source": line.condition_source,
            "technical_requirements": line.technical_requirements,
            "documents_required": line.documents_required,
            "delivery_requirement": line.delivery_requirement,
            "status": line.status,
            "verification_status": line.verification_status,
        },
        "supplier_quotes": quotes,
        "market_analysis": analysis,
        "decision_checks": build_checks(line, quotes, analysis),
        "decisions": [dump_decision(x) for x in decisions],
    }


@router.get("/pending")
def pending(db: Session = Depends(get_db)):
    """Return the latest pending decision per RFQ line."""
    rows = db.scalars(
        select(CommercialDecision)
        .where(CommercialDecision.decision_status == "PENDING")
        .order_by(CommercialDecision.created_at.desc())
    ).all()
    seen = set()
    result = []
    for row in rows:
        if row.rfq_line_id in seen:
            continue
        seen.add(row.rfq_line_id)
        result.append(dump_decision(row))
    return result


@router.post("/rfq-lines/{line_id}/decision")
def create_decision(
    line_id: int,
    payload: CommercialDecisionCreate,
    db: Session = Depends(get_db),
):
    line = db.get(RFQLine, line_id)
    if not line:
        raise HTTPException(404, "RFQ line not found")
    if payload.decision_status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid decision status")

    selected = None
    if payload.selected_supplier_quote_line_id is not None:
        selected = db.get(SupplierQuoteLine, payload.selected_supplier_quote_line_id)
        if not selected or selected.rfq_line_id != line_id:
            raise HTTPException(400, "Selected quote line does not belong to this RFQ line")
        if selected.technical_compliance in BLOCKING_COMPLIANCE:
            raise HTTPException(400, "A non-compliant or partially compliant quote line cannot be selected")

    analysis = analyze_rfq_line(line_id, payload.target_currency, db)

    if payload.decision_status == "PROCEED":
        if selected is None:
            raise HTTPException(400, "PROCEED requires an explicitly selected supplier quote line")
        if selected.unit_price is None:
            raise HTTPException(400, "Selected supplier quote line has no unit price")
        if not payload.commercial_notes or not payload.commercial_notes.strip():
            raise HTTPException(400, "Commercial notes/reason are required for PROCEED")

    if payload.decision_status in {"HOLD", "REJECT"}:
        if not payload.commercial_notes or not payload.commercial_notes.strip():
            raise HTTPException(400, "Commercial notes/reason are required for HOLD or REJECT")

    if payload.target_purchase_price is not None and payload.target_currency:
        analysis_currency = analysis.get("target_currency")
        if analysis_currency and analysis_currency.upper() != payload.target_currency.upper():
            raise HTTPException(400, "Target purchase price currency does not match the analysis currency")

    now = datetime.now(timezone.utc)
    row = CommercialDecision(
        rfq_line_id=line_id,
        **payload.model_dump(),
        created_at=now,
        updated_at=now,
        decided_at=now if payload.decision_status != "PENDING" else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return dump_decision(row)

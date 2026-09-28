from datetime import datetime, timezone
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.supplier import Supplier, SupplierQuote, SupplierQuoteLine
from app.models.supplier_performance import SupplierOutreach
from app.models.rfq import RFQ
from app.schemas.supplier_performance import SupplierOutreachCreate

router = APIRouter(prefix="/suppliers", tags=["Supplier Performance Intelligence"])


def _pct(a, b):
    return round((a / b) * 100, 1) if b else None


def _lead_days(value):
    if not value:
        return None
    s = str(value).lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:working\s*)?(?:day|days|d)\b", s)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:week|weeks|wk|wks)\b", s)
    if m:
        return float(m.group(1)) * 7
    return None


@router.post("/outreach", response_model=dict)
def create_outreach(payload: SupplierOutreachCreate, db: Session = Depends(get_db)):
    if not db.get(Supplier, payload.supplier_id):
        raise HTTPException(404, "Supplier not found")
    if not db.get(RFQ, payload.rfq_id):
        raise HTTPException(404, "RFQ not found")
    now = datetime.now(timezone.utc)
    row = SupplierOutreach(**payload.model_dump(), created_at=now, updated_at=now)
    db.add(row)
    db.commit(); db.refresh(row)
    return {"id": row.id, "status": row.status}


@router.get("/{supplier_id}/performance", response_model=dict)
def supplier_performance(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "Supplier not found")

    outreach = db.scalars(select(SupplierOutreach).where(SupplierOutreach.supplier_id == supplier_id)).all()
    quotes = db.scalars(select(SupplierQuote).where(SupplierQuote.supplier_id == supplier_id)).all()
    quote_ids = [q.id for q in quotes]
    lines = db.scalars(select(SupplierQuoteLine).where(SupplierQuoteLine.supplier_quote_id.in_(quote_ids))).all() if quote_ids else []

    requested = sum((x.requested_line_count or 0) for x in outreach)
    responded = sum((x.responded_line_count or 0) for x in outreach)
    responded_outreach = sum(1 for x in outreach if x.response_at or x.status in {"RESPONDED", "QUOTED", "PARTIAL"})
    compliant = sum(1 for x in lines if x.technical_compliance == "COMPLIANT")
    reviewed = sum(1 for x in lines if x.technical_compliance != "NOT_REVIEWED")
    in_stock = sum(1 for x in lines if (x.availability or "").upper() == "IN_STOCK")
    lead_values = [v for v in (_lead_days(x.lead_time) for x in lines) if v is not None]

    response_times = []
    for x in outreach:
        if x.sent_at and x.response_at:
            response_times.append((x.response_at - x.sent_at).total_seconds() / 86400)

    last_quote = max((q.quote_date for q in quotes if q.quote_date), default=None)
    currencies = sorted({q.currency for q in quotes if q.currency})

    return {
        "supplier": {"id": supplier.id, "name": supplier.name_en or supplier.name, "country": supplier.country, "type": supplier.supplier_type, "verification_status": supplier.verification_status},
        "period": {"from": min((x.created_at for x in outreach), default=None), "to": max((x.updated_at for x in outreach), default=None)},
        "outreach": {
            "rfqs_sent": len(outreach), "rfqs_responded": responded_outreach,
            "response_rate_pct": _pct(responded_outreach, len(outreach)),
            "requested_lines": requested or None, "responded_lines": responded or None,
            "line_response_rate_pct": _pct(responded, requested) if requested else None,
            "avg_response_days": round(sum(response_times) / len(response_times), 2) if response_times else None,
        },
        "quotes": {"quote_count": len(quotes), "active_review_count": sum(1 for q in quotes if q.status in {"RECEIVED", "UNDER_REVIEW"}), "last_quote_date": last_quote, "currencies": currencies},
        "quote_lines": {
            "line_count": len(lines), "compliant_count": compliant, "reviewed_count": reviewed,
            "compliance_rate_pct": _pct(compliant, reviewed), "in_stock_count": in_stock,
            "in_stock_rate_pct": _pct(in_stock, len(lines)),
            "avg_stated_lead_days": round(sum(lead_values) / len(lead_values), 2) if lead_values else None,
        },
        "data_quality_note": "Metrics are historical observations from recorded outreach and supplier quotes; they are not a predictive score or guarantee of future performance.",
    }


@router.get("/{supplier_id}/performance/recent", response_model=list[dict])
def recent_supplier_activity(supplier_id: int, limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    if not db.get(Supplier, supplier_id):
        raise HTTPException(404, "Supplier not found")
    rows = db.scalars(select(SupplierOutreach).where(SupplierOutreach.supplier_id == supplier_id).order_by(SupplierOutreach.updated_at.desc()).limit(limit)).all()
    return [{"id": x.id, "rfq_id": x.rfq_id, "status": x.status, "channel": x.channel, "sent_at": x.sent_at, "response_at": x.response_at, "requested_line_count": x.requested_line_count, "responded_line_count": x.responded_line_count, "notes": x.notes} for x in rows]

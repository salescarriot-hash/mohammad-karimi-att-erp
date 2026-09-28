from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.case import Case
from app.models.rfq import RFQ, RFQLine
from app.models.verification import VerificationTask
from app.models.supplier import SupplierQuote
from app.models.commercial_decision import CommercialDecision
from app.models.quotation import Quotation, QuotationLine

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def count_where(db, model, *conditions):
    stmt = select(func.count()).select_from(model)
    if conditions:
        stmt = stmt.where(*conditions)
    return int(db.scalar(stmt) or 0)


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    cases_open = count_where(db, Case, Case.status.in_(["OPEN", "IN_PROGRESS", "WAITING_CUSTOMER"]))
    rfqs_active = count_where(db, RFQ, RFQ.status.in_(["NEW", "UNDER_REVIEW", "WAITING_CLARIFICATION", "SUPPLIER_INQUIRY", "PRICING"]))
    verification_pending = count_where(db, VerificationTask, VerificationTask.status == "PENDING")
    supplier_quotes_received = count_where(db, SupplierQuote, SupplierQuote.status.in_(["RECEIVED", "UNDER_REVIEW"]))
    commercial_pending = count_where(db, CommercialDecision, CommercialDecision.decision_status == "PENDING")
    quotation_pending = count_where(db, Quotation, Quotation.status.in_(["DRAFT", "UNDER_REVIEW", "PENDING_APPROVAL"]))
    quotation_approved = count_where(db, Quotation, Quotation.status == "APPROVED")
    quotation_sent = count_where(db, Quotation, Quotation.status == "SENT")
    rfq_lines_pending = count_where(db, RFQLine, RFQLine.verification_status.in_(["PENDING", "NEEDS_CLARIFICATION"]))
    pricing_pending = count_where(db, QuotationLine, QuotationLine.pricing_status.in_(["PENDING", "NOT_CALCULATED"]))

    recent_cases = db.scalars(select(Case).order_by(Case.updated_at.desc()).limit(8)).all()
    recent_rfqs = db.scalars(select(RFQ).order_by(RFQ.updated_at.desc()).limit(8)).all()
    recent_quotes = db.scalars(select(SupplierQuote).order_by(SupplierQuote.updated_at.desc()).limit(8)).all()
    recent_quotations = db.scalars(select(Quotation).order_by(Quotation.updated_at.desc()).limit(8)).all()

    return {
        "generated_at": now.isoformat(),
        "summary": {
            "cases_open": cases_open,
            "rfqs_active": rfqs_active,
            "verification_pending": verification_pending,
            "supplier_quotes_received": supplier_quotes_received,
            "commercial_pending": commercial_pending,
            "quotation_pending": quotation_pending,
            "quotation_approved": quotation_approved,
            "quotation_sent": quotation_sent,
            "rfq_lines_pending": rfq_lines_pending,
            "pricing_pending": pricing_pending,
        },
        "recent_cases": [
            {"id": x.id, "case_number": x.case_number, "title": x.title, "status": x.status, "priority": x.priority, "updated_at": x.updated_at.isoformat() if x.updated_at else None}
            for x in recent_cases
        ],
        "recent_rfqs": [
            {"id": x.id, "case_id": x.case_id, "customer_rfq_number": x.customer_rfq_number, "title": x.title, "status": x.status, "updated_at": x.updated_at.isoformat() if x.updated_at else None}
            for x in recent_rfqs
        ],
        "recent_supplier_quotes": [
            {"id": x.id, "supplier_id": x.supplier_id, "rfq_id": x.rfq_id, "quote_number": x.quote_number, "status": x.status, "currency": x.currency, "updated_at": x.updated_at.isoformat() if x.updated_at else None}
            for x in recent_quotes
        ],
        "recent_quotations": [
            {"id": x.id, "quotation_number": x.quotation_number, "rfq_id": x.rfq_id, "status": x.status, "currency": x.currency, "grand_total": float(x.grand_total or 0), "updated_at": x.updated_at.isoformat() if x.updated_at else None}
            for x in recent_quotations
        ],
    }

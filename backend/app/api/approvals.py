from datetime import date, datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.quotation import Quotation, QuotationLine
from app.models.pricing import PricingSetting
from app.models.verification import VerificationTask
from app.models.approval import QuotationApproval
from app.schemas.approval import ApprovalAction

router = APIRouter(prefix="/quotations", tags=["Quotation Approval"])

FINAL_STATUSES = {"SENT", "CUSTOMER_ACCEPTED", "CUSTOMER_REJECTED", "CANCELLED"}

def ser(x):
    return {c.name: (float(v) if isinstance(v, Decimal) else v.isoformat() if hasattr(v, "isoformat") else v) for c in x.__table__.columns for v in [getattr(x, c.name)]}

def approval_check(db: Session, q: Quotation):
    lines = db.scalars(select(QuotationLine).where(QuotationLine.quotation_id == q.id).order_by(QuotationLine.line_number)).all()
    blockers = []
    warnings = []
    if not lines:
        blockers.append({"code":"NO_LINES","message":"Quotation has no lines."})
    if not q.currency:
        blockers.append({"code":"MISSING_CURRENCY","message":"Quotation currency is required."})
    if not q.valid_until:
        blockers.append({"code":"MISSING_VALID_UNTIL","message":"Quotation validity date is required."})
    elif q.valid_until < date.today():
        blockers.append({"code":"EXPIRED_VALIDITY","message":"Quotation validity date has already passed."})
    if not q.incoterm:
        blockers.append({"code":"MISSING_INCOTERM","message":"Incoterm is required before approval."})
    if q.grand_total is None:
        blockers.append({"code":"MISSING_TOTAL","message":"Quotation grand total is missing."})

    settings = db.scalars(select(PricingSetting).order_by(PricingSetting.id.desc())).first()
    for line in lines:
        prefix = f"Line {line.line_number}"
        if line.final_selling_price is None or line.pricing_status not in {"CALCULATED", "MANUAL_OVERRIDE"}:
            blockers.append({"code":"PRICING_MISSING","line_id":line.id,"message":f"{prefix}: valid pricing is required."})
        if line.manual_selling_price is not None and not (line.override_reason or "").strip():
            blockers.append({"code":"OVERRIDE_REASON_MISSING","line_id":line.id,"message":f"{prefix}: manual price override requires a reason."})
        if line.currency and q.currency and line.currency != q.currency:
            blockers.append({"code":"CURRENCY_MISMATCH","line_id":line.id,"message":f"{prefix}: line currency differs from quotation currency."})
        if line.quantity is None or line.quantity <= 0:
            blockers.append({"code":"INVALID_QUANTITY","line_id":line.id,"message":f"{prefix}: quantity must be greater than zero."})
        if line.technical_compliance in {None, "NOT_REVIEWED", "EQUIVALENT_PENDING", "PARTIALLY_COMPLIANT", "NON_COMPLIANT"}:
            blockers.append({"code":"TECHNICAL_COMPLIANCE","line_id":line.id,"message":f"{prefix}: technical compliance must be reviewed and compliant."})
        if line.verification_status not in {None, "CONFIRMED"}:
            blockers.append({"code":"LINE_VERIFICATION","line_id":line.id,"message":f"{prefix}: verification is not confirmed."})
        if settings and settings.minimum_margin_value is not None and line.margin_value is not None:
            if settings.minimum_margin_type == line.margin_type and line.margin_value < settings.minimum_margin_value:
                blockers.append({"code":"BELOW_MIN_MARGIN","line_id":line.id,"message":f"{prefix}: margin is below configured minimum."})
        if line.pricing_status == "MANUAL_OVERRIDE":
            warnings.append({"code":"MANUAL_OVERRIDE","line_id":line.id,"message":f"{prefix}: manual selling price override is present."})

    pending = db.scalars(select(VerificationTask).where(
        VerificationTask.case_id == q.case_id,
        VerificationTask.status.in_(["PENDING", "NEEDS_CLARIFICATION"])
    )).all()
    if pending:
        blockers.append({"code":"PENDING_VERIFICATION","message":f"{len(pending)} pending verification task(s) remain for this case."})
    return {"quotation_id":q.id,"status":q.status,"can_approve":not blockers,"blockers":blockers,"warnings":warnings,"line_count":len(lines)}

@router.get("/{quotation_id}/approval-check")
def check(quotation_id: int, db: Session = Depends(get_db)):
    q = db.get(Quotation, quotation_id)
    if not q: raise HTTPException(404, "Quotation not found")
    return approval_check(db, q)

@router.get("/{quotation_id}/approval-history")
def history(quotation_id: int, db: Session = Depends(get_db)):
    q = db.get(Quotation, quotation_id)
    if not q: raise HTTPException(404, "Quotation not found")
    rows = db.scalars(select(QuotationApproval).where(QuotationApproval.quotation_id == quotation_id).order_by(QuotationApproval.id.desc())).all()
    return [ser(x) for x in rows]

@router.post("/{quotation_id}/submit-for-review")
def submit_for_review(quotation_id: int, db: Session = Depends(get_db)):
    q = db.get(Quotation, quotation_id)
    if not q: raise HTTPException(404, "Quotation not found")
    if q.status != "DRAFT": raise HTTPException(409, f"Only DRAFT quotations can be submitted; current status is {q.status}")
    result = approval_check(db, q)
    if result["blockers"]:
        raise HTTPException(422, detail=result)
    old=q.status; q.status="PENDING_APPROVAL"; q.updated_at=datetime.now(timezone.utc)
    db.add(QuotationApproval(quotation_id=q.id, action="SUBMIT", status_from=old, status_to=q.status, created_at=datetime.now(timezone.utc)))
    db.commit(); db.refresh(q)
    return {**ser(q), "approval_check":result}

@router.post("/{quotation_id}/approve")
def approve(quotation_id: int, payload: ApprovalAction, db: Session = Depends(get_db)):
    q = db.get(Quotation, quotation_id)
    if not q: raise HTTPException(404, "Quotation not found")
    if q.status != "PENDING_APPROVAL": raise HTTPException(409, f"Quotation must be PENDING_APPROVAL; current status is {q.status}")
    result=approval_check(db,q)
    if result["blockers"]: raise HTTPException(422, detail=result)
    old=q.status; q.status="APPROVED"; q.updated_at=datetime.now(timezone.utc)
    db.add(QuotationApproval(quotation_id=q.id, action="APPROVE", status_from=old, status_to=q.status, reason=payload.reason, created_at=datetime.now(timezone.utc)))
    db.commit(); db.refresh(q); return ser(q)

@router.post("/{quotation_id}/reject-approval")
def reject(quotation_id: int, payload: ApprovalAction, db: Session = Depends(get_db)):
    q = db.get(Quotation, quotation_id)
    if not q: raise HTTPException(404, "Quotation not found")
    if q.status != "PENDING_APPROVAL": raise HTTPException(409, f"Quotation must be PENDING_APPROVAL; current status is {q.status}")
    reason=(payload.reason or "").strip()
    if not reason: raise HTTPException(400,"Rejection reason is required")
    old=q.status; q.status="DRAFT"; q.updated_at=datetime.now(timezone.utc)
    db.add(QuotationApproval(quotation_id=q.id, action="REJECT", status_from=old, status_to=q.status, reason=reason, created_at=datetime.now(timezone.utc)))
    db.commit(); db.refresh(q); return ser(q)

@router.post("/{quotation_id}/send")
def send(quotation_id: int, db: Session = Depends(get_db)):
    q = db.get(Quotation, quotation_id)
    if not q: raise HTTPException(404, "Quotation not found")
    if q.status != "APPROVED": raise HTTPException(409, "Only APPROVED quotations can be sent")
    old=q.status; q.status="SENT"; q.updated_at=datetime.now(timezone.utc)
    db.add(QuotationApproval(quotation_id=q.id, action="SEND", status_from=old, status_to=q.status, created_at=datetime.now(timezone.utc)))
    db.commit(); db.refresh(q); return ser(q)

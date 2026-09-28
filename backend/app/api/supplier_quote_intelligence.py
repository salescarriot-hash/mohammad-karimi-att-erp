from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.case import Case
from app.models.file import CaseFile
from app.models.rfq import RFQ, RFQLine
from app.models.supplier import Supplier, SupplierQuote, SupplierQuoteLine
from app.models.verification import VerificationTask
from app.services.supplier_quote_intake import extract_supplier_quote

router = APIRouter(prefix="/document-intelligence", tags=["Supplier Quote Intelligence"])


def now():
    return datetime.now(timezone.utc)


def get_file(db, case_id, file_id):
    db.get(Case, case_id) or (_ for _ in ()).throw(HTTPException(404, "Case not found"))
    record = db.scalar(select(CaseFile).where(CaseFile.id == file_id, CaseFile.case_id == case_id))
    if not record:
        raise HTTPException(404, "Case file not found")
    base = Path(settings.storage_path).resolve()
    path = (base / record.file_path).resolve()
    if base not in path.parents or not path.exists():
        raise HTTPException(404, "Stored file is missing")
    return record, path


def rfq_for_case(db, case_id, rfq_id):
    row = db.scalar(select(RFQ).where(RFQ.id == rfq_id, RFQ.case_id == case_id))
    if not row:
        raise HTTPException(400, "RFQ does not belong to this Case")
    return row


@router.post("/cases/{case_id}/files/{file_id}/supplier-quote-preview")
def supplier_quote_preview(case_id: int, file_id: int, rfq_id: int | None = None, db: Session = Depends(get_db)):
    record, path = get_file(db, case_id, file_id)
    rfq_lines = []
    if rfq_id is not None:
        rfq = rfq_for_case(db, case_id, rfq_id)
        rfq_lines = list(db.scalars(select(RFQLine).where(RFQLine.rfq_id == rfq.id).order_by(RFQLine.line_number)).all())
    result = extract_supplier_quote(record.original_file_name, path.read_bytes(), rfq_lines)

    supplier_name = result.get("supplier_name_candidate")
    candidates = []
    if supplier_name:
        like = f"%{supplier_name}%"
        suppliers = db.scalars(select(Supplier).where(Supplier.status == "ACTIVE").where(
            (Supplier.name.ilike(like)) | (Supplier.name_en.ilike(like))
        ).limit(10)).all()
        candidates = [{"supplier_id": s.id, "name": s.name_en or s.name, "confidence": 0.90, "source": "supplier_master"} for s in suppliers]
    result["supplier_candidates"] = candidates
    result["rfq_id"] = rfq_id
    result["file_id"] = file_id
    return result


@router.post("/cases/{case_id}/files/{file_id}/supplier-quote-verification-tasks")
def create_supplier_quote_verification_tasks(case_id: int, file_id: int, rfq_id: int | None = None, db: Session = Depends(get_db)):
    record, path = get_file(db, case_id, file_id)
    rfq_lines = []
    if rfq_id is not None:
        rfq = rfq_for_case(db, case_id, rfq_id)
        rfq_lines = list(db.scalars(select(RFQLine).where(RFQLine.rfq_id == rfq.id).order_by(RFQLine.line_number)).all())
    result = extract_supplier_quote(record.original_file_name, path.read_bytes(), rfq_lines)
    created = []
    tnow = now()
    for field in result.get("fields", []):
        if not field.get("value"):
            continue
        task = VerificationTask(
            case_id=case_id, rfq_id=rfq_id, field_name=f"supplier_quote.{field['field_name']}",
            reason="EXTRACTION", status="PENDING", source_file_id=file_id,
            extracted_value=str(field["value"]), confidence=Decimal(str(field.get("confidence", 0))),
            created_at=tnow, updated_at=tnow,
        )
        db.add(task); created.append(task)
    for item in result.get("lines", []):
        line_ref = item.get("rfq_line_candidate_id")
        for field_name in ("supplier_part_number", "description", "quantity", "unit_price", "total_price", "condition", "lead_time", "availability"):
            value = item.get(field_name)
            if value is None or value == "":
                continue
            task = VerificationTask(
                case_id=case_id, rfq_id=rfq_id, rfq_line_id=line_ref,
                field_name=f"supplier_quote_line.{item.get('line_number')}.{field_name}",
                reason="EXTRACTION", status="PENDING", source_file_id=file_id,
                extracted_value=str(value), confidence=Decimal(str(item.get("confidence", 0))),
                created_at=tnow, updated_at=tnow,
            )
            db.add(task); created.append(task)
        if line_ref is not None and item.get("rfq_line_match_confidence", 0) < 0.80:
            task = VerificationTask(
                case_id=case_id, rfq_id=rfq_id, rfq_line_id=line_ref,
                field_name=f"supplier_quote_line.{item.get('line_number')}.rfq_line_match",
                reason="MASTER_MATCHING", status="PENDING", source_file_id=file_id,
                extracted_value=str(line_ref), confidence=Decimal(str(item.get("rfq_line_match_confidence", 0))),
                created_at=tnow, updated_at=tnow, notes="Candidate RFQ line match; must be confirmed by user.",
            )
            db.add(task); created.append(task)
    db.commit()
    return {"created": len(created), "task_ids": [x.id for x in created], "requires_user_confirmation": True}


class ConfirmedQuoteField(BaseModel):
    field_name: str
    value: str | None = None


class ConfirmedQuoteLine(BaseModel):
    rfq_line_id: int
    supplier_part_number: str | None = None
    description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    condition: str | None = None
    brand: str | None = None
    manufacturer: str | None = None
    lead_time: str | None = None
    availability: str | None = None
    technical_compliance: str = "NOT_REVIEWED"
    deviation: str | None = None
    notes: str | None = None


class ConfirmSupplierQuote(BaseModel):
    supplier_id: int
    rfq_id: int
    quote_number: str | None = None
    quote_date: str | None = None
    valid_until: str | None = None
    currency: str | None = None
    incoterm: str | None = None
    delivery_time: str | None = None
    payment_terms: str | None = None
    origin: str | None = None
    warranty: str | None = None
    source_file_id: int | None = None
    source_url: str | None = None
    notes: str | None = None
    lines: list[ConfirmedQuoteLine] = Field(default_factory=list)
    verification_task_ids: list[int] = Field(default_factory=list)


def parse_date(v):
    if not v:
        return None
    from datetime import date
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


@router.post("/cases/{case_id}/supplier-quotes/confirm")
def confirm_supplier_quote(case_id: int, payload: ConfirmSupplierQuote, db: Session = Depends(get_db)):
    rfq = rfq_for_case(db, case_id, payload.rfq_id)
    supplier = db.get(Supplier, payload.supplier_id)
    if not supplier:
        raise HTTPException(400, "Supplier must be selected/confirmed before creating the Supplier Quote")
    if payload.source_file_id:
        record, _ = get_file(db, case_id, payload.source_file_id)
        source_file = record.file_path
    else:
        source_file = None
    for line in payload.lines:
        rfq_line = db.get(RFQLine, line.rfq_line_id)
        if not rfq_line or rfq_line.rfq_id != rfq.id:
            raise HTTPException(400, f"RFQ line {line.rfq_line_id} does not belong to RFQ {rfq.id}")
    tnow = now()
    quote = SupplierQuote(
        supplier_id=supplier.id, rfq_id=rfq.id, quote_number=payload.quote_number,
        quote_date=parse_date(payload.quote_date), valid_until=parse_date(payload.valid_until),
        currency=payload.currency, incoterm=payload.incoterm, delivery_time=payload.delivery_time,
        payment_terms=payload.payment_terms, origin=payload.origin, warranty=payload.warranty,
        source_file=source_file, source_url=payload.source_url, status="RECEIVED", notes=payload.notes,
        created_at=tnow, updated_at=tnow,
    )
    db.add(quote); db.flush()
    for line in payload.lines:
        db.add(SupplierQuoteLine(
            supplier_quote_id=quote.id, rfq_line_id=line.rfq_line_id,
            supplier_part_number=line.supplier_part_number, description=line.description,
            quantity=line.quantity, unit=line.unit, unit_price=line.unit_price, total_price=line.total_price,
            condition=line.condition, brand=line.brand, manufacturer=line.manufacturer,
            lead_time=line.lead_time, availability=line.availability,
            technical_compliance=line.technical_compliance, deviation=line.deviation, notes=line.notes,
            created_at=tnow, updated_at=tnow,
        ))
    if payload.verification_task_ids:
        tasks = db.scalars(select(VerificationTask).where(VerificationTask.id.in_(payload.verification_task_ids), VerificationTask.case_id == case_id)).all()
        for task in tasks:
            task.status = "CONFIRMED"
            task.verified_at = tnow
            task.updated_at = tnow
    db.commit(); db.refresh(quote)
    return {"id": quote.id, "status": quote.status, "supplier_id": quote.supplier_id, "rfq_id": quote.rfq_id, "lines": len(payload.lines)}

@router.get("/supplier-quotes/{quote_id}/validation")
def validate_confirmed_supplier_quote(quote_id: int, db: Session = Depends(get_db)):
    from app.services.supplier_quote_validation import compare_quote
    quote = db.get(SupplierQuote, quote_id)
    if not quote:
        raise HTTPException(404, "Supplier Quote not found")
    rfq = db.get(RFQ, quote.rfq_id)
    rfq_lines = list(db.scalars(select(RFQLine).where(RFQLine.rfq_id == rfq.id).order_by(RFQLine.line_number)).all())
    quote_lines = list(db.scalars(select(SupplierQuoteLine).where(SupplierQuoteLine.supplier_quote_id == quote.id)).all())
    return compare_quote(rfq, rfq_lines, quote, quote_lines)


@router.post("/supplier-quotes/{quote_id}/validation-tasks")
def create_supplier_quote_validation_tasks(quote_id: int, db: Session = Depends(get_db)):
    from app.services.supplier_quote_validation import compare_quote
    quote = db.get(SupplierQuote, quote_id)
    if not quote:
        raise HTTPException(404, "Supplier Quote not found")
    rfq = db.get(RFQ, quote.rfq_id)
    rfq_lines = list(db.scalars(select(RFQLine).where(RFQLine.rfq_id == rfq.id).order_by(RFQLine.line_number)).all())
    quote_lines = list(db.scalars(select(SupplierQuoteLine).where(SupplierQuoteLine.supplier_quote_id == quote.id)).all())
    analysis = compare_quote(rfq, rfq_lines, quote, quote_lines)
    created = []
    tnow = now()

    for conflict in analysis["header_conflicts"]:
        task = VerificationTask(case_id=rfq.case_id, rfq_id=rfq.id,
            field_name=f"supplier_quote.{conflict['field']}", reason="CONFLICT", status="PENDING",
            extracted_value=str(conflict["actual"]), confidence=Decimal("1.0"),
            notes=f"Expected: {conflict['expected']}. {conflict['reason']}", created_at=tnow, updated_at=tnow)
        db.add(task); created.append(task)

    for item in analysis["line_results"]:
        for conflict in item["conflicts"]:
            task = VerificationTask(case_id=rfq.case_id, rfq_id=rfq.id, rfq_line_id=item["rfq_line_id"],
                field_name=f"supplier_quote_line.{conflict['field']}", reason="CONFLICT", status="PENDING",
                extracted_value=str(conflict["actual"]), confidence=Decimal("1.0"),
                notes=f"Expected: {conflict['expected']}. {conflict['reason']}", created_at=tnow, updated_at=tnow)
            db.add(task); created.append(task)

    for item in analysis["unmatched_rfq_lines"]:
        task = VerificationTask(case_id=rfq.case_id, rfq_id=rfq.id, rfq_line_id=item["rfq_line_id"],
            field_name="supplier_quote_line.match", reason="MASTER_MATCHING", status="PENDING",
            extracted_value="", confidence=Decimal("0"), notes=item["reason"], created_at=tnow, updated_at=tnow)
        db.add(task); created.append(task)

    db.commit()
    return {"created": len(created), "task_ids": [x.id for x in created], "analysis": analysis}

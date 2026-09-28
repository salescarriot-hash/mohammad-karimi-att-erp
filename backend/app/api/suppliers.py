from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.supplier import Supplier, SupplierQuote, SupplierQuoteLine
from app.models.rfq import RFQ, RFQLine
from app.models.master import Part, Manufacturer
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierSearchOut, SupplierQuoteCreate, SupplierQuoteLineCreate

router = APIRouter(prefix="/suppliers", tags=["Suppliers & Supplier Search"])

def norm(v):
    return " ".join((v or "").lower().replace("-", " ").replace("_", " ").split())

@router.post("", response_model=SupplierOut)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    row = Supplier(**payload.model_dump(), created_at=now, updated_at=now)
    db.add(row); db.commit(); db.refresh(row)
    return row

@router.get("", response_model=list[SupplierOut])
def list_suppliers(q: str | None = None, country: str | None = None, supplier_type: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Supplier).where(Supplier.status == "ACTIVE")
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Supplier.name.ilike(like), Supplier.name_en.ilike(like), Supplier.contact_name.ilike(like)))
    if country: stmt = stmt.where(Supplier.country.ilike(country))
    if supplier_type: stmt = stmt.where(Supplier.supplier_type == supplier_type)
    return db.scalars(stmt.order_by(Supplier.name)).all()

@router.get("/search-for-rfq-line/{line_id}", response_model=list[SupplierSearchOut])
def search_suppliers_for_line(line_id: int, limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    line = db.get(RFQLine, line_id)
    if not line: raise HTTPException(404, "RFQ line not found")
    part = db.get(Part, line.part_id) if line.part_id else None
    manufacturer_name = norm(line.manufacturer)
    if part and part.manufacturer_id:
        m = db.get(Manufacturer, part.manufacturer_id)
        if m: manufacturer_name = norm(m.name_en or m.name)
    desc = norm(line.description_normalized or line.description_original)
    pn = norm(part.part_number if part else line.customer_part_number)
    suppliers = db.scalars(select(Supplier).where(Supplier.status == "ACTIVE")).all()
    results = []
    for s in suppliers:
        score = 0; reasons = []
        snames = {norm(s.name), norm(s.name_en)}
        if manufacturer_name and any(manufacturer_name == x or manufacturer_name in x or x in manufacturer_name for x in snames if x):
            score += 60; reasons.append("Supplier name matches requested manufacturer")
        text = norm(" ".join(filter(None, [s.notes, s.name, s.name_en])))
        if desc and text and any(token in text for token in desc.split() if len(token) >= 4):
            score += 10; reasons.append("Supplier profile overlaps RFQ description")
        if s.verification_status == "CONFIRMED":
            score += 10; reasons.append("Supplier master is confirmed")
        if s.supplier_type in {"MANUFACTURER", "DISTRIBUTOR", "STOCKIST", "TRADER"}:
            score += 5; reasons.append("Supplier type is relevant to sourcing")
        if score > 0:
            results.append(SupplierSearchOut(supplier_id=s.id, supplier_name=s.name_en or s.name, supplier_type=s.supplier_type, country=s.country, match_score=min(score,100), match_reasons=reasons, verification_status=s.verification_status))
    results.sort(key=lambda x: (-x.match_score, x.supplier_name.lower()))
    return results[:limit]



@router.get("/quotes", response_model=list[dict])
def list_supplier_quotes(rfq_id: int | None = None, supplier_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(SupplierQuote)
    if rfq_id is not None:
        stmt = stmt.where(SupplierQuote.rfq_id == rfq_id)
    if supplier_id is not None:
        stmt = stmt.where(SupplierQuote.supplier_id == supplier_id)
    rows = db.scalars(stmt.order_by(SupplierQuote.id.desc())).all()
    return [{
        "id": r.id, "supplier_id": r.supplier_id, "rfq_id": r.rfq_id,
        "quote_number": r.quote_number, "quote_date": r.quote_date.isoformat() if r.quote_date else None,
        "valid_until": r.valid_until.isoformat() if r.valid_until else None, "currency": r.currency,
        "incoterm": r.incoterm, "delivery_time": r.delivery_time, "payment_terms": r.payment_terms,
        "origin": r.origin, "warranty": r.warranty, "source_file": r.source_file,
        "source_url": r.source_url, "status": r.status, "notes": r.notes
    } for r in rows]

@router.get("/quotes/{quote_id}/lines", response_model=list[dict])
def list_supplier_quote_lines(quote_id: int, db: Session = Depends(get_db)):
    if not db.get(SupplierQuote, quote_id):
        raise HTTPException(404, "Supplier quote not found")
    rows = db.scalars(select(SupplierQuoteLine).where(SupplierQuoteLine.supplier_quote_id == quote_id).order_by(SupplierQuoteLine.id)).all()
    return [{
        "id": r.id, "supplier_quote_id": r.supplier_quote_id, "rfq_line_id": r.rfq_line_id,
        "supplier_part_number": r.supplier_part_number, "description": r.description,
        "quantity": float(r.quantity) if r.quantity is not None else None, "unit": r.unit,
        "unit_price": float(r.unit_price) if r.unit_price is not None else None,
        "total_price": float(r.total_price) if r.total_price is not None else None,
        "condition": r.condition, "brand": r.brand, "manufacturer": r.manufacturer,
        "lead_time": r.lead_time, "availability": r.availability,
        "technical_compliance": r.technical_compliance, "deviation": r.deviation, "notes": r.notes
    } for r in rows]

@router.post("/quotes", response_model=dict)
def create_supplier_quote(payload: SupplierQuoteCreate, db: Session = Depends(get_db)):
    if not db.get(Supplier, payload.supplier_id): raise HTTPException(404, "Supplier not found")
    if not db.get(RFQ, payload.rfq_id): raise HTTPException(404, "RFQ not found")
    now = datetime.now(timezone.utc)
    row = SupplierQuote(**payload.model_dump(), created_at=now, updated_at=now)
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "status": row.status}

@router.post("/quotes/{quote_id}/lines", response_model=dict)
def create_supplier_quote_line(quote_id: int, payload: SupplierQuoteLineCreate, db: Session = Depends(get_db)):
    quote = db.get(SupplierQuote, quote_id)
    if not quote: raise HTTPException(404, "Supplier quote not found")
    line = db.get(RFQLine, payload.rfq_line_id)
    if not line or line.rfq_id != quote.rfq_id: raise HTTPException(400, "RFQ line does not belong to the quote's RFQ")
    now = datetime.now(timezone.utc)
    row = SupplierQuoteLine(supplier_quote_id=quote_id, **payload.model_dump(), created_at=now, updated_at=now)
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "status": "RECEIVED"}

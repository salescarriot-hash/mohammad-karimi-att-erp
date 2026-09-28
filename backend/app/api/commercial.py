from datetime import datetime, timezone, date
from statistics import median
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.commercial import MarketPrice
from app.models.rfq import RFQLine
from app.models.supplier import SupplierQuoteLine, SupplierQuote
from app.models.master import Part
from app.schemas.commercial import MarketPriceCreate
from app.services.commercial_intelligence import analyze_line

router = APIRouter(prefix="/commercial", tags=["Commercial Intelligence"])

def dump_market(r):
    return {"id":r.id,"part_id":r.part_id,"supplier_id":r.supplier_id,"source_type":r.source_type,"source_name":r.source_name,"source_url":r.source_url,"condition":r.condition,"brand":r.brand,"part_number":r.part_number,"quantity":float(r.quantity) if r.quantity is not None else None,"unit":r.unit,"unit_price":float(r.unit_price),"currency":r.currency,"incoterm":r.incoterm,"lead_time":r.lead_time,"availability":r.availability,"observed_date":r.observed_date.isoformat() if r.observed_date else None,"confidence":r.confidence,"verification_status":r.verification_status,"notes":r.notes}

@router.post("/market-prices")
def create_market_price(payload: MarketPriceCreate, db: Session = Depends(get_db)):
    now=datetime.now(timezone.utc)
    row=MarketPrice(**payload.model_dump(), created_at=now, updated_at=now)
    db.add(row); db.commit(); db.refresh(row)
    return dump_market(row)

@router.get("/market-prices")
def list_market_prices(part_id:int|None=None, part_number:str|None=None, currency:str|None=None, db:Session=Depends(get_db)):
    stmt=select(MarketPrice)
    if part_id is not None: stmt=stmt.where(MarketPrice.part_id==part_id)
    if part_number: stmt=stmt.where(MarketPrice.part_number.ilike(part_number))
    if currency: stmt=stmt.where(MarketPrice.currency.ilike(currency))
    return [dump_market(x) for x in db.scalars(stmt.order_by(MarketPrice.observed_date.desc().nullslast(), MarketPrice.id.desc())).all()]

@router.get("/rfq-lines/{line_id}/analysis")
def analyze_rfq_line(line_id:int, currency:str|None=None, include_equivalents:bool=False, db:Session=Depends(get_db)):
    """Backward-compatible endpoint backed by the advanced commercial engine."""
    try:
        return analyze_line(db, line_id, currency, include_equivalents)
    except ValueError as exc:
        raise HTTPException(404, str(exc))

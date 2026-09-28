from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.supplier_quote_comparison import compare_quotes_for_line

router = APIRouter(prefix="/supplier-quote-comparison", tags=["Supplier Quote Comparison"])

@router.get("/rfq-lines/{line_id}")
def compare(line_id: int, db: Session = Depends(get_db)):
    try:
        return compare_quotes_for_line(db, line_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))

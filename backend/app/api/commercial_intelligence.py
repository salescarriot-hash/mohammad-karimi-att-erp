from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.commercial_intelligence import analyze_line

router = APIRouter(prefix="/commercial-intelligence", tags=["Advanced Commercial Intelligence"])

@router.get("/rfq-lines/{line_id}/analysis")
def advanced_analysis(
    line_id: int,
    currency: str | None = Query(None),
    include_equivalents: bool = Query(False),
    db: Session = Depends(get_db),
):
    try:
        return analyze_line(db, line_id, currency, include_equivalents)
    except ValueError as exc:
        raise HTTPException(404, str(exc))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
from app.db.session import get_db
from app.models.knowledge import KnowledgeAssertion
from app.models.rfq import RFQLine
from app.services.industrial_knowledge import rfq_line_candidates, part_graph, knowledge_search

router = APIRouter(prefix="/industrial-knowledge", tags=["Industrial Knowledge"])

@router.get("/rfq-lines/{line_id}/candidates")
def candidates(line_id: int, db: Session = Depends(get_db)):
    line = db.get(RFQLine, line_id)
    if not line: raise HTTPException(404, "RFQ line not found")
    return rfq_line_candidates(db, line)

@router.get("/parts/{part_id}/graph")
def graph(part_id: int, db: Session = Depends(get_db)):
    return part_graph(db, part_id)

@router.get("/search")
def search(q: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return {"query": q, "results": knowledge_search(db, q, limit)}

@router.post("/assertions")
def create_assertion(payload: dict, db: Session = Depends(get_db)):
    required = ["subject_type", "predicate"]
    missing = [k for k in required if not payload.get(k)]
    if missing: raise HTTPException(400, f"Missing: {', '.join(missing)}")
    a = KnowledgeAssertion(
        subject_type=payload["subject_type"], subject_id=payload.get("subject_id"), subject_label=payload.get("subject_label"),
        predicate=payload["predicate"], object_type=payload.get("object_type"), object_id=payload.get("object_id"),
        object_label=payload.get("object_label"), object_text=payload.get("object_text"), source_file_id=payload.get("source_file_id"),
        source=payload.get("source", "USER_CONFIRMED"), evidence_text=payload.get("evidence_text"),
        confidence=payload.get("confidence", 1.0), verification_status=payload.get("verification_status", "PENDING"),
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    db.add(a); db.commit(); db.refresh(a)
    return {"id": a.id, "verification_status": a.verification_status, "message": "Knowledge assertion stored; it is not treated as confirmed unless explicitly confirmed."}

@router.post("/assertions/{assertion_id}/confirm")
def confirm_assertion(assertion_id: int, db: Session = Depends(get_db)):
    a = db.get(KnowledgeAssertion, assertion_id)
    if not a: raise HTTPException(404, "Assertion not found")
    a.verification_status = "CONFIRMED"; a.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": a.id, "verification_status": a.verification_status}

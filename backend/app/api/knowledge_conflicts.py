from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.knowledge_conflict import KnowledgeConflict
from app.models.knowledge import KnowledgeAssertion
from app.models.verification import VerificationTask
from app.models.file import CaseFile

router = APIRouter(prefix="/knowledge-conflicts", tags=["Knowledge Conflicts"])

def now(): return datetime.now(timezone.utc)

class ConflictDecision(BaseModel):
    action: str
    verified_value: str | None = None
    notes: str | None = None

@router.get("")
def list_conflicts(db: Session = Depends(get_db), status: str = "PENDING"):
    q = select(KnowledgeConflict).order_by(KnowledgeConflict.id.desc())
    if status: q = q.where(KnowledgeConflict.status == status.upper())
    return list(db.scalars(q).all())

@router.post("/{conflict_id}/verification-task")
def create_task(conflict_id: int, db: Session = Depends(get_db)):
    c = db.get(KnowledgeConflict, conflict_id)
    if not c: raise HTTPException(404, "Conflict not found")
    a = db.get(KnowledgeAssertion, c.assertion_id)
    f = db.get(CaseFile, a.source_file_id) if a else None
    if not a or not f: raise HTTPException(404, "Conflict source not found")
    marker = f"knowledge_conflict_id={c.id}"
    existing = db.query(VerificationTask).filter(VerificationTask.reason == "KNOWLEDGE_CONFLICT", VerificationTask.notes.like(f"%{marker}%")).first()
    if existing: return {"task_id": existing.id, "created": False}
    task = VerificationTask(case_id=f.case_id, field_name=c.field_name, current_value=c.current_value, requested_value=c.new_value,
        reason="KNOWLEDGE_CONFLICT", status="PENDING", source_file_id=a.source_file_id, extracted_value=c.new_value,
        confidence=a.confidence, notes=f"{marker}; existing_assertion_id={c.existing_assertion_id}", created_at=now(), updated_at=now())
    db.add(task); db.commit(); db.refresh(task)
    return {"task_id": task.id, "created": True}

@router.post("/{conflict_id}/resolve")
def resolve(conflict_id: int, payload: ConflictDecision, db: Session = Depends(get_db)):
    c = db.get(KnowledgeConflict, conflict_id)
    if not c: raise HTTPException(404, "Conflict not found")
    action = payload.action.strip().upper()
    if action not in {"KEEP_EXISTING", "ACCEPT_NEW", "EDIT_AND_ACCEPT", "NEEDS_CLARIFICATION"}:
        raise HTTPException(400, "Invalid conflict action")
    new = db.get(KnowledgeAssertion, c.assertion_id)
    old = db.get(KnowledgeAssertion, c.existing_assertion_id)
    if action == "KEEP_EXISTING":
        new.verification_status = "REJECTED"; c.status = "RESOLVED"; c.resolution = "KEEP_EXISTING"
    elif action == "ACCEPT_NEW":
        new.verification_status = "CONFIRMED"; old.verification_status = "REJECTED"; c.status = "RESOLVED"; c.resolution = "ACCEPT_NEW"
    elif action == "EDIT_AND_ACCEPT":
        if not payload.verified_value: raise HTTPException(400, "verified_value is required")
        new.object_text = payload.verified_value.strip(); new.verification_status = "CONFIRMED"; old.verification_status = "REJECTED"; c.status = "RESOLVED"; c.resolution = "EDIT_AND_ACCEPT"
    else:
        c.status = "NEEDS_CLARIFICATION"; c.resolution = payload.notes or "Needs clarification"
    c.updated_at = now(); new.updated_at = now(); old.updated_at = now()
    db.commit(); db.refresh(c)
    return c

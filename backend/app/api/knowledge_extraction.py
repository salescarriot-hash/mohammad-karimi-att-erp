from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.knowledge_extraction import extract_file_knowledge, file_assertions
from app.models.file import CaseFile
from app.models.verification import VerificationTask
from datetime import datetime, timezone

router = APIRouter(prefix="/knowledge-extraction", tags=["Knowledge Extraction"])

@router.post("/files/{file_id}/extract")
def extract(file_id: int, db: Session = Depends(get_db)):
    result = extract_file_knowledge(db, file_id)
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return result

@router.get("/files/{file_id}/assertions")
def assertions(file_id: int, db: Session = Depends(get_db)):
    if not db.get(CaseFile, file_id):
        raise HTTPException(404, "File not found")
    return {"file_id": file_id, "assertions": file_assertions(db, file_id)}


@router.post("/files/{file_id}/verification-tasks")
def create_verification_tasks(file_id: int, db: Session = Depends(get_db)):
    file = db.get(CaseFile, file_id)
    if not file:
        raise HTTPException(404, "File not found")
    assertions = file_assertions(db, file_id)
    created = []
    now = datetime.now(timezone.utc)
    for a in assertions:
        if a.get("status") != "PENDING":
            continue
        marker = f"knowledge_assertion_id={a['id']}"
        existing = db.query(VerificationTask).filter(
            VerificationTask.source_file_id == file_id,
            VerificationTask.reason == "KNOWLEDGE_EXTRACTION",
            VerificationTask.notes.like(f"%{marker}%")
        ).first()
        if existing:
            continue
        task = VerificationTask(
            case_id=file.case_id,
            field_name=a.get("predicate") or "industrial_knowledge",
            current_value=None,
            requested_value=a.get("value"),
            reason="KNOWLEDGE_EXTRACTION",
            status="PENDING",
            source_file_id=file_id,
            extracted_value=a.get("value"),
            confidence=a.get("confidence"),
            notes=f"{marker}; source={a.get('source')}; evidence={a.get('evidence') or ''}",
            created_at=now, updated_at=now
        )
        db.add(task); created.append(task)
    db.commit()
    return {"file_id": file_id, "created": len(created), "task_ids": [x.id for x in created], "message": "Knowledge candidates sent to Verification Center; no candidate is confirmed automatically."}

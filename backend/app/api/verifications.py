from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.verification import VerificationTask
from app.models.knowledge import KnowledgeAssertion
from app.models.rfq import RFQ, RFQLine
from app.schemas.rfq import CONDITIONS
from decimal import Decimal, InvalidOperation
from datetime import date
from app.schemas.verification import VerificationOut, VerificationDecision

router=APIRouter(prefix="/verification-tasks", tags=["Verification"])

def now(): return datetime.now(timezone.utc)

def get_task(db, task_id):
    task=db.get(VerificationTask, task_id)
    if not task: raise HTTPException(404,"Verification task not found")
    return task

@router.get("", response_model=list[VerificationOut])
def list_tasks(db:Session=Depends(get_db), case_id:int|None=None, rfq_id:int|None=None, status:str|None="PENDING"):
    q=select(VerificationTask).order_by(VerificationTask.id.desc())
    if case_id is not None: q=q.where(VerificationTask.case_id==case_id)
    if rfq_id is not None: q=q.where(VerificationTask.rfq_id==rfq_id)
    if status:
        q=q.where(VerificationTask.status==status.strip().upper())
    return list(db.scalars(q).all())

@router.get("/{task_id}", response_model=VerificationOut)
def read_task(task_id:int, db:Session=Depends(get_db)): return get_task(db,task_id)

@router.post("/{task_id}/decision", response_model=VerificationOut)
def decide(task_id:int, payload:VerificationDecision, db:Session=Depends(get_db)):
    task=get_task(db,task_id)
    action=payload.action.strip().upper()
    if action not in {"CONFIRMED","EDITED","REJECTED","NEEDS_CLARIFICATION"}:
        raise HTTPException(400,"Invalid verification action")
    if action=="EDITED" and payload.verified_value is None:
        raise HTTPException(400,"verified_value is required for EDITED")
    # Industrial Knowledge candidates/conflicts are finalized only through this user decision.
    knowledge_assertion_id = None
    knowledge_conflict_id = None
    if task.notes:
        import re
        if task.reason == "KNOWLEDGE_EXTRACTION":
            m = re.search(r"knowledge_assertion_id=(\d+)", task.notes)
            if m: knowledge_assertion_id = int(m.group(1))
        elif task.reason == "KNOWLEDGE_CONFLICT":
            m = re.search(r"knowledge_conflict_id=(\d+)", task.notes)
            if m: knowledge_conflict_id = int(m.group(1))
    if knowledge_conflict_id:
        from app.models.knowledge_conflict import KnowledgeConflict
        conflict = db.get(KnowledgeConflict, knowledge_conflict_id)
        if conflict:
            new_assertion = db.get(KnowledgeAssertion, conflict.assertion_id)
            old_assertion = db.get(KnowledgeAssertion, conflict.existing_assertion_id)
            if action == "CONFIRMED":
                if new_assertion: new_assertion.verification_status = "CONFIRMED"; new_assertion.updated_at = now()
                if old_assertion: old_assertion.verification_status = "REJECTED"; old_assertion.updated_at = now()
                conflict.status = "RESOLVED"; conflict.resolution = "ACCEPT_NEW"
            elif action == "EDITED":
                if not payload.verified_value: raise HTTPException(400,"verified_value is required")
                if new_assertion:
                    new_assertion.object_text = payload.verified_value.strip(); new_assertion.verification_status = "CONFIRMED"; new_assertion.updated_at = now()
                if old_assertion: old_assertion.verification_status = "REJECTED"; old_assertion.updated_at = now()
                conflict.status = "RESOLVED"; conflict.resolution = "EDIT_AND_ACCEPT"
            elif action == "REJECTED":
                if new_assertion: new_assertion.verification_status = "REJECTED"; new_assertion.updated_at = now()
                conflict.status = "RESOLVED"; conflict.resolution = "KEEP_EXISTING"
            else:
                conflict.status = "NEEDS_CLARIFICATION"; conflict.resolution = payload.notes or "Needs clarification"
            conflict.updated_at = now()

    if knowledge_assertion_id:
        assertion = db.get(KnowledgeAssertion, knowledge_assertion_id)
        if assertion:
            if action in {"CONFIRMED", "EDITED"}:
                if payload.verified_value is not None:
                    assertion.object_text = payload.verified_value.strip()
                assertion.verification_status = "CONFIRMED"
            elif action == "REJECTED":
                assertion.verification_status = "REJECTED"
            else:
                assertion.verification_status = "NEEDS_CLARIFICATION"
            assertion.updated_at = now()

    task.status=action
    task.verified_value=payload.verified_value if action in {"CONFIRMED","EDITED"} else None
    task.notes=payload.notes
    task.verified_at=now()

    # Apply only user-confirmed/edited values to authoritative RFQ/RFQ Line fields.
    if action in {"CONFIRMED","EDITED"} and payload.verified_value is not None:
        value=payload.verified_value.strip()
        rfq=db.get(RFQ, task.rfq_id) if task.rfq_id else None
        line=db.get(RFQLine, task.rfq_line_id) if task.rfq_line_id else None
        rfq_fields={"customer_rfq_number","title","currency","delivery_location","incoterm"}
        if rfq and task.field_name in rfq_fields:
            setattr(rfq, task.field_name, value)
            rfq.updated_at=now()
        elif rfq and task.field_name in {"request_date","required_date"}:
            parsed=None
            for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%Y/%m/%d"):
                try: parsed=datetime.strptime(value,fmt).date(); break
                except ValueError: pass
            if parsed is None: raise HTTPException(400,"Invalid date format; use YYYY-MM-DD")
            setattr(rfq, task.field_name, parsed); rfq.updated_at=now()
        elif line:
            if task.field_name in {"description_original","description_normalized","manufacturer","customer_part_number","unit","documents_required","technical_requirements","delivery_requirement","notes"}:
                setattr(line, task.field_name, value)
            elif task.field_name=="quantity":
                try: line.quantity=Decimal(value.replace(",",""))
                except InvalidOperation: raise HTTPException(400,"Invalid quantity")
            elif task.field_name=="condition":
                normalized=value.upper()
                if normalized not in CONDITIONS: raise HTTPException(400,"Invalid condition")
                line.condition_required=normalized; line.condition_source="USER"
            line.updated_at=now()

    if task.rfq_line_id:
        line_tasks=list(db.scalars(select(VerificationTask).where(VerificationTask.rfq_line_id==task.rfq_line_id)).all())
        statuses={x.status for x in line_tasks}
        line=db.get(RFQLine,task.rfq_line_id)
        if line:
            if "NEEDS_CLARIFICATION" in statuses: line.verification_status="NEEDS_CLARIFICATION"
            elif "REJECTED" in statuses: line.verification_status="REJECTED"
            elif line_tasks and all(x.status in {"CONFIRMED","EDITED"} for x in line_tasks): line.verification_status="CONFIRMED"
            else: line.verification_status="PENDING"
            line.updated_at=now()

    db.commit(); db.refresh(task); return task

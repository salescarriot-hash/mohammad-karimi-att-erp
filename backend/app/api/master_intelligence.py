from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.rfq import RFQ, RFQLine
from app.models.master import Part, EquipmentModel
from app.models.part_context import PartApplication, PartRelation
from app.models.verification import VerificationTask
from app.services.master_intelligence import equipment_candidates, part_candidates, context

router = APIRouter(prefix="/master-intelligence", tags=["Advanced Master Intelligence"])

def now(): return datetime.now(timezone.utc)

@router.get("/rfq-lines/{line_id}")
def intelligence_for_line(line_id: int, db: Session = Depends(get_db)):
    line = db.get(RFQLine, line_id)
    if not line: raise HTTPException(404, "RFQ line not found")
    warnings = []
    if not line.part_id: warnings.append("No confirmed Part is linked to this line.")
    if not line.equipment_model_id: warnings.append("No confirmed Equipment Model is linked to this line.")
    if line.part_id and line.equipment_model_id:
        confirmed = db.scalar(select(PartApplication).where(
            PartApplication.part_id == line.part_id,
            PartApplication.equipment_model_id == line.equipment_model_id,
            PartApplication.verification_status == "CONFIRMED"
        ))
        if not confirmed:
            warnings.append("Selected Part/Application relationship is not confirmed.")
    return {
        "rfq_line_id": line.id,
        "current": {"part_id": line.part_id, "equipment_model_id": line.equipment_model_id,
                    "manufacturer": line.manufacturer, "customer_part_number": line.customer_part_number},
        "part_candidates": part_candidates(db, line),
        "equipment_candidates": equipment_candidates(db, line),
        "selected_part_context": context(db, line.part_id) if line.part_id else None,
        "warnings": warnings,
        "needs_confirmation": True,
    }

@router.get("/parts/{part_id}/context")
def part_master_context(part_id: int, db: Session = Depends(get_db)):
    data = context(db, part_id)
    if not data: raise HTTPException(404, "Part not found")
    return data

@router.post("/rfq-lines/{line_id}/confirm-application")
def confirm_application(line_id: int, equipment_model_id: int, notes: str | None = None, db: Session = Depends(get_db)):
    line = db.get(RFQLine, line_id)
    em = db.get(EquipmentModel, equipment_model_id)
    if not line or not em: raise HTTPException(404, "RFQ line or Equipment Model not found")
    if not line.part_id: raise HTTPException(400, "A confirmed Part is required before confirming application")
    existing = db.scalar(select(PartApplication).where(PartApplication.part_id == line.part_id, PartApplication.equipment_model_id == equipment_model_id))
    if existing:
        existing.verification_status = "CONFIRMED"; existing.updated_at = now(); existing.source = "USER_CONFIRMED_FROM_RFQ"
    else:
        existing = PartApplication(part_id=line.part_id, equipment_model_id=equipment_model_id, application_notes=notes,
                                   source="USER_CONFIRMED_FROM_RFQ", verification_status="CONFIRMED", created_at=now(), updated_at=now())
        db.add(existing)
    db.add(VerificationTask(case_id=db.scalar(select(RFQ.case_id).where(RFQ.id == line.rfq_id)), rfq_id=line.rfq_id,
        rfq_line_id=line.id, field_name="part_application", current_value=str(line.part_id), requested_value=str(equipment_model_id),
        reason="MASTER_CONTEXT_REVIEW", status="CONFIRMED", verified_value=str(equipment_model_id), verified_at=now(),
        notes=notes, created_at=now(), updated_at=now()))
    db.commit()
    return {"status":"CONFIRMED", "part_id":line.part_id, "equipment_model_id":equipment_model_id}

@router.post("/rfq-lines/{line_id}/confirm-relation")
def confirm_relation(line_id: int, related_part_id: int, relation_type: str, notes: str | None = None, db: Session = Depends(get_db)):
    line = db.get(RFQLine, line_id)
    related = db.get(Part, related_part_id)
    if not line or not related: raise HTTPException(404, "RFQ line or related Part not found")
    if not line.part_id: raise HTTPException(400, "A confirmed Part is required")
    if line.part_id == related_part_id: raise HTTPException(400, "Self relation is not allowed")
    allowed = {"ALTERNATE", "EQUIVALENT", "SUBSTITUTE", "SUPERSEDES"}
    if relation_type not in allowed: raise HTTPException(400, "Unsupported relation type")
    existing = db.scalar(select(PartRelation).where(PartRelation.part_id == line.part_id, PartRelation.related_part_id == related_part_id, PartRelation.relation_type == relation_type))
    if existing:
        existing.verification_status="CONFIRMED"; existing.updated_at=now(); existing.source="USER_CONFIRMED_FROM_RFQ"
    else:
        db.add(PartRelation(part_id=line.part_id, related_part_id=related_part_id, relation_type=relation_type,
                            source="USER_CONFIRMED_FROM_RFQ", notes=notes, verification_status="CONFIRMED", created_at=now(), updated_at=now()))
    case_id = db.scalar(select(RFQ.case_id).where(RFQ.id == line.rfq_id))
    db.add(VerificationTask(case_id=case_id, rfq_id=line.rfq_id, rfq_line_id=line.id,
        field_name=f"part_relation.{relation_type.lower()}", current_value=str(line.part_id), requested_value=str(related_part_id),
        reason="MASTER_CONTEXT_REVIEW", status="CONFIRMED", verified_value=str(related_part_id), verified_at=now(), notes=notes,
        created_at=now(), updated_at=now()))
    db.commit()
    return {"status":"CONFIRMED", "part_id":line.part_id, "related_part_id":related_part_id, "relation_type":relation_type}

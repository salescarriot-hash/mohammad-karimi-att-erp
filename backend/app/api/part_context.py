from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.rfq import RFQLine
from app.models.master import Part, EquipmentModel
from app.models.part_context import PartApplication, PartRelation
from app.schemas.part_context import PartContextOut

router = APIRouter(prefix="/part-context", tags=["Part Application & Technical Context"])

@router.get("/rfq-lines/{line_id}", response_model=PartContextOut)
def get_part_context(line_id: int, db: Session = Depends(get_db)):
    line = db.get(RFQLine, line_id)
    if not line:
        raise HTTPException(404, "RFQ line not found")
    part = db.get(Part, line.part_id) if line.part_id else None
    applications = []
    relations = []
    warnings = []

    if part:
        app_rows = db.scalars(select(PartApplication).where(PartApplication.part_id == part.id)).all()
        for a in app_rows:
            em = db.get(EquipmentModel, a.equipment_model_id)
            applications.append({
                "id": a.id, "equipment_model_id": a.equipment_model_id,
                "equipment_model": em.model if em else None,
                "equipment_type": em.equipment_type if em else None,
                "family": em.family if em else None,
                "application_notes": a.application_notes, "source": a.source,
                "verification_status": a.verification_status,
            })
        rel_rows = db.scalars(select(PartRelation).where(PartRelation.part_id == part.id)).all()
        for r in rel_rows:
            rp = db.get(Part, r.related_part_id)
            relations.append({
                "id": r.id, "related_part_id": r.related_part_id,
                "related_part_number": rp.part_number if rp else None,
                "related_description": rp.description if rp else None,
                "relation_type": r.relation_type, "source": r.source,
                "notes": r.notes, "verification_status": r.verification_status,
            })
        if not applications:
            warnings.append("No confirmed part application was found in Master Data.")
        if any(a["verification_status"] != "CONFIRMED" for a in applications):
            warnings.append("One or more application records are not confirmed.")
        if any(r["verification_status"] != "CONFIRMED" for r in relations):
            warnings.append("One or more alternate/equivalent relations are not confirmed.")
    else:
        warnings.append("No confirmed Part is linked to this RFQ line yet.")

    # If RFQ line already has an equipment model, check whether the selected part is documented for it.
    if part and line.equipment_model_id:
        matching = [a for a in applications if a["equipment_model_id"] == line.equipment_model_id]
        if not matching:
            em = db.get(EquipmentModel, line.equipment_model_id)
            warnings.append(f"Part application for selected equipment model '{em.model if em else line.equipment_model_id}' was not found.")
        elif not any(a["verification_status"] == "CONFIRMED" for a in matching):
            warnings.append("The Part/Application match for the selected equipment model is not confirmed.")

    return {
        "rfq_line_id": line.id,
        "part_id": part.id if part else None,
        "part_number": part.part_number if part else line.customer_part_number,
        "part_description": part.description if part else line.description_normalized or line.description_original,
        "applications": applications,
        "relations": relations,
        "warnings": warnings,
        "needs_confirmation": bool(warnings) or any(x["verification_status"] != "CONFIRMED" for x in applications + relations),
    }

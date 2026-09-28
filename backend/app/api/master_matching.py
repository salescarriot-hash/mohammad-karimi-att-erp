from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.rfq import RFQ, RFQLine
from app.models.verification import VerificationTask
from app.schemas.master_matching import MatchResult, MatchDecision
from app.services.master_matching import match_line

router=APIRouter(prefix="/master-matching",tags=["Master Matching"])

def now(): return datetime.now(timezone.utc)

@router.get("/rfq-lines/{line_id}",response_model=MatchResult)
def match_rfq_line(line_id:int,db:Session=Depends(get_db)):
    line=db.get(RFQLine,line_id)
    if not line: raise HTTPException(404,"RFQ line not found")
    candidates=match_line(db,line)
    return {"rfq_line_id":line.id,"input":{"manufacturer":line.manufacturer,"customer_part_number":line.customer_part_number,"description":line.description_normalized or line.description_original,"equipment_model_id":line.equipment_model_id,"part_id":line.part_id},"candidates":candidates,"needs_confirmation":True}

@router.post("/rfq-lines/{line_id}/decision",response_model=dict)
def decide_match(line_id:int,payload:MatchDecision,db:Session=Depends(get_db)):
    line=db.get(RFQLine,line_id)
    if not line: raise HTTPException(404,"RFQ line not found")
    if payload.entity_type not in {"PART","EQUIPMENT_MODEL","MANUFACTURER"}: raise HTTPException(400,"Unsupported entity type")
    rfq=db.get(RFQ,line.rfq_id)
    if not rfq: raise HTTPException(404,"RFQ not found")
    if payload.entity_type=="PART": line.part_id=payload.entity_id
    elif payload.entity_type=="EQUIPMENT_MODEL": line.equipment_model_id=payload.entity_id
    elif payload.entity_type=="MANUFACTURER":
        from app.models.master import Manufacturer
        m=db.get(Manufacturer,payload.entity_id)
        if not m: raise HTTPException(404,"Manufacturer not found")
        line.manufacturer=m.name
    task=VerificationTask(case_id=rfq.case_id,rfq_id=line.rfq_id,rfq_line_id=line.id,field_name=f"master_match.{payload.entity_type.lower()}",current_value=str(payload.entity_id),requested_value=str(payload.entity_id),reason="MASTER_MATCH_REVIEW",status="CONFIRMED",verified_value=str(payload.entity_id),verified_at=now(),notes=payload.notes,created_at=now(),updated_at=now())
    db.add(task); line.verification_status="CONFIRMED"; line.updated_at=now(); db.commit()
    return {"status":"CONFIRMED","rfq_line_id":line.id,"entity_type":payload.entity_type,"entity_id":payload.entity_id}

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.rfq import RFQ, RFQLine
from app.models.supplier import Supplier, SupplierQuote
from app.models.supplier_performance import SupplierOutreach
from app.services.supplier_rfq_template_engine import render_supplier_rfq

router = APIRouter(prefix="/supplier-rfq-workflow", tags=["Supplier RFQ Workflow"])
ROOT = Path(__file__).resolve().parents[3]
GENERATED = ROOT / "storage" / "generated" / "supplier-rfq"
TEMPLATE_DIR = ROOT / "storage" / "templates" / "supplier-rfq"
META = TEMPLATE_DIR / "templates.json"
GENERATED.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

class PreparePayload(BaseModel):
    supplier_ids: list[int] = Field(min_length=1)
    template_id: str | None = None
    channel: str = "EMAIL"

class MarkSentPayload(BaseModel):
    channel: str | None = None
    sent_at: datetime | None = None
    notes: str | None = None

class ResponsePayload(BaseModel):
    response_at: datetime | None = None
    status: str = "RESPONDED"
    responded_line_count: int | None = None
    quote_id: int | None = None
    notes: str | None = None

def _templates():
    if not META.exists(): return []
    try: return json.loads(META.read_text(encoding="utf-8"))
    except Exception: return []

def _template(template_id: str | None):
    rows = _templates()
    row = next((x for x in rows if x.get("id") == template_id), None) if template_id else next((x for x in rows if x.get("active")), None)
    if not row: raise HTTPException(400, "No active Supplier RFQ template is configured")
    path = ROOT / row["path"]
    if not path.exists(): raise HTTPException(404, "Supplier RFQ template file is missing")
    return row, path

def _serialize(row, supplier, rfq, generated_path=None):
    return {"id": row.id, "supplier_id": row.supplier_id, "supplier_name": supplier.name_en or supplier.name, "rfq_id": row.rfq_id, "status": row.status, "channel": row.channel, "sent_at": row.sent_at, "response_at": row.response_at, "requested_line_count": row.requested_line_count, "responded_line_count": row.responded_line_count, "notes": row.notes, "generated_file": str(generated_path.relative_to(ROOT)) if generated_path and generated_path.exists() else None}

@router.post("/rfqs/{rfq_id}/prepare", response_model=list[dict])
def prepare_supplier_rfqs(rfq_id: int, payload: PreparePayload, db: Session = Depends(get_db)):
    rfq = db.get(RFQ, rfq_id)
    if not rfq: raise HTTPException(404, "RFQ not found")
    template_row, template_path = _template(payload.template_id)
    lines = db.scalars(select(RFQLine).where(RFQLine.rfq_id == rfq_id).order_by(RFQLine.line_number)).all()
    if not lines: raise HTTPException(400, "RFQ has no lines")
    out=[]; now=datetime.now(timezone.utc)
    for supplier_id in dict.fromkeys(payload.supplier_ids):
        supplier=db.get(Supplier,supplier_id)
        if not supplier: raise HTTPException(404, f"Supplier {supplier_id} not found")
        existing=db.scalar(select(SupplierOutreach).where(SupplierOutreach.rfq_id==rfq_id, SupplierOutreach.supplier_id==supplier_id, SupplierOutreach.status.in_(["READY","SENT","PARTIAL","RESPONDED"])).order_by(SupplierOutreach.created_at.desc()))
        if existing:
            raise HTTPException(409, f"An active supplier RFQ already exists for supplier {supplier_id} and RFQ {rfq_id}")
        row=SupplierOutreach(supplier_id=supplier_id,rfq_id=rfq_id,status="READY",channel=payload.channel,requested_line_count=len(lines),created_at=now,updated_at=now,notes=f"Generated from template {template_row['id']}")
        db.add(row); db.flush()
        outpath=GENERATED/f"RFQ-{rfq.id}-SUP-{supplier.id}-OUTREACH-{row.id}{template_path.suffix}"
        render_supplier_rfq(template_path,outpath,rfq,supplier,lines)
        out.append(_serialize(row,supplier,rfq,outpath))
    db.commit()
    return out

@router.get("/rfqs/{rfq_id}", response_model=list[dict])
def list_supplier_rfqs(rfq_id:int, db:Session=Depends(get_db)):
    rows=db.scalars(select(SupplierOutreach).where(SupplierOutreach.rfq_id==rfq_id).order_by(SupplierOutreach.created_at.desc())).all()
    result=[]
    for row in rows:
        supplier=db.get(Supplier,row.supplier_id)
        result.append(_serialize(row,supplier,db.get(RFQ,rfq_id)))
    return result

@router.post("/outreach/{outreach_id}/mark-sent", response_model=dict)
def mark_sent(outreach_id:int,payload:MarkSentPayload,db:Session=Depends(get_db)):
    row=db.get(SupplierOutreach,outreach_id)
    if not row: raise HTTPException(404,"Supplier outreach not found")
    if row.status not in {"READY","DRAFT"}: raise HTTPException(409,"Only READY/DRAFT outreach can be marked as sent")
    row.status="SENT"; row.sent_at=payload.sent_at or datetime.now(timezone.utc); row.channel=payload.channel or row.channel; row.notes=payload.notes or row.notes; row.updated_at=datetime.now(timezone.utc)
    db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"sent_at":row.sent_at}

@router.post("/outreach/{outreach_id}/response", response_model=dict)
def record_response(outreach_id:int,payload:ResponsePayload,db:Session=Depends(get_db)):
    row=db.get(SupplierOutreach,outreach_id)
    if not row: raise HTTPException(404,"Supplier outreach not found")
    if payload.status not in {"RESPONDED","PARTIAL","NO_QUOTE","DECLINED"}: raise HTTPException(400,"Invalid response status")
    if payload.quote_id is not None:
        quote=db.get(SupplierQuote,payload.quote_id)
        if not quote: raise HTTPException(404,"Supplier quote not found")
        if quote.supplier_id!=row.supplier_id or quote.rfq_id!=row.rfq_id: raise HTTPException(400,"Quote does not belong to this supplier outreach")
    row.status=payload.status; row.response_at=payload.response_at or datetime.now(timezone.utc); row.responded_line_count=payload.responded_line_count; row.updated_at=datetime.now(timezone.utc)
    if payload.notes: row.notes=payload.notes
    db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"response_at":row.response_at,"quote_id":payload.quote_id}

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.quotation import Quotation, QuotationLine
from app.models.customer import Customer, CustomerContact
from app.services.template_engine import inspect_template, render_quotation

router = APIRouter(prefix="/templates", tags=["Template Engine"])
ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = ROOT / "storage" / "templates"
GENERATED = ROOT / "storage" / "generated"
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
GENERATED.mkdir(parents=True, exist_ok=True)
META = TEMPLATE_DIR / "quotation_templates.json"


def _load_meta():
    if not META.exists():
        return []
    try:
        return json.loads(META.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_meta(rows):
    META.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


@router.post("/quotation/upload", status_code=201)
async def upload_quotation_template(file: UploadFile = File(...)):
    name = file.filename or "quotation_template.docx"
    if not name.lower().endswith(".docx"):
        raise HTTPException(400, "Quotation template must be a .docx file")
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty template file")
    template_id = datetime.now(timezone.utc).strftime("tpl-%Y%m%d%H%M%S%f")
    safe_name = Path(name).name
    path = TEMPLATE_DIR / f"{template_id}.docx"
    path.write_bytes(content)
    try:
        inspection = inspect_template(path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(400, f"Invalid DOCX template: {exc}")
    rows = _load_meta()
    record = {"id": template_id, "name": safe_name, "path": str(path.relative_to(ROOT)), "uploaded_at": datetime.now(timezone.utc).isoformat(), "inspection": inspection, "active": False}
    rows.append(record)
    # First uploaded template becomes active only if there is no active template.
    if not any(x.get("active") for x in rows):
        record["active"] = True
    _save_meta(rows)
    return record


@router.get("/quotation")
def list_quotation_templates():
    return _load_meta()


@router.get("/quotation/{template_id}")
def get_quotation_template(template_id: str):
    row = next((x for x in _load_meta() if x["id"] == template_id), None)
    if not row:
        raise HTTPException(404, "Template not found")
    return row


@router.post("/quotation/{template_id}/activate")
def activate_quotation_template(template_id: str):
    rows = _load_meta()
    found = False
    for row in rows:
        if row["id"] == template_id:
            row["active"] = True; found = True
        else:
            row["active"] = False
    if not found:
        raise HTTPException(404, "Template not found")
    _save_meta(rows)
    return next(x for x in rows if x["id"] == template_id)


@router.post("/quotation/{template_id}/render/{quotation_id}")
def render_quotation_template(template_id: str, quotation_id: int, db: Session = Depends(get_db)):
    row = next((x for x in _load_meta() if x["id"] == template_id), None)
    if not row:
        raise HTTPException(404, "Template not found")
    q = db.get(Quotation, quotation_id)
    if not q:
        raise HTTPException(404, "Quotation not found")
    if q.status not in {"APPROVED", "SENT"}:
        raise HTTPException(409, "Customer quotation can only be rendered after approval")
    template_path = ROOT / row["path"]
    if not template_path.exists():
        raise HTTPException(404, "Template file is missing from storage")
    customer = db.get(Customer, q.customer_id)
    contact = db.get(CustomerContact, q.contact_id) if q.contact_id else None
    lines = db.scalars(select(QuotationLine).where(QuotationLine.quotation_id == q.id).order_by(QuotationLine.line_number)).all()
    out = GENERATED / f"{q.quotation_number}-{template_id}.docx"
    render_quotation(template_path, out, q, lines, customer, contact)
    q.source_template = row["id"]
    db.commit()
    return FileResponse(out, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=out.name)

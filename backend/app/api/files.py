from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.case import Case
from app.models.file import CaseFile
from app.schemas.file import DOCUMENT_TYPES, FileOut
from app.services.rfq_intake import build_preview

router = APIRouter(prefix="/cases/{case_id}/files", tags=["Files"])

def now():
    return datetime.now(timezone.utc)

def ensure_case(db: Session, case_id: int) -> Case:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

def safe_name(name: str) -> str:
    return Path(name).name or "uploaded_file"

@router.post("", response_model=FileOut, status_code=201)
async def upload_case_file(
    case_id: int,
    upload: UploadFile = File(...),
    document_type: str = Query(default="OTHER"),
    db: Session = Depends(get_db),
):
    ensure_case(db, case_id)
    document_type = document_type.upper()
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid document_type")

    original_name = safe_name(upload.filename or "uploaded_file")
    suffix = Path(original_name).suffix.lower()
    stored_name = f"{uuid4().hex}{suffix}"
    base = Path(settings.storage_path).resolve()
    case_dir = (base / "cases" / str(case_id)).resolve()
    case_dir.mkdir(parents=True, exist_ok=True)
    target = (case_dir / stored_name).resolve()
    if base not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid file path")

    with target.open("wb") as out:
        while chunk := await upload.read(1024 * 1024):
            out.write(chunk)
    await upload.close()

    relative_path = target.relative_to(base).as_posix()
    record = CaseFile(
        case_id=case_id,
        file_name=stored_name,
        original_file_name=original_name,
        document_type=document_type,
        file_type=upload.content_type,
        file_path=relative_path,
        uploaded_at=now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.get("", response_model=list[FileOut])
def list_case_files(case_id: int, document_type: str | None = Query(default=None),
                    limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    ensure_case(db, case_id)
    stmt = select(CaseFile).where(CaseFile.case_id == case_id)
    if document_type:
        document_type = document_type.upper()
        if document_type not in DOCUMENT_TYPES:
            raise HTTPException(status_code=400, detail="Invalid document_type")
        stmt = stmt.where(CaseFile.document_type == document_type)
    return list(db.scalars(stmt.order_by(CaseFile.id.desc()).limit(limit)).all())


@router.get("/{file_id}/preview")
def preview_case_file(case_id: int, file_id: int, db: Session = Depends(get_db)):
    ensure_case(db, case_id)
    record = db.scalar(select(CaseFile).where(CaseFile.id == file_id, CaseFile.case_id == case_id))
    if not record:
        raise HTTPException(status_code=404, detail="Case file not found")
    base = Path(settings.storage_path).resolve()
    path = (base / record.file_path).resolve()
    if base not in path.parents or not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return build_preview(record.original_file_name, path.read_bytes())


@router.post("/{file_id}/classify")
def classify_case_file(case_id: int, file_id: int, db: Session = Depends(get_db)):
    ensure_case(db, case_id)
    record = db.scalar(select(CaseFile).where(CaseFile.id == file_id, CaseFile.case_id == case_id))
    if not record:
        raise HTTPException(status_code=404, detail="Case file not found")
    name = record.original_file_name.lower()
    current = record.document_type or "OTHER"
    suggestions = []
    if any(x in name for x in ["rfq", "request for quotation", "inquiry", "enquiry", "استعلام"]):
        suggestions.append(("RFQ", 0.92))
    if any(x in name for x in ["quote", "quotation", "offer", "proposal", "قیمت"]):
        suggestions.append(("SUPPLIER_QUOTE", 0.88))
    if any(x in name for x in ["nameplate", "plate", "پلاک", "مشخصات فنی"]):
        suggestions.append(("NAMEPLATE", 0.90))
    if any(x in name for x in ["datasheet", "data sheet", "spec", "technical", "دیتاشیت"]):
        suggestions.append(("TECHNICAL_DATASHEET", 0.86))
    if any(x in name for x in ["po", "purchase order", "سفارش خرید"]):
        suggestions.append(("CUSTOMER_PO", 0.90))
    if any(x in name for x in ["email", "mail", "نامه"]):
        suggestions.append(("CUSTOMER_EMAIL", 0.82))
    if not suggestions:
        suggestions.append((current, 0.50))
    suggestions.sort(key=lambda x: x[1], reverse=True)
    return {"file_id": record.id, "current_type": current, "suggestions": [{"document_type": t, "confidence": c, "source": "filename"} for t,c in suggestions], "requires_user_confirmation": True}


@router.post("/{file_id}/set-type")
def set_case_file_type(case_id: int, file_id: int, document_type: str = Query(...), db: Session = Depends(get_db)):
    ensure_case(db, case_id)
    record = db.scalar(select(CaseFile).where(CaseFile.id == file_id, CaseFile.case_id == case_id))
    if not record:
        raise HTTPException(status_code=404, detail="Case file not found")
    document_type = document_type.upper()
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid document_type")
    record.document_type = document_type
    db.commit(); db.refresh(record)
    return record

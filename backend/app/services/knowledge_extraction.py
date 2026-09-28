from __future__ import annotations
import re
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.models.file import CaseFile
from app.models.knowledge import KnowledgeAssertion
from app.models.knowledge_conflict import KnowledgeConflict
from app.models.verification import VerificationTask
from datetime import datetime, timezone
from app.services.rfq_intake import extract_text
from app.services.industrial_knowledge import _score

FIELD_PATTERNS = {
    "manufacturer": [r"(?:manufacturer|maker|brand)\s*[:=]\s*([^\n;]+)"],
    "model": [r"(?:model|type)\s*[:=]\s*([^\n;]+)"],
    "part_number": [r"(?:part\s*(?:no|number)|p/?n|pn)\s*[:=]\s*([A-Z0-9][A-Z0-9._/-]{2,})"],
    "serial_number": [r"(?:serial\s*(?:no|number)|s/?n)\s*[:=]\s*([^\n;]+)"],
    "tag_number": [r"(?:tag\s*(?:no|number)|tag)\s*[:=]\s*([^\n;]+)"],
    "revision": [r"(?:revision|rev)\s*[:=]\s*([^\n;]+)"],
    "power": [r"(?:power)\s*[:=]\s*([^\n;]+)"],
    "voltage": [r"(?:voltage|volt)\s*[:=]\s*([^\n;]+)"],
    "frequency": [r"(?:frequency|freq)\s*[:=]\s*([^\n;]+)"],
}

PREDICATES = {
    "manufacturer": "MANUFACTURED_BY", "model": "HAS_MODEL", "part_number": "HAS_PART_NUMBER",
    "serial_number": "HAS_SERIAL_NUMBER", "tag_number": "HAS_TAG_NUMBER", "revision": "HAS_REVISION",
    "power": "HAS_POWER", "voltage": "HAS_VOLTAGE", "frequency": "HAS_FREQUENCY",
}

def _read_file(record: CaseFile) -> str:
    base = Path(settings.storage_path).resolve()
    path = (base / record.file_path).resolve()
    if base not in path.parents or not path.exists():
        return ""
    try:
        text, _method, _warnings = extract_text(record.original_file_name, path.read_bytes())
        return text
    except Exception:
        return ""

def extract_file_knowledge(db: Session, file_id: int) -> dict:
    record = db.get(CaseFile, file_id)
    if not record:
        return {"error": "File not found"}
    text = _read_file(record)
    if not text:
        return {"file_id": file_id, "document_type": record.document_type, "assertions": [], "warning": "No usable text. OCR/AI adapter is required for scanned/image files."}
    candidates = []
    for field, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.I)
            if m:
                value = m.group(1).strip().strip('"\'')
                if value:
                    candidates.append((field, value, 0.88))
                    break
    # Common turbine/model mentions even when the document has no explicit Model: label.
    if not any(f == "model" for f, _, _ in candidates):
        m = re.search(r"\b(SGT[- ]?(?:400|600|800)|V94\.[23]|Frame\s*[569]|701[BD])\b", text, flags=re.I)
        if m:
            candidates.append(("model", m.group(1).strip(), 0.78))
    created = []
    for field, value, confidence in candidates:
        pred = PREDICATES[field]
        existing = db.scalar(select(KnowledgeAssertion).where(
            KnowledgeAssertion.source_file_id == record.id,
            KnowledgeAssertion.predicate == pred,
            KnowledgeAssertion.object_text == value
        ))
        if existing:
            continue
        a = KnowledgeAssertion(
            subject_type="DOCUMENT", subject_id=record.id, subject_label=record.original_file_name,
            predicate=pred, object_type="TEXT", object_text=value,
            source_file_id=record.id, source="DOCUMENT_EXTRACTION",
            evidence_text=value, confidence=confidence, verification_status="PENDING"
        )
        db.add(a); created.append(a)
    db.flush()
    # Compare new candidates with already CONFIRMED knowledge. Never overwrite it.
    conflicts = []
    for a in created:
        existing = db.scalars(select(KnowledgeAssertion).where(
            KnowledgeAssertion.predicate == a.predicate,
            KnowledgeAssertion.verification_status == "CONFIRMED",
            KnowledgeAssertion.source_file_id != record.id,
            KnowledgeAssertion.object_text.is_not(None),
            KnowledgeAssertion.object_text != a.object_text
        ).order_by(KnowledgeAssertion.id.desc())).all()
        for old in existing:
            duplicate_conflict = db.scalar(select(KnowledgeConflict).where(
                KnowledgeConflict.assertion_id == a.id,
                KnowledgeConflict.existing_assertion_id == old.id,
                KnowledgeConflict.status == "PENDING"
            ))
            if duplicate_conflict:
                continue
            c = KnowledgeConflict(
                assertion_id=a.id, existing_assertion_id=old.id,
                field_name=next((k for k,v in PREDICATES.items() if v == a.predicate), a.predicate),
                current_value=old.object_text, new_value=a.object_text,
                status="PENDING", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
            )
            db.add(c); conflicts.append(c)
            break
    # Every detected conflict gets a Verification Center task.
    for c in conflicts:
        marker = f"knowledge_conflict_id={c.id}"
        existing_task = db.query(VerificationTask).filter(
            VerificationTask.reason == "KNOWLEDGE_CONFLICT", VerificationTask.notes.like(f"%{marker}%")
        ).first()
        if not existing_task:
            db.add(VerificationTask(
                case_id=record.case_id, field_name=c.field_name, current_value=c.current_value, requested_value=c.new_value,
                reason="KNOWLEDGE_CONFLICT", status="PENDING", source_file_id=record.id, extracted_value=c.new_value,
                confidence=next((a.confidence for a in created if a.id == c.assertion_id), None),
                notes=f"{marker}; existing_assertion_id={c.existing_assertion_id}",
                created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
            ))
    db.commit()
    return {"file_id": file_id, "document_type": record.document_type, "assertions": [
        {"id": a.id, "field": next((k for k,v in PREDICATES.items() if v == a.predicate), a.predicate), "predicate": a.predicate,
         "value": a.object_text, "confidence": float(a.confidence or 0), "status": a.verification_status,
         "source": a.source, "evidence": a.evidence_text} for a in created
    ], "conflicts": [{"id": c.id, "field": c.field_name, "current_value": c.current_value, "new_value": c.new_value, "status": c.status} for c in conflicts], "needs_user_confirmation": True}

def file_assertions(db: Session, file_id: int) -> list[dict]:
    rows = db.scalars(select(KnowledgeAssertion).where(KnowledgeAssertion.source_file_id == file_id).order_by(KnowledgeAssertion.id.desc())).all()
    return [{"id": r.id, "subject": r.subject_label, "predicate": r.predicate, "value": r.object_label or r.object_text,
             "confidence": float(r.confidence or 0), "status": r.verification_status, "source": r.source, "evidence": r.evidence_text} for r in rows]

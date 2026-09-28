from __future__ import annotations
from dataclasses import dataclass
import re
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.models.master import Manufacturer, EquipmentModel, Part
from app.models.part_context import PartApplication, PartRelation
from app.models.knowledge import KnowledgeAssertion
from app.models.rfq import RFQLine
from app.models.file import CaseFile

@dataclass
class KnowledgeCandidate:
    subject_type: str
    subject_id: int | None
    subject_label: str
    predicate: str
    object_type: str | None
    object_id: int | None
    object_label: str | None
    confidence: float
    source: str
    verification_status: str = "PENDING"

def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

def _score(a: str | None, b: str | None) -> float:
    aa, bb = _norm(a), _norm(b)
    if not aa or not bb: return 0.0
    if aa == bb: return 1.0
    if aa in bb or bb in aa: return 0.88
    common = sum(1 for token in re.findall(r"[a-z0-9]+", (a or "").lower()) if token in (b or "").lower())
    return min(0.82, 0.45 + common * 0.12) if common else 0.0

def rfq_line_candidates(db: Session, line: RFQLine) -> dict:
    candidates: list[KnowledgeCandidate] = []
    if line.customer_part_number:
        parts = db.scalars(select(Part)).all()
        for p in parts:
            score = max(_score(line.customer_part_number, p.part_number), _score(line.description_original, p.description) * 0.85)
            if score >= 0.55:
                candidates.append(KnowledgeCandidate("PART", p.id, p.part_number, "MATCHES_RFQ_LINE", "RFQ_LINE", line.id, f"Line {line.line_number}", round(score,4), "MASTER_DATA+RFQ"))
    if line.equipment_model_id:
        em = db.get(EquipmentModel, line.equipment_model_id)
        if em:
            candidates.append(KnowledgeCandidate("RFQ_LINE", line.id, f"Line {line.line_number}", "REFERS_TO_EQUIPMENT_MODEL", "EQUIPMENT_MODEL", em.id, em.model, 1.0, "RFQ_MASTER"))
    elif line.description_original:
        for em in db.scalars(select(EquipmentModel)).all():
            score = _score(line.description_original, em.model)
            if score >= 0.75:
                candidates.append(KnowledgeCandidate("RFQ_LINE", line.id, f"Line {line.line_number}", "POSSIBLY_REFERS_TO_EQUIPMENT_MODEL", "EQUIPMENT_MODEL", em.id, em.model, round(score,4), "DESCRIPTION_MATCH"))
    return {"candidates": [c.__dict__ for c in sorted(candidates, key=lambda x: x.confidence, reverse=True)], "needs_user_confirmation": True}

def part_graph(db: Session, part_id: int) -> dict:
    part = db.get(Part, part_id)
    if not part: return {"part": None, "nodes": [], "edges": []}
    nodes = [{"type":"PART","id":part.id,"label":part.part_number,"status":part.verification_status}]
    edges = []
    apps = db.scalars(select(PartApplication).where(PartApplication.part_id == part_id)).all()
    for a in apps:
        em = db.get(EquipmentModel, a.equipment_model_id)
        if em:
            nodes.append({"type":"EQUIPMENT_MODEL","id":em.id,"label":em.model,"status":"MASTER"})
            edges.append({"from_type":"PART","from_id":part.id,"predicate":"APPLIES_TO","to_type":"EQUIPMENT_MODEL","to_id":em.id,"verification_status":a.verification_status,"source":a.source})
    rels = db.scalars(select(PartRelation).where(or_(PartRelation.part_id == part_id, PartRelation.related_part_id == part_id))).all()
    for r in rels:
        other_id = r.related_part_id if r.part_id == part_id else r.part_id
        other = db.get(Part, other_id)
        if other:
            nodes.append({"type":"PART","id":other.id,"label":other.part_number,"status":other.verification_status})
            edges.append({"from_type":"PART","from_id":r.part_id,"predicate":r.relation_type,"to_type":"PART","to_id":r.related_part_id,"verification_status":r.verification_status,"source":r.source})
    assertions = db.scalars(select(KnowledgeAssertion).where(KnowledgeAssertion.subject_type == "PART", KnowledgeAssertion.subject_id == part_id)).all()
    for a in assertions:
        edges.append({"from_type":a.subject_type,"from_id":a.subject_id,"predicate":a.predicate,"to_type":a.object_type,"to_id":a.object_id,"to_label":a.object_label or a.object_text,"verification_status":a.verification_status,"confidence":float(a.confidence or 0),"source":a.source})
    return {"part":{"id":part.id,"part_number":part.part_number,"description":part.description},"nodes":nodes,"edges":edges}

def knowledge_search(db: Session, q: str, limit: int = 20) -> list[dict]:
    query = f"%{q.strip()}%"
    rows = db.scalars(select(KnowledgeAssertion).where(or_(KnowledgeAssertion.subject_label.ilike(query), KnowledgeAssertion.object_label.ilike(query), KnowledgeAssertion.object_text.ilike(query), KnowledgeAssertion.evidence_text.ilike(query))).limit(limit)).all()
    return [{"id":r.id,"subject":r.subject_label,"predicate":r.predicate,"object":r.object_label or r.object_text,"confidence":float(r.confidence or 0),"verification_status":r.verification_status,"source":r.source,"evidence":r.evidence_text} for r in rows]

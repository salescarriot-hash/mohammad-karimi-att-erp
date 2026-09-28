import re
from difflib import SequenceMatcher
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.master import Manufacturer, EquipmentModel, Part
from app.models.part_context import PartApplication, PartRelation
from app.models.rfq import RFQLine


def norm(v):
    if not v:
        return ""
    s = str(v).upper().strip()
    s = re.sub(r"[‐‑‒–—−]", "-", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.92
    return SequenceMatcher(None, a, b).ratio()


def equipment_candidates(db: Session, line: RFQLine):
    desc = line.description_normalized or line.description_original or ""
    out = []
    for em in db.scalars(select(EquipmentModel)).all():
        score = sim(desc, em.model)
        reasons = []
        if norm(em.model) == norm(desc):
            score = 1.0
            reasons.append("exact model/description")
        elif score >= .72:
            reasons.append("model/description similarity")
        if line.manufacturer and em.manufacturer_id:
            m = db.get(Manufacturer, em.manufacturer_id)
            ms = sim(line.manufacturer, m.name if m else "")
            if ms >= .90:
                score = min(1.0, score * .85 + ms * .15)
                reasons.append("manufacturer matches")
        if score >= .60:
            out.append((em, score, reasons))
    out.sort(key=lambda x: x[1], reverse=True)
    return [{"entity_type": "EQUIPMENT_MODEL", "entity_id": e.id, "display_name": e.model,
             "confidence": round(s, 4), "match_reasons": r, "source": "MASTER_DATA_CANDIDATE"}
            for e, s, r in out[:10]]


def part_candidates(db: Session, line: RFQLine):
    pn = line.customer_part_number
    desc = line.description_normalized or line.description_original or ""
    out = []
    for p in db.scalars(select(Part)).all():
        score_pn = sim(pn, p.part_number) if pn else 0.0
        score_desc = sim(desc, p.description or "") if desc else 0.0
        score = max(score_pn, score_desc * .82)
        reasons = []
        if pn and norm(p.part_number) == norm(pn):
            score = 1.0
            reasons.append("exact part number")
        elif score_pn >= .90:
            reasons.append("close part number")
        if desc and score_desc >= .75:
            reasons.append("description similarity")
        if line.manufacturer and p.manufacturer_id:
            m = db.get(Manufacturer, p.manufacturer_id)
            ms = sim(line.manufacturer, m.name if m else "")
            if ms >= .90:
                score = min(1.0, score * .88 + ms * .12)
                reasons.append("manufacturer matches")
        if score >= .62:
            out.append((p, score, reasons))
    out.sort(key=lambda x: x[1], reverse=True)
    return [{"entity_type": "PART", "entity_id": p.id, "display_name": p.part_number,
             "description": p.description, "confidence": round(s, 4),
             "match_reasons": r, "source": "MASTER_DATA_CANDIDATE"}
            for p, s, r in out[:15]]


def relation_candidates(db: Session, part_id: int):
    existing = db.scalars(select(PartRelation).where(PartRelation.part_id == part_id)).all()
    existing_ids = {r.related_part_id for r in existing}
    part = db.get(Part, part_id)
    if not part:
        return []
    out = []
    for p in db.scalars(select(Part).where(Part.id != part_id)).all():
        if p.id in existing_ids:
            continue
        score = max(sim(part.part_number, p.part_number), sim(part.description, p.description) * .85)
        if score >= .78:
            reasons = []
            if sim(part.part_number, p.part_number) >= .9:
                reasons.append("part-number similarity")
            if sim(part.description, p.description) >= .78:
                reasons.append("description similarity")
            if part.manufacturer_id and p.manufacturer_id and part.manufacturer_id == p.manufacturer_id:
                reasons.append("same manufacturer")
            out.append((p, score, reasons))
    out.sort(key=lambda x: x[1], reverse=True)
    return [{"related_part_id": p.id, "part_number": p.part_number, "description": p.description,
             "confidence": round(s, 4), "match_reasons": r, "relation_type": "UNCLASSIFIED_CANDIDATE"}
            for p, s, r in out[:15]]


def context(db: Session, part_id: int):
    part = db.get(Part, part_id)
    if not part:
        return None
    apps = db.scalars(select(PartApplication).where(PartApplication.part_id == part_id)).all()
    rels = db.scalars(select(PartRelation).where(PartRelation.part_id == part_id)).all()
    app_data = []
    for a in apps:
        em = db.get(EquipmentModel, a.equipment_model_id)
        app_data.append({"id": a.id, "equipment_model_id": a.equipment_model_id,
                         "equipment_model": em.model if em else None,
                         "verification_status": a.verification_status, "source": a.source,
                         "application_notes": a.application_notes})
    rel_data = []
    for r in rels:
        rp = db.get(Part, r.related_part_id)
        rel_data.append({"id": r.id, "related_part_id": r.related_part_id,
                         "part_number": rp.part_number if rp else None,
                         "relation_type": r.relation_type,
                         "verification_status": r.verification_status,
                         "source": r.source, "notes": r.notes})
    return {"part_id": part.id, "part_number": part.part_number,
            "description": part.description, "applications": app_data,
            "relations": rel_data, "relation_candidates": relation_candidates(db, part_id)}

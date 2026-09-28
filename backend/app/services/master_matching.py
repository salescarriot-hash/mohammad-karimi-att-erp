import re
from difflib import SequenceMatcher
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.master import Manufacturer, EquipmentModel, Part

def norm(v):
    if not v: return ""
    s=str(v).upper().strip()
    s=re.sub(r"[‐‑‒–—−]", "-", s)
    s=re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def similarity(a,b):
    a,b=norm(a),norm(b)
    if not a or not b:return 0.0
    if a==b:return 1.0
    if a in b or b in a:return 0.92
    return SequenceMatcher(None,a,b).ratio()

def manufacturer_candidates(db, value):
    q=norm(value)
    if not q:return []
    out=[]
    for x in db.scalars(select(Manufacturer)).all():
        vals=[x.name,x.name_en]+((x.aliases or "").split(","))
        score=max(similarity(q,v) for v in vals if v)
        reasons=[]
        if norm(x.name)==q or norm(x.name_en)==q: reasons.append("exact name")
        if score>=0.92: reasons.append("strong name/alias match")
        if score>=0.65: out.append((x,score,reasons))
    return sorted(out,key=lambda z:z[1],reverse=True)[:10]

def match_line(db,line):
    candidates=[]
    pn=line.customer_part_number
    manufacturer=line.manufacturer
    desc=line.description_normalized or line.description_original
    if pn:
        pnorm=norm(pn)
        for x in db.scalars(select(Part)).all():
            score=similarity(pnorm,x.part_number)
            reasons=[]
            if norm(x.part_number)==pnorm: reasons.append("exact part number")
            elif score>=.9: reasons.append("close part number")
            if manufacturer:
                m=db.get(Manufacturer,x.manufacturer_id) if x.manufacturer_id else None
                if m:
                    ms=similarity(manufacturer,m.name)
                    score=min(1.0,score*0.85+ms*0.15)
                    if ms>=.9: reasons.append("manufacturer matches")
            if score>=.65:
                candidates.append(("PART",x.id,x.part_number,score,reasons))
    if manufacturer:
        for x,score,reasons in manufacturer_candidates(db,manufacturer):
            candidates.append(("MANUFACTURER",x.id,x.name,score,reasons))
    if desc:
        for x in db.scalars(select(EquipmentModel)).all():
            score=similarity(desc,x.model)
            if score>=.72:
                candidates.append(("EQUIPMENT_MODEL",x.id,x.model,score,["description/model similarity"]))
    candidates.sort(key=lambda z:z[3],reverse=True)
    return [{"entity_type":a,"entity_id":b,"display_name":c,"confidence":round(d,4),"match_reasons":e,"source":"MASTER_DATA"} for a,b,c,d,e in candidates[:15]]

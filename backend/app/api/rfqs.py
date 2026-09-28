from datetime import date, datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.case import Case
from app.models.customer import Customer, CustomerSite
from app.models.rfq import RFQ, RFQLine
from app.models.file import CaseFile
from app.models.verification import VerificationTask
from app.schemas.rfq import RFQCreate, RFQOut, RFQUpdate, RFQLineCreate, RFQLineOut, RFQLineUpdate, RFQIntakePreview
from app.services.rfq_intake import build_preview
from app.config import settings
from decimal import Decimal, InvalidOperation

router=APIRouter(prefix="/cases/{case_id}/rfqs",tags=["RFQs"])
def now(): return datetime.now(timezone.utc)

def candidate_value(field: dict, *, normalized: bool = False):
    if normalized:
        return field.get("normalized_value") or field.get("translated_value") or field.get("value")
    return field.get("value")

def get_case(db,case_id):
    case=db.get(Case,case_id)
    if not case: raise HTTPException(404,"Case not found")
    return case

def get_rfq(db,case_id,rfq_id):
    obj=db.scalar(select(RFQ).where(RFQ.id==rfq_id,RFQ.case_id==case_id))
    if not obj: raise HTTPException(404,"RFQ not found")
    return obj

def validate_site(db,customer_id,site_id):
    if site_id is None:return
    site=db.get(CustomerSite,site_id)
    if not site or site.customer_id!=customer_id: raise HTTPException(400,"Site does not belong to this customer")

@router.post("",response_model=RFQOut,status_code=201)
def create_rfq(case_id:int,payload:RFQCreate,db:Session=Depends(get_db)):
    case=get_case(db,case_id); validate_site(db,case.customer_id,payload.site_id)
    obj=RFQ(case_id=case_id,customer_id=case.customer_id,**payload.model_dump(),created_at=now(),updated_at=now())
    db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("",response_model=list[RFQOut])
def list_rfqs(case_id:int,db:Session=Depends(get_db)):
    get_case(db,case_id)
    return list(db.scalars(select(RFQ).where(RFQ.case_id==case_id).order_by(RFQ.id.desc())).all())

@router.get("/{rfq_id}",response_model=RFQOut)
def read_rfq(case_id:int,rfq_id:int,db:Session=Depends(get_db)): return get_rfq(db,case_id,rfq_id)

@router.patch("/{rfq_id}",response_model=RFQOut)
def update_rfq(case_id:int,rfq_id:int,payload:RFQUpdate,db:Session=Depends(get_db)):
    obj=get_rfq(db,case_id,rfq_id); data=payload.model_dump(exclude_unset=True); validate_site(db,obj.customer_id,data.get("site_id",obj.site_id))
    for k,v in data.items(): setattr(obj,k,v)
    if obj.request_date and obj.required_date and obj.required_date<obj.request_date: raise HTTPException(400,"required_date cannot be before request_date")
    obj.updated_at=now(); db.commit(); db.refresh(obj); return obj

@router.get("/{rfq_id}/lines",response_model=list[RFQLineOut])
def list_lines(case_id:int,rfq_id:int,db:Session=Depends(get_db)):
    get_rfq(db,case_id,rfq_id); return list(db.scalars(select(RFQLine).where(RFQLine.rfq_id==rfq_id).order_by(RFQLine.line_number)).all())

@router.post("/{rfq_id}/lines",response_model=RFQLineOut,status_code=201)
def create_line(case_id:int,rfq_id:int,payload:RFQLineCreate,db:Session=Depends(get_db)):
    get_rfq(db,case_id,rfq_id)
    if db.scalar(select(RFQLine).where(RFQLine.rfq_id==rfq_id,RFQLine.line_number==payload.line_number)): raise HTTPException(409,"Line number already exists")
    obj=RFQLine(rfq_id=rfq_id,**payload.model_dump(),created_at=now(),updated_at=now()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.patch("/{rfq_id}/lines/{line_id}",response_model=RFQLineOut)
def update_line(case_id:int,rfq_id:int,line_id:int,payload:RFQLineUpdate,db:Session=Depends(get_db)):
    get_rfq(db,case_id,rfq_id); obj=db.scalar(select(RFQLine).where(RFQLine.id==line_id,RFQLine.rfq_id==rfq_id))
    if not obj: raise HTTPException(404,"RFQ line not found")
    data=payload.model_dump(exclude_unset=True)
    if "line_number" in data and data["line_number"]!=obj.line_number and db.scalar(select(RFQLine).where(RFQLine.rfq_id==rfq_id,RFQLine.line_number==data["line_number"])): raise HTTPException(409,"Line number already exists")
    for k,v in data.items(): setattr(obj,k,v)
    obj.updated_at=now(); db.commit(); db.refresh(obj); return obj

@router.post("/intake-preview",response_model=RFQIntakePreview)
async def intake_preview(case_id:int,upload:UploadFile=File(...),db:Session=Depends(get_db)):
    get_case(db,case_id)
    data=await upload.read(); await upload.close()
    if len(data)>25*1024*1024: raise HTTPException(413,"File exceeds 25 MB limit")
    return build_preview(Path(upload.filename or "uploaded_file").name,data)


@router.post("/intake-from-file/{file_id}", response_model=RFQIntakePreview)
def intake_from_file(case_id:int, file_id:int, db:Session=Depends(get_db)):
    get_case(db,case_id)
    case_file=db.scalar(select(CaseFile).where(CaseFile.id==file_id, CaseFile.case_id==case_id))
    if not case_file: raise HTTPException(404,"Case file not found")
    path=(Path(settings.storage_path) / case_file.file_path).resolve()
    base=Path(settings.storage_path).resolve()
    if base not in path.parents or not path.exists(): raise HTTPException(404,"Stored file is missing")
    return build_preview(case_file.original_file_name, path.read_bytes())

@router.post("/intake-from-file/{file_id}/verification-tasks", response_model=list[dict])
def create_intake_verification_tasks(case_id:int, file_id:int, db:Session=Depends(get_db)):
    get_case(db,case_id)
    case_file=db.scalar(select(CaseFile).where(CaseFile.id==file_id, CaseFile.case_id==case_id))
    if not case_file: raise HTTPException(404,"Case file not found")
    path=(Path(settings.storage_path) / case_file.file_path).resolve()
    base=Path(settings.storage_path).resolve()
    if base not in path.parents or not path.exists(): raise HTTPException(404,"Stored file is missing")
    preview=build_preview(case_file.original_file_name, path.read_bytes())
    created=[]
    for field in preview["fields"]:
        task=VerificationTask(case_id=case_id, field_name=field["field_name"], reason="AI_EXTRACTION_REVIEW", status="PENDING", source_file_id=file_id, extracted_value=field.get("value"), confidence=field.get("confidence"), created_at=now(), updated_at=now())
        db.add(task); created.append(task)
    db.commit()
    for task in created: db.refresh(task)
    return [{"id":t.id,"field_name":t.field_name,"extracted_value":t.extracted_value,"confidence":float(t.confidence) if t.confidence is not None else None,"status":t.status,"source_file_id":t.source_file_id} for t in created]

@router.post("/intake-from-file/{file_id}/create-draft", response_model=RFQOut, status_code=201)
def create_rfq_draft_from_file(case_id:int, file_id:int, db:Session=Depends(get_db)):
    """Create a non-authoritative RFQ draft from an uploaded document.
    Extracted values are copied into draft fields; uncertain RFQ lines remain PENDING.
    """
    case=get_case(db,case_id)
    case_file=db.scalar(select(CaseFile).where(CaseFile.id==file_id, CaseFile.case_id==case_id))
    if not case_file: raise HTTPException(404,"Case file not found")
    path=(Path(settings.storage_path) / case_file.file_path).resolve()
    base=Path(settings.storage_path).resolve()
    if base not in path.parents or not path.exists(): raise HTTPException(404,"Stored file is missing")
    preview=build_preview(case_file.original_file_name,path.read_bytes())
    if not preview["fields"] and not preview["lines"]:
        raise HTTPException(422, "No reliable RFQ data was extracted; RFQ draft was not created. Review the document layout or enter the RFQ manually.")
    values={x["field_name"]:candidate_value(x, normalized=True) for x in preview["fields"] if x.get("value")}
    obj=RFQ(case_id=case_id,customer_id=case.customer_id,
        customer_rfq_number=values.get("customer_rfq_number"), title=values.get("title"),
        currency=values.get("currency"), delivery_location=values.get("delivery_location"),
        incoterm=values.get("incoterm"), status="UNDER_REVIEW",
        notes=f"Draft created from file #{file_id}. Extracted values require user review.",
        created_at=now(),updated_at=now())
    db.add(obj); db.flush()
    for line in preview["lines"]:
        desc_field=next((f for f in line["fields"] if f["field_name"]=="description_original"),None)
        desc=desc_field.get("value") if desc_field else None
        normalized_desc=(desc_field.get("normalized_value") or desc_field.get("translated_value")) if desc_field else None
        qty=next((f["value"] for f in line["fields"] if f["field_name"]=="quantity"),None)
        try: qty_val=float(qty) if qty else None
        except Exception: qty_val=None
        db.add(RFQLine(rfq_id=obj.id,line_number=line["line_number"],description_original=desc,
            description_normalized=normalized_desc,
            quantity=qty_val,status="NEW",verification_status="PENDING",
            condition_required="NEW",condition_source="DEFAULT_RULE",created_at=now(),updated_at=now()))
    db.commit(); db.refresh(obj)
    return obj


@router.post("/intake-from-file/{file_id}/start", response_model=dict, status_code=201)
def start_rfq_intake_workflow(case_id:int, file_id:int, db:Session=Depends(get_db)):
    """Run RFQ intake as a reviewable workflow: create draft RFQ/lines and linked verification tasks."""
    case=get_case(db,case_id)
    case_file=db.scalar(select(CaseFile).where(CaseFile.id==file_id, CaseFile.case_id==case_id))
    if not case_file: raise HTTPException(404,"Case file not found")
    base=Path(settings.storage_path).resolve()
    path=(base / case_file.file_path).resolve()
    if base not in path.parents or not path.exists(): raise HTTPException(404,"Stored file is missing")

    preview=build_preview(case_file.original_file_name,path.read_bytes())
    if not preview["fields"] and not preview["lines"]:
        raise HTTPException(422, "No reliable RFQ data was extracted; intake stopped before creating an RFQ. Review the document layout or enter the RFQ manually.")

    # Do not create a second RFQ from the same source file if intake was already started.
    marker = f"Intake workflow started from file #{file_id};"
    existing_rfq = db.scalar(select(RFQ).where(RFQ.case_id == case_id, RFQ.notes.like(f"%{marker}%")))
    if existing_rfq:
        raise HTTPException(409, f"RFQ intake has already been started from file #{file_id} (RFQ #{existing_rfq.id}).")

    values={x["field_name"]:candidate_value(x, normalized=True) for x in preview["fields"] if x.get("value")}

    def parse_date(value):
        if not value: return None
        for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%Y/%m/%d"):
            try: return datetime.strptime(str(value).strip(),fmt).date()
            except ValueError: pass
        return None

    request_date=parse_date(values.get("request_date"))
    required_date=parse_date(values.get("required_date"))
    if request_date and required_date and required_date < request_date:
        required_date=None

    rfq=RFQ(case_id=case_id,customer_id=case.customer_id,
        customer_rfq_number=values.get("customer_rfq_number"), title=values.get("title"),
        request_date=request_date, required_date=required_date, currency=values.get("currency"),
        delivery_location=values.get("delivery_location"), incoterm=values.get("incoterm"),
        status="UNDER_REVIEW", notes=f"Intake workflow started from file #{file_id}; extracted data requires verification.",
        created_at=now(),updated_at=now())
    db.add(rfq); db.flush()

    field_to_rfq={"customer_rfq_number","title","request_date","required_date","currency","delivery_location","incoterm"}
    tasks=[]
    for field in preview["fields"]:
        task=VerificationTask(case_id=case_id,rfq_id=rfq.id,field_name=field["field_name"],
            reason="EXTRACTION",status="PENDING",source_file_id=file_id,extracted_value=str(field["value"]),
            confidence=field.get("confidence"),created_at=now(),updated_at=now())
        if field["field_name"] not in field_to_rfq:
            task.notes="Candidate field is not yet mapped to an authoritative RFQ field."
        db.add(task); tasks.append(task)

    line_results=[]
    for line in preview["lines"]:
        values_line={x["field_name"]:candidate_value(x) for x in line["fields"] if x.get("value") is not None}
        normalized_line={x["field_name"]:candidate_value(x, normalized=True) for x in line["fields"] if x.get("value") is not None}
        qty=None
        if values_line.get("quantity"):
            try: qty=Decimal(str(values_line["quantity"]).replace(",",""))
            except InvalidOperation: qty=None
        obj=RFQLine(rfq_id=rfq.id,line_number=line["line_number"],description_original=values_line.get("description_original"),
            description_normalized=normalized_line.get("description_original"),
            manufacturer=normalized_line.get("manufacturer") or values_line.get("manufacturer"),customer_part_number=values_line.get("customer_part_number"),
            quantity=qty,unit=values_line.get("unit"),status="NEW",verification_status="PENDING",
            condition_required=values_line.get("condition_required") or "NEW",
            condition_source="CUSTOMER" if values_line.get("condition_required") else "DEFAULT_RULE",
            documents_required=values_line.get("documents_required"),technical_requirements=values_line.get("technical_requirements"),
            delivery_requirement=values_line.get("delivery_requirement"),
            created_at=now(),updated_at=now())
        db.add(obj); db.flush()
        for field in line["fields"]:
            task=VerificationTask(case_id=case_id,rfq_id=rfq.id,rfq_line_id=obj.id,field_name=field["field_name"],
                reason="EXTRACTION",status="PENDING",source_file_id=file_id,extracted_value=str(field["value"]),
                confidence=field.get("confidence"),created_at=now(),updated_at=now())
            if field.get("translation_status") in {"GLOSSARY_TRANSLATION", "TRANSLATION_REQUIRED"}:
                task.notes=(f"Original text: {field.get('value')} | English candidate: {field.get('translated_value') or 'REQUIRES AI TRANSLATION'} "
                             f"| Translation status: {field.get('translation_status')} | Translation confidence: {field.get('translation_confidence', 0)}")
            db.add(task); tasks.append(task)
            if field.get("translation_status") == "GLOSSARY_TRANSLATION" and field.get("translated_value"):
                tr_task=VerificationTask(case_id=case_id,rfq_id=rfq.id,rfq_line_id=obj.id,field_name="translation:"+field["field_name"],
                    reason="TRANSLATION_REVIEW",status="PENDING",source_file_id=file_id,
                    extracted_value=field.get("translated_value"),confidence=field.get("translation_confidence"),
                    requested_value=field.get("value"),
                    notes="English translation candidate must be confirmed by the user before it is treated as authoritative.",
                    created_at=now(),updated_at=now())
                db.add(tr_task); tasks.append(tr_task)
            elif field.get("translation_status") == "TRANSLATION_REQUIRED":
                tr_task=VerificationTask(case_id=case_id,rfq_id=rfq.id,rfq_line_id=obj.id,field_name="translation:"+field["field_name"],
                    reason="TRANSLATION_REVIEW",status="PENDING",source_file_id=file_id,
                    extracted_value=None,confidence=0,requested_value=field.get("value"),
                    notes="Persian text requires English translation. No English value was guessed.",
                    created_at=now(),updated_at=now())
                db.add(tr_task); tasks.append(tr_task)
        # Important values that cannot be reliably identified from the file are surfaced
        # explicitly for user clarification instead of being silently guessed.
        for required_field, label in (("manufacturer", "Manufacturer"), ("customer_part_number", "Part Number"),
                                      ("quantity", "Quantity"), ("unit", "Unit")):
            if not values_line.get(required_field):
                db.add(VerificationTask(
                    case_id=case_id, rfq_id=rfq.id, rfq_line_id=obj.id, field_name=required_field,
                    reason="CUSTOMER_CLARIFICATION", status="PENDING", source_file_id=file_id,
                    extracted_value=None, confidence=0, requested_value=f"{label} was not reliably identified in the uploaded file.",
                    notes="Important field missing or not reliably identifiable from customer document; user confirmation is required.",
                    created_at=now(), updated_at=now()
                ))
        line_results.append(obj)

    # Missing RFQ-level values are also made explicit to the user.
    for required_field, label in (("customer_rfq_number", "Customer RFQ Number"), ("required_date", "Required Date"),
                                  ("currency", "Currency"), ("delivery_location", "Delivery Location"),
                                  ("incoterm", "Incoterm")):
        if not values.get(required_field):
            db.add(VerificationTask(
                case_id=case_id, rfq_id=rfq.id, field_name=required_field,
                reason="CUSTOMER_CLARIFICATION", status="PENDING", source_file_id=file_id,
                extracted_value=None, confidence=0, requested_value=f"{label} was not reliably identified in the uploaded file.",
                notes="Important RFQ field missing or not reliably identifiable from customer document; user confirmation is required.",
                created_at=now(), updated_at=now()
            ))

    db.commit(); db.refresh(rfq)
    verification_count = len(db.scalars(select(VerificationTask).where(VerificationTask.rfq_id == rfq.id)).all())
    return {"rfq":rfq,"lines":line_results,"verification_tasks_created":verification_count,"warnings":preview["warnings"],"extraction_method":preview["extraction_method"]}

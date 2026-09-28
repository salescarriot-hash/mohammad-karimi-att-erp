from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.case import Case
from app.models.customer import Customer
from app.schemas.case import CaseCreate, CaseOut, CaseUpdate, CASE_STATUSES, CASE_TYPES, PRIORITIES

router = APIRouter(prefix="/customers/{customer_id}/cases", tags=["Cases"])
workspace_router = APIRouter(prefix="/cases", tags=["Case Workspace"])

def now():
    return datetime.now(timezone.utc)

def ensure_customer(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

def ensure_case(db: Session, customer_id: int, case_id: int) -> Case:
    case = db.scalar(select(Case).where(Case.id == case_id, Case.customer_id == customer_id))
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.post("", response_model=CaseOut, status_code=201)
def create_case(customer_id: int, payload: CaseCreate, db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    timestamp = now()
    # case_number is NOT NULL, so it must have a value before the first flush.
    # Use a temporary unique value, let PostgreSQL allocate the case ID, then
    # replace it with the canonical CASE-YYYY-XXXXXX format before commit.
    import uuid
    provisional_number = f"CASE-{timestamp.year}-{uuid.uuid4().hex[:12].upper()}"
    case = Case(customer_id=customer_id, title=payload.title, case_type=payload.case_type,
                description=payload.description, status=payload.status, priority=payload.priority,
                assigned_to=payload.assigned_to, case_number=provisional_number,
                created_at=timestamp, updated_at=timestamp)
    db.add(case)
    db.flush()
    case.case_number = f"CASE-{timestamp.year}-{case.id:06d}"
    db.commit()
    db.refresh(case)
    return case

@router.get("", response_model=list[CaseOut])
def list_cases(customer_id: int, q: str | None = Query(default=None), status: str | None = None,
               priority: str | None = None, limit: int = Query(default=50, ge=1, le=200),
               offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    stmt = select(Case).where(Case.customer_id == customer_id)
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(Case.case_number.ilike(term), Case.title.ilike(term), Case.description.ilike(term)))
    if status:
        status = status.upper()
        if status not in CASE_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid case status")
        stmt = stmt.where(Case.status == status)
    if priority:
        priority = priority.upper()
        if priority not in PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid case priority")
        stmt = stmt.where(Case.priority == priority)
    return list(db.scalars(stmt.order_by(Case.id.desc()).offset(offset).limit(limit)).all())

@router.get("/{case_id}", response_model=CaseOut)
def get_case(customer_id: int, case_id: int, db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    return ensure_case(db, customer_id, case_id)

@router.patch("/{case_id}", response_model=CaseOut)
def update_case(customer_id: int, case_id: int, payload: CaseUpdate, db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    case = ensure_case(db, customer_id, case_id)
    data = payload.model_dump(exclude_unset=True)
    if "case_type" in data:
        data["case_type"] = data["case_type"].upper()
        if data["case_type"] not in CASE_TYPES:
            raise HTTPException(status_code=400, detail="Invalid case type")
    if "status" in data:
        data["status"] = data["status"].upper()
        if data["status"] not in CASE_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid case status")
        if data["status"] == "CLOSED" and case.closed_at is None:
            case.closed_at = now()
        elif data["status"] != "CLOSED":
            case.closed_at = None
    if "priority" in data:
        data["priority"] = data["priority"].upper()
        if data["priority"] not in PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid case priority")
    for key, value in data.items():
        setattr(case, key, value)
    case.updated_at = now()
    db.commit()
    db.refresh(case)
    return case


@workspace_router.get("/{case_id}", response_model=CaseOut)
def get_case_by_id(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.customer import Customer, CustomerContact, CustomerSite
from app.schemas.customer import (
    CustomerCreate, CustomerOut, CustomerUpdate,
    ContactCreate, ContactOut, ContactUpdate,
    SiteCreate, SiteOut, SiteUpdate,
)

router = APIRouter(prefix="/customers", tags=["Customers"])


def now():
    return datetime.now(timezone.utc)


def ensure_customer(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def duplicate_customer(db: Session, name: str, country: str | None, exclude_id: int | None = None):
    stmt = select(Customer).where(func.lower(func.trim(Customer.name)) == name.strip().lower())
    if country:
        stmt = stmt.where(func.lower(func.trim(Customer.country)) == country.strip().lower())
    else:
        stmt = stmt.where(Customer.country.is_(None))
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    return db.scalar(stmt)


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    duplicate = duplicate_customer(db, payload.name, payload.country)
    if duplicate:
        raise HTTPException(status_code=409, detail={"message": "Possible duplicate customer", "customer_id": duplicate.id})
    customer = Customer(**payload.model_dump(), created_at=now(), updated_at=now())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerOut])
def list_customers(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    customer_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Customer)
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(Customer.name.ilike(term), Customer.name_en.ilike(term), Customer.city.ilike(term), Customer.tax_id.ilike(term)))
    if status:
        stmt = stmt.where(Customer.status == status)
    if customer_type:
        stmt = stmt.where(Customer.customer_type == customer_type)
    return list(db.scalars(stmt.order_by(Customer.id.desc()).offset(offset).limit(limit)).all())


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return ensure_customer(db, customer_id)


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    customer = ensure_customer(db, customer_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        duplicate = duplicate_customer(db, data["name"], data.get("country", customer.country), customer_id)
        if duplicate:
            raise HTTPException(status_code=409, detail={"message": "Possible duplicate customer", "customer_id": duplicate.id})
    for key, value in data.items():
        setattr(customer, key, value)
    customer.updated_at = now()
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}/contacts", response_model=list[ContactOut])
def list_contacts(customer_id: int, db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    return list(db.scalars(select(CustomerContact).where(CustomerContact.customer_id == customer_id).order_by(CustomerContact.id.desc())).all())


@router.post("/{customer_id}/contacts", response_model=ContactOut, status_code=201)
def create_contact(customer_id: int, payload: ContactCreate, db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    contact = CustomerContact(customer_id=customer_id, **payload.model_dump(), created_at=now(), updated_at=now())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.patch("/{customer_id}/contacts/{contact_id}", response_model=ContactOut)
def update_contact(customer_id: int, contact_id: int, payload: ContactUpdate, db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    contact = db.scalar(select(CustomerContact).where(CustomerContact.id == contact_id, CustomerContact.customer_id == customer_id))
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    contact.updated_at = now()
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{customer_id}/sites", response_model=list[SiteOut])
def list_sites(customer_id: int, db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    return list(db.scalars(select(CustomerSite).where(CustomerSite.customer_id == customer_id).order_by(CustomerSite.id.desc())).all())


@router.post("/{customer_id}/sites", response_model=SiteOut, status_code=201)
def create_site(customer_id: int, payload: SiteCreate, db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    if payload.site_code:
        existing = db.scalar(select(CustomerSite).where(CustomerSite.customer_id == customer_id, CustomerSite.site_code == payload.site_code))
        if existing:
            raise HTTPException(status_code=409, detail={"message": "Site code already exists for this customer", "site_id": existing.id})
    site = CustomerSite(customer_id=customer_id, **payload.model_dump(), created_at=now(), updated_at=now())
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.patch("/{customer_id}/sites/{site_id}", response_model=SiteOut)
def update_site(customer_id: int, site_id: int, payload: SiteUpdate, db: Session = Depends(get_db)):
    ensure_customer(db, customer_id)
    site = db.scalar(select(CustomerSite).where(CustomerSite.id == site_id, CustomerSite.customer_id == customer_id))
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("site_code"):
        existing = db.scalar(select(CustomerSite).where(CustomerSite.customer_id == customer_id, CustomerSite.site_code == data["site_code"], CustomerSite.id != site_id))
        if existing:
            raise HTTPException(status_code=409, detail={"message": "Site code already exists for this customer", "site_id": existing.id})
    for key, value in data.items():
        setattr(site, key, value)
    site.updated_at = now()
    db.commit()
    db.refresh(site)
    return site

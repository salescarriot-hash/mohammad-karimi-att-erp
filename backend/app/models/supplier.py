from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255))
    supplier_type: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(500))
    contact_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(100))
    whatsapp: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class SupplierQuote(Base):
    __tablename__ = "supplier_quotes"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    rfq_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False)
    quote_number: Mapped[str | None] = mapped_column(String(100))
    quote_date: Mapped[Date | None] = mapped_column(Date)
    valid_until: Mapped[Date | None] = mapped_column(Date)
    currency: Mapped[str | None] = mapped_column(String(10))
    incoterm: Mapped[str | None] = mapped_column(String(20))
    delivery_time: Mapped[str | None] = mapped_column(String(100))
    payment_terms: Mapped[str | None] = mapped_column(String(255))
    origin: Mapped[str | None] = mapped_column(String(255))
    warranty: Mapped[str | None] = mapped_column(String(255))
    source_file: Mapped[str | None] = mapped_column(String(1000))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECEIVED")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class SupplierQuoteLine(Base):
    __tablename__ = "supplier_quote_lines"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    supplier_quote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("supplier_quotes.id", ondelete="CASCADE"), nullable=False)
    rfq_line_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rfq_lines.id", ondelete="CASCADE"), nullable=False)
    supplier_part_number: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    unit: Mapped[str | None] = mapped_column(String(50))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    condition: Mapped[str | None] = mapped_column(String(50))
    brand: Mapped[str | None] = mapped_column(String(255))
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    lead_time: Mapped[str | None] = mapped_column(String(100))
    availability: Mapped[str | None] = mapped_column(String(50))
    technical_compliance: Mapped[str] = mapped_column(String(50), nullable=False, default="NOT_REVIEWED")
    deviation: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

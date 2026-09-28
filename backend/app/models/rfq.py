from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class RFQ(Base):
    __tablename__ = "rfqs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    site_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("customer_sites.id", ondelete="SET NULL"))
    customer_rfq_number: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(255))
    request_date: Mapped[date | None] = mapped_column(Date)
    required_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str | None] = mapped_column(String(10))
    delivery_location: Mapped[str | None] = mapped_column(String(255))
    incoterm: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)
    source_rfq_url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class RFQLine(Base):
    __tablename__ = "rfq_lines"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rfq_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description_original: Mapped[str | None] = mapped_column(Text)
    description_normalized: Mapped[str | None] = mapped_column(Text)
    part_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("parts.id", ondelete="SET NULL"))
    equipment_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("equipment.id", ondelete="SET NULL"))
    equipment_model_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("equipment_models.id", ondelete="SET NULL"))
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    customer_part_number: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18,4))
    unit: Mapped[str | None] = mapped_column(String(50))
    condition_required: Mapped[str | None] = mapped_column(String(50))
    condition_source: Mapped[str | None] = mapped_column(String(30))
    documents_required: Mapped[str | None] = mapped_column(Text)
    technical_requirements: Mapped[str | None] = mapped_column(Text)
    delivery_requirement: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)
    verification_status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

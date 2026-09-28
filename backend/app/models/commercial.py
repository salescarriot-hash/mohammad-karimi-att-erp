from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class MarketPrice(Base):
    __tablename__ = "market_prices"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    part_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("parts.id", ondelete="SET NULL"))
    supplier_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("suppliers.id", ondelete="SET NULL"))
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    condition: Mapped[str | None] = mapped_column(String(50))
    brand: Mapped[str | None] = mapped_column(String(255))
    part_number: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18,4))
    unit: Mapped[str | None] = mapped_column(String(50))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20,6))
    currency: Mapped[str | None] = mapped_column(String(10))
    incoterm: Mapped[str | None] = mapped_column(String(20))
    lead_time: Mapped[str | None] = mapped_column(String(100))
    availability: Mapped[str | None] = mapped_column(String(50))
    observed_date: Mapped[date | None] = mapped_column(Date)
    confidence: Mapped[str] = mapped_column(String(30), nullable=False, default="MEDIUM")
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

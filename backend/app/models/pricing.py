from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class PricingSetting(Base):
    __tablename__ = "pricing_settings"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    default_margin_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MARKUP")
    default_margin_value: Mapped[Decimal] = mapped_column(Numeric(12,6), nullable=False, default=Decimal("0.05"))
    minimum_margin_type: Mapped[str | None] = mapped_column(String(30))
    minimum_margin_value: Mapped[Decimal | None] = mapped_column(Numeric(12,6))
    default_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    rounding_method: Mapped[str] = mapped_column(String(30), nullable=False, default="NONE")
    rounding_value: Mapped[Decimal | None] = mapped_column(Numeric(20,6))
    default_incoterm: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class PricingCalculation(Base):
    __tablename__ = "pricing_calculations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rfq_line_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rfq_lines.id", ondelete="CASCADE"), nullable=False)
    commercial_decision_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("commercial_decisions.id", ondelete="SET NULL"))
    basis_type: Mapped[str] = mapped_column(String(30), nullable=False, default="TARGET_PURCHASE_PRICE")
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False)
    purchase_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(20,8), nullable=False, default=Decimal("1"))
    exchange_rate_date: Mapped[date | None] = mapped_column(Date)
    target_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    freight_cost: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False, default=Decimal("0"))
    insurance_cost: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False, default=Decimal("0"))
    customs_cost: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False, default=Decimal("0"))
    clearance_cost: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False, default=Decimal("0"))
    local_delivery_cost: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False, default=Decimal("0"))
    financial_cost: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False, default=Decimal("0"))
    other_cost: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False, default=Decimal("0"))
    landed_cost: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False)
    margin_type: Mapped[str] = mapped_column(String(30), nullable=False)
    margin_value: Mapped[Decimal] = mapped_column(Numeric(12,6), nullable=False)
    calculated_selling_price: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False)
    rounding_method: Mapped[str] = mapped_column(String(30), nullable=False, default="NONE")
    rounding_value: Mapped[Decimal | None] = mapped_column(Numeric(20,6))
    final_selling_price: Mapped[Decimal] = mapped_column(Numeric(20,6), nullable=False)
    incoterm: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

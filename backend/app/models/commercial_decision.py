from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class CommercialDecision(Base):
    __tablename__ = "commercial_decisions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rfq_line_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rfq_lines.id", ondelete="CASCADE"), nullable=False)
    selected_supplier_quote_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("supplier_quote_lines.id", ondelete="SET NULL"))
    decision_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    target_purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(20,6))
    target_currency: Mapped[str | None] = mapped_column(String(10))
    technical_status: Mapped[str | None] = mapped_column(String(50))
    commercial_notes: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[int | None] = mapped_column(BigInteger)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

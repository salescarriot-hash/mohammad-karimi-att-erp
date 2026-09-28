from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class QuotationApproval(Base):
    __tablename__ = "quotation_approvals"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    quotation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    status_from: Mapped[str | None] = mapped_column(String(40))
    status_to: Mapped[str | None] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

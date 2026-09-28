from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class VerificationTask(Base):
    __tablename__ = "verification_tasks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cases.id", ondelete="CASCADE"))
    rfq_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("rfqs.id", ondelete="CASCADE"))
    rfq_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("rfq_lines.id", ondelete="CASCADE"))
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_value: Mapped[str | None] = mapped_column(Text)
    requested_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    source_file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("files.id", ondelete="SET NULL"))
    extracted_value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5,4))
    verified_value: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

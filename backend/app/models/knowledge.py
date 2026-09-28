from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class KnowledgeAssertion(Base):
    __tablename__ = "knowledge_assertions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[int | None] = mapped_column(BigInteger)
    subject_label: Mapped[str | None] = mapped_column(String(500))
    predicate: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str | None] = mapped_column(String(50))
    object_id: Mapped[int | None] = mapped_column(BigInteger)
    object_label: Mapped[str | None] = mapped_column(String(500))
    object_text: Mapped[str | None] = mapped_column(Text)
    source_file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("files.id", ondelete="SET NULL"))
    source: Mapped[str | None] = mapped_column(String(1000))
    evidence_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Numeric(5,4))
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

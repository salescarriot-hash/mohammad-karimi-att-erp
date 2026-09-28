from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class KnowledgeConflict(Base):
    __tablename__ = "knowledge_conflicts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    assertion_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("knowledge_assertions.id", ondelete="CASCADE"), nullable=False)
    existing_assertion_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("knowledge_assertions.id", ondelete="CASCADE"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    resolution: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

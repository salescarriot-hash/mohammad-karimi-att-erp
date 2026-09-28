from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class PartApplication(Base):
    __tablename__ = "part_applications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    part_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    equipment_model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("equipment_models.id", ondelete="CASCADE"), nullable=False)
    application_notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class PartRelation(Base):
    __tablename__ = "part_relations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    part_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    related_part_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

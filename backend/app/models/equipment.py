from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    site_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("customer_sites.id", ondelete="SET NULL")
    )
    equipment_model_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("equipment_models.id", ondelete="SET NULL")
    )
    revision: Mapped[str | None] = mapped_column(String(100))
    serial_number: Mapped[str | None] = mapped_column(String(255))
    tag_number: Mapped[str | None] = mapped_column(String(255))
    unit_number: Mapped[str | None] = mapped_column(String(100))
    commissioning_year: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

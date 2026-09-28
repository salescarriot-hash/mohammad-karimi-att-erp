from pydantic import BaseModel
from typing import Any

class PartApplicationOut(BaseModel):
    id: int
    equipment_model_id: int
    equipment_model: str | None = None
    equipment_type: str | None = None
    family: str | None = None
    application_notes: str | None = None
    source: str | None = None
    verification_status: str

class PartRelationOut(BaseModel):
    id: int
    related_part_id: int
    related_part_number: str | None = None
    related_description: str | None = None
    relation_type: str
    source: str | None = None
    notes: str | None = None
    verification_status: str

class PartContextOut(BaseModel):
    rfq_line_id: int
    part_id: int | None
    part_number: str | None
    part_description: str | None
    applications: list[PartApplicationOut]
    relations: list[PartRelationOut]
    warnings: list[str]
    needs_confirmation: bool

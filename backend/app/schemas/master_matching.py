from pydantic import BaseModel, Field

class MatchCandidate(BaseModel):
    entity_type: str
    entity_id: int
    display_name: str
    confidence: float = Field(ge=0, le=1)
    match_reasons: list[str] = []
    source: str = "MASTER_DATA"

class MatchResult(BaseModel):
    rfq_line_id: int
    input: dict
    candidates: list[MatchCandidate]
    needs_confirmation: bool = True

class MatchDecision(BaseModel):
    entity_type: str
    entity_id: int
    notes: str | None = None

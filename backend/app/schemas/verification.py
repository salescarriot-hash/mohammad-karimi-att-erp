from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator

STATUSES={"PENDING","CONFIRMED","EDITED","REJECTED","NEEDS_CLARIFICATION"}

class VerificationOut(BaseModel):
    id:int; case_id:int|None; rfq_id:int|None; rfq_line_id:int|None
    field_name:str; current_value:str|None; requested_value:str|None; reason:str
    status:str; source_file_id:int|None; extracted_value:str|None
    confidence:Decimal|None; verified_value:str|None; verified_by:int|None
    verified_at:datetime|None; notes:str|None; created_at:datetime; updated_at:datetime
    model_config=ConfigDict(from_attributes=True)

class VerificationDecision(BaseModel):
    action:str = Field(description="CONFIRM, EDIT, REJECT, or NEEDS_CLARIFICATION")
    verified_value:str|None=None
    notes:str|None=None

    @field_validator("action")
    @classmethod
    def validate_action(cls, value):
        value=value.strip().upper()
        if value not in STATUSES-{"PENDING"}: raise ValueError("Invalid verification action")
        return value

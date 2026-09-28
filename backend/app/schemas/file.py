from datetime import datetime
from pydantic import BaseModel, ConfigDict

DOCUMENT_TYPES = {"RFQ", "NAMEPLATE", "TECHNICAL_DATASHEET", "SUPPLIER_QUOTE", "CUSTOMER_PO", "CUSTOMER_EMAIL", "PHOTO", "OTHER"}

class FileOut(BaseModel):
    id: int
    case_id: int
    file_name: str
    original_file_name: str
    document_type: str | None
    file_type: str | None
    file_path: str
    uploaded_at: datetime
    uploaded_by: int | None
    model_config = ConfigDict(from_attributes=True)

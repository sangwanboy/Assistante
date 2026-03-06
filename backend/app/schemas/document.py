from pydantic import BaseModel
from datetime import datetime

class DocumentCreate(BaseModel):
    filename: str
    file_type: str
    size: int
    content_hash: str
    conversation_id: str | None = None

class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    size: int
    content_hash: str
    conversation_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

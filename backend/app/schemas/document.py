from pydantic import BaseModel
from datetime import datetime

class DocumentCreate(BaseModel):
    filename: str
    file_type: str
    size: int
    content_hash: str

class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    size: int
    content_hash: str
    created_at: datetime

    class Config:
        from_attributes = True

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class SkillBase(BaseModel):
    name: str
    description: Optional[str] = None
    instructions: str
    is_active: bool = True
    user_invocable: bool = True
    trigger_pattern: Optional[str] = None
    metadata_json: Optional[str] = None


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    is_active: Optional[bool] = None
    user_invocable: Optional[bool] = None
    trigger_pattern: Optional[str] = None
    metadata_json: Optional[str] = None


class SkillOut(SkillBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillImportRequest(BaseModel):
    """Import a skill from raw SKILL.md content."""
    content: str


class SkillExportResponse(BaseModel):
    """Exported SKILL.md content."""
    filename: str
    content: str

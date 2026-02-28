from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class CustomToolBase(BaseModel):
    name: str
    description: str
    parameters_schema: str  # JSON string of parameter definitions
    code: str               # Python source code
    is_active: bool = True


class CustomToolCreate(CustomToolBase):
    pass


class CustomToolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters_schema: Optional[str] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None


class CustomToolOut(CustomToolBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomToolTestRequest(BaseModel):
    """Request body for test-executing a custom tool."""
    arguments: dict = {}


class CustomToolTestResponse(BaseModel):
    """Result from test-executing a custom tool."""
    success: bool
    output: str

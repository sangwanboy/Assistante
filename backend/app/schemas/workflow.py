from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class NodeBase(BaseModel):
    id: str
    type: str
    sub_type: str
    config_json: str = "{}"
    position_x: str = "0"
    position_y: str = "0"

class NodeCreate(NodeBase):
    pass

class NodeOut(NodeBase):
    workflow_id: str

    class Config:
        from_attributes = True

class EdgeBase(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str

class EdgeCreate(EdgeBase):
    pass

class EdgeOut(EdgeBase):
    workflow_id: str

    class Config:
        from_attributes = True

class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None

class WorkflowCreate(WorkflowBase):
    agent_id: Optional[str] = None
    channel_id: Optional[str] = None

class WorkflowOut(WorkflowBase):
    id: str
    is_active: bool
    agent_id: Optional[str] = None
    channel_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkflowGraph(WorkflowOut):
    nodes: List[NodeOut]
    edges: List[EdgeOut]

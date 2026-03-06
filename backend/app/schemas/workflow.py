from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ---------- Node Schemas ----------

class NodeBase(BaseModel):
    id: str
    type: str
    sub_type: str
    label: Optional[str] = None
    config_json: str = "{}"
    position_x: str = "0"
    position_y: str = "0"

class NodeCreate(NodeBase):
    pass

class NodeOut(NodeBase):
    workflow_id: str

    class Config:
        from_attributes = True


# ---------- Edge Schemas ----------

class EdgeBase(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    source_handle: Optional[str] = None
    label: Optional[str] = None

class EdgeCreate(EdgeBase):
    pass

class EdgeOut(EdgeBase):
    workflow_id: str

    class Config:
        from_attributes = True


# ---------- Workflow Schemas ----------

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
    version: Optional[str] = "1"
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkflowGraph(WorkflowOut):
    nodes: List[NodeOut]
    edges: List[EdgeOut]


# ---------- Execution Schemas ----------

class WorkflowRunOut(BaseModel):
    id: str
    workflow_id: str
    status: str
    trigger_payload: Optional[str] = "{}"
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NodeExecutionOut(BaseModel):
    id: str
    run_id: str
    node_id: str
    status: str
    input_json: Optional[str] = "{}"
    output_json: Optional[str] = "{}"
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkflowRunDetail(WorkflowRunOut):
    node_executions: List[NodeExecutionOut]

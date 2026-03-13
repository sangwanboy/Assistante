from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base

def generate_uuid():
    return str(uuid.uuid4())


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    channel_id = Column(String, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    version = Column(String, default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    nodes = relationship("Node", back_populates="workflow", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="workflow", cascade="all, delete-orphan")
    runs = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")


class Node(Base):
    __tablename__ = "nodes"

    id = Column(String, primary_key=True)  # Using ReactFlow string IDs
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)        # trigger, action, agent, tool, data, logic, human
    sub_type = Column(String, nullable=False)     # webhook, schedule, agent_call, http_request, etc.
    label = Column(String, nullable=True)         # Human-readable display name
    config_json = Column(Text, default="{}")      # JSON string for configuration

    # UI Positioning
    position_x = Column(String, default="0")
    position_y = Column(String, default="0")

    workflow = relationship("Workflow", back_populates="nodes")


class Edge(Base):
    __tablename__ = "edges"

    id = Column(String, primary_key=True) # ReactFlow edge ID
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    source_node_id = Column(String, nullable=False)
    target_node_id = Column(String, nullable=False)
    source_handle = Column(String, nullable=True)   # For multi-output nodes (e.g. condition true/false)
    label = Column(String, nullable=True)            # Optional edge label

    workflow = relationship("Workflow", back_populates="edges")


class WorkflowRun(Base):
    """Tracks each execution of a workflow."""
    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("ix_workflow_runs_status", "status"),
        Index("ix_workflow_runs_workflow_id", "workflow_id"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="pending")       # pending, running, completed, failed, paused
    trigger_payload = Column(Text, default="{}")     # JSON of the triggering data
    context_json = Column(Text, default="{}")        # JSON of the runtime execution context

    # Checkpoint support for resuming paused runs
    checkpoint_node_id = Column(String, nullable=True)
    checkpoint_payload = Column(Text, nullable=True)

    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    workflow = relationship("Workflow", back_populates="runs")
    node_executions = relationship("NodeExecution", back_populates="run", cascade="all, delete-orphan")


class NodeExecution(Base):
    """Tracks execution of each node within a workflow run."""
    __tablename__ = "node_executions"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String, nullable=False)          # References Node.id
    status = Column(String, default="waiting")        # waiting, running, completed, failed, skipped
    input_json = Column(Text, default="{}")
    output_json = Column(Text, default="{}")
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    run = relationship("WorkflowRun", back_populates="node_executions")


class WorkflowMemory(Base):
    """Persistent memory associated with a workflow, partitioned by agent or channel."""
    __tablename__ = "workflow_memories"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=True)
    channel_id = Column(String, ForeignKey("channels.id", ondelete="CASCADE"), nullable=True)

    memory_json = Column(Text, default="{}")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

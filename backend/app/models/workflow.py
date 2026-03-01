from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    nodes = relationship("Node", back_populates="workflow", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="workflow", cascade="all, delete-orphan")

class Node(Base):
    __tablename__ = "nodes"

    id = Column(String, primary_key=True)  # Using ReactFlow string IDs
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)  # trigger, action
    sub_type = Column(String, nullable=False)  # webhook, schedule, summarize, llm, email
    config_json = Column(Text, default="{}")  # JSON string for configuration
    
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

    workflow = relationship("Workflow", back_populates="edges")

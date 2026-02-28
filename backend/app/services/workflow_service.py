import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.workflow import Workflow, Node, Edge
from app.schemas.workflow import WorkflowCreate, NodeCreate, EdgeCreate

class WorkflowService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_workflows(self) -> List[Workflow]:
        stmt = select(Workflow).order_by(Workflow.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        stmt = select(Workflow).options(selectinload(Workflow.nodes), selectinload(Workflow.edges)).where(Workflow.id == workflow_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_workflow(self, name: str, description: Optional[str] = None) -> Workflow:
        workflow = Workflow(name=name, description=description)
        self.session.add(workflow)
        await self.session.commit()
        await self.session.refresh(workflow)
        return workflow

    async def save_graph(self, workflow_id: str, nodes: List[NodeCreate], edges: List[EdgeCreate]) -> Optional[Workflow]:
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return None

        # Delete existing nodes & edges directly (cascade will handle it if we delete via ORM, or we can just empty arrays)
        # SQLAlchemy selectinload populated arrays:
        for node in list(workflow.nodes):
            await self.session.delete(node)
        for edge in list(workflow.edges):
            await self.session.delete(edge)

        # Clear relationships in session 
        workflow.nodes.clear()
        workflow.edges.clear()

        # Add new
        for node_in in nodes:
            n = Node(
                id=node_in.id,
                workflow_id=workflow_id,
                type=node_in.type,
                sub_type=node_in.sub_type,
                config_json=node_in.config_json,
                position_x=node_in.position_x,
                position_y=node_in.position_y
            )
            self.session.add(n)
        
        for edge_in in edges:
            e = Edge(
                id=edge_in.id,
                workflow_id=workflow_id,
                source_node_id=edge_in.source_node_id,
                target_node_id=edge_in.target_node_id
            )
            self.session.add(e)

        await self.session.commit()
        
        return await self.get_workflow(workflow_id)

    async def delete_workflow(self, workflow_id: str) -> bool:
        workflow = await self.get_workflow(workflow_id)
        if workflow:
            await self.session.delete(workflow)
            await self.session.commit()
            return True
        return False

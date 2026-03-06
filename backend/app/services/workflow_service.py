from typing import List, Optional
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.workflow import Workflow, Node, Edge, WorkflowRun, NodeExecution
from app.schemas.workflow import NodeCreate, EdgeCreate


class WorkflowService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Workflow CRUD ────────────────────────────────────────

    async def list_workflows(
        self,
        agent_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> List[Workflow]:
        stmt = select(Workflow)
        if agent_id:
            stmt = stmt.where(Workflow.agent_id == agent_id)
        if channel_id:
            stmt = stmt.where(Workflow.channel_id == channel_id)
        stmt = stmt.order_by(Workflow.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        stmt = select(Workflow).options(
            selectinload(Workflow.nodes),
            selectinload(Workflow.edges)
        ).where(Workflow.id == workflow_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_workflow(
        self,
        name: str,
        description: Optional[str] = None,
        agent_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> Workflow:
        workflow = Workflow(
            name=name,
            description=description,
            agent_id=agent_id,
            channel_id=channel_id,
        )
        self.session.add(workflow)
        await self.session.commit()
        await self.session.refresh(workflow)
        return workflow

    async def save_graph(self, workflow_id: str, nodes: List[NodeCreate], edges: List[EdgeCreate]) -> Optional[Workflow]:
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return None

        # Delete existing nodes & edges
        for node in list(workflow.nodes):
            await self.session.delete(node)
        for edge in list(workflow.edges):
            await self.session.delete(edge)

        workflow.nodes.clear()
        workflow.edges.clear()

        # Add new nodes
        for node_in in nodes:
            n = Node(
                id=node_in.id,
                workflow_id=workflow_id,
                type=node_in.type,
                sub_type=node_in.sub_type,
                label=node_in.label,
                config_json=node_in.config_json,
                position_x=node_in.position_x,
                position_y=node_in.position_y
            )
            self.session.add(n)
        
        # Add new edges
        for edge_in in edges:
            e = Edge(
                id=edge_in.id,
                workflow_id=workflow_id,
                source_node_id=edge_in.source_node_id,
                target_node_id=edge_in.target_node_id,
                source_handle=edge_in.source_handle,
                label=edge_in.label,
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

    # ─── Workflow Run Tracking ────────────────────────────────

    async def create_run(self, workflow_id: str, trigger_payload: dict = None) -> WorkflowRun:
        run = WorkflowRun(
            workflow_id=workflow_id,
            status="pending",
            trigger_payload=json.dumps(trigger_payload or {}),
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def update_run_status(self, run_id: str, status: str, error: str = None) -> Optional[WorkflowRun]:
        stmt = select(WorkflowRun).where(WorkflowRun.id == run_id)
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            return None
        run.status = status
        if error:
            run.error = error
        if status in ("completed", "failed"):
            run.ended_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        stmt = select(WorkflowRun).options(
            selectinload(WorkflowRun.node_executions)
        ).where(WorkflowRun.id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_runs(self, workflow_id: str, limit: int = 20) -> List[WorkflowRun]:
        stmt = select(WorkflowRun).where(
            WorkflowRun.workflow_id == workflow_id
        ).order_by(WorkflowRun.started_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ─── Node Execution Tracking ─────────────────────────────

    async def create_node_execution(self, run_id: str, node_id: str, input_data: dict = None) -> NodeExecution:
        exe = NodeExecution(
            run_id=run_id,
            node_id=node_id,
            status="waiting",
            input_json=json.dumps(input_data or {}),
        )
        self.session.add(exe)
        await self.session.commit()
        await self.session.refresh(exe)
        return exe

    async def update_node_execution(
        self,
        execution_id: str,
        status: str,
        output_data: dict = None,
        error: str = None,
    ) -> Optional[NodeExecution]:
        stmt = select(NodeExecution).where(NodeExecution.id == execution_id)
        result = await self.session.execute(stmt)
        exe = result.scalar_one_or_none()
        if not exe:
            return None

        exe.status = status
        if status == "running" and not exe.started_at:
            exe.started_at = datetime.now(timezone.utc)
        if output_data:
            exe.output_json = json.dumps(output_data)
        if error:
            exe.error = error
        if status in ("completed", "failed", "skipped"):
            exe.ended_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(exe)
        return exe

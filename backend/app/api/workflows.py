from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from app.db.engine import get_session
from app.schemas.workflow import (
    WorkflowOut, WorkflowCreate, WorkflowGraph,
    NodeCreate, EdgeCreate,
    WorkflowRunOut, WorkflowRunDetail, WorkflowMemoryOut
)

from app.services.workflow_service import WorkflowService
from app.services.workflow_engine import WorkflowEngine
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry

router = APIRouter()

# Singletons initialized at app startup (set in main.py)
_provider_registry: Optional[ProviderRegistry] = None
_tool_registry: Optional[ToolRegistry] = None


def set_registries(provider_reg: ProviderRegistry, tool_reg: ToolRegistry):
    global _provider_registry, _tool_registry
    _provider_registry = provider_reg
    _tool_registry = tool_reg


def get_workflow_service(session: AsyncSession = Depends(get_session)) -> WorkflowService:
    return WorkflowService(session)


# ─── Workflow CRUD ────────────────────────────────────────

@router.get("", response_model=List[WorkflowOut])
async def list_workflows(
    agent_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    service: WorkflowService = Depends(get_workflow_service),
):
    return await service.list_workflows(agent_id=agent_id, channel_id=channel_id)


@router.post("", response_model=WorkflowOut)
async def create_workflow(
    workflow: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service)
):
    return await service.create_workflow(
        name=workflow.name,
        description=workflow.description,
        agent_id=workflow.agent_id,
        channel_id=workflow.channel_id,
    )


@router.get("/{workflow_id}", response_model=WorkflowGraph)
async def get_workflow(workflow_id: str, service: WorkflowService = Depends(get_workflow_service)):
    workflow = await service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.post("/{workflow_id}/graph", response_model=WorkflowGraph)
async def save_graph(
    workflow_id: str,
    nodes: List[NodeCreate],
    edges: List[EdgeCreate],
    service: WorkflowService = Depends(get_workflow_service)
):
    workflow = await service.save_graph(workflow_id, nodes, edges)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, service: WorkflowService = Depends(get_workflow_service)):
    success = await service.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "deleted"}


# ─── Workflow Execution ───────────────────────────────────

@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    payload: Dict[str, Any] = {},
    session: AsyncSession = Depends(get_session),
):
    """Trigger a workflow execution with an optional payload."""
    if not _provider_registry:
        raise HTTPException(status_code=500, detail="Provider registry not initialized")

    engine = WorkflowEngine(session, _provider_registry, _tool_registry)
    result = await engine.execute_workflow(workflow_id, payload)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Execution failed"))

    return result


@router.get("/{workflow_id}/runs", response_model=List[WorkflowRunOut])
async def list_runs(
    workflow_id: str,
    limit: int = Query(20, le=100),
    service: WorkflowService = Depends(get_workflow_service),
):
    """List execution runs for a workflow."""
    return await service.list_runs(workflow_id, limit=limit)


@router.get("/runs/{run_id}", response_model=WorkflowRunDetail)
async def get_run(
    run_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Get detailed run info with all node executions."""
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.get("/{workflow_id}/memory", response_model=WorkflowMemoryOut)
async def get_workflow_memory(
    workflow_id: str,
    agent_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    service: WorkflowService = Depends(get_workflow_service),
):
    """Get persistent memory for a workflow bounded by agent or channel."""
    memory = await service.get_workflow_memory(workflow_id, agent_id, channel_id)
    if not memory:
        # Return an empty dummy object instead of 404 to satisfy UI easily
        return WorkflowMemoryOut(
            id="empty",
            workflow_id=workflow_id,
            agent_id=agent_id,
            channel_id=channel_id,
            memory_json="{}"
        )
    return memory


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.engine import get_session
from app.schemas.workflow import WorkflowOut, WorkflowCreate, WorkflowGraph, NodeCreate, EdgeCreate
from app.services.workflow_service import WorkflowService

router = APIRouter()

def get_workflow_service(session: AsyncSession = Depends(get_session)) -> WorkflowService:
    return WorkflowService(session)

@router.get("", response_model=List[WorkflowOut])
async def list_workflows(service: WorkflowService = Depends(get_workflow_service)):
    return await service.list_workflows()

@router.post("", response_model=WorkflowOut)
async def create_workflow(
    workflow: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service)
):
    return await service.create_workflow(workflow.name, workflow.description)

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

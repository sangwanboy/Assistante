import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.orchestration_run import OrchestrationRun, OrchestrationTaskEdge, OrchestrationTaskNode

router = APIRouter(prefix="/runs")


@router.get("/{run_id}")
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)):
    run = await session.get(OrchestrationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    node_rows = await session.execute(
        select(OrchestrationTaskNode).where(OrchestrationTaskNode.run_id == run_id)
    )
    edge_rows = await session.execute(
        select(OrchestrationTaskEdge).where(OrchestrationTaskEdge.run_id == run_id)
    )

    def _safe_json(raw: str | None):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return raw

    nodes = []
    for n in node_rows.scalars().all():
        nodes.append(
            {
                "id": n.id,
                "node_key": n.node_key,
                "type": n.type,
                "agent_id": n.agent_id,
                "state": n.state,
                "prompt_excerpt": n.prompt_excerpt,
                "inputs": _safe_json(n.inputs_json),
                "outputs": _safe_json(n.outputs_json),
                "tool_calls": _safe_json(n.tool_calls_json),
                "token_usage": n.token_usage,
                "estimated_cost": n.estimated_cost,
                "error": n.error,
                "started_at": n.started_at,
                "completed_at": n.completed_at,
            }
        )

    edges = []
    for e in edge_rows.scalars().all():
        edges.append(
            {
                "id": e.id,
                "source": e.source_node_key,
                "target": e.target_node_key,
                "dependency_type": e.dependency_type,
            }
        )

    return {
        "run": {
            "id": run.id,
            "conversation_id": run.conversation_id,
            "root_agent_id": run.root_agent_id,
            "strategy": run.strategy,
            "state": run.state,
            "user_request": run.user_request,
            "plan": _safe_json(run.plan_json),
            "autonomy_report": _safe_json(run.autonomy_report_json),
            "token_usage_total": run.token_usage_total,
            "estimated_cost_total": run.estimated_cost_total,
            "created_at": run.created_at,
            "completed_at": run.completed_at,
        },
        "graph": {
            "nodes": nodes,
            "edges": edges,
        },
    }

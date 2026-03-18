from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orchestration_run import OrchestrationRun, OrchestrationTaskEdge, OrchestrationTaskNode


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RunTracer:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start_run(self, conversation_id: str | None, root_agent_id: str | None, strategy: str, user_request: str, plan: dict | None = None) -> OrchestrationRun:
        run = OrchestrationRun(
            conversation_id=conversation_id,
            root_agent_id=root_agent_id,
            strategy=strategy,
            state="RUNNING",
            user_request=user_request,
            plan_json=json.dumps(plan or {}),
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_or_create_root_node(self, run_id: str, prompt_excerpt: str | None = None, agent_id: str | None = None) -> OrchestrationTaskNode:
        rows = await self.session.execute(
            select(OrchestrationTaskNode).where(
                OrchestrationTaskNode.run_id == run_id,
                OrchestrationTaskNode.node_key == "root",
            )
        )
        existing = rows.scalar_one_or_none()
        if existing:
            return existing

        node = OrchestrationTaskNode(
            run_id=run_id,
            node_key="root",
            type="assistant_turn",
            agent_id=agent_id,
            state="RUNNING",
            started_at=utcnow(),
            prompt_excerpt=(prompt_excerpt or "")[:1000],
        )
        self.session.add(node)
        await self.session.commit()
        await self.session.refresh(node)
        return node

    async def log_tool_calls(self, run_id: str, tool_calls: list[dict]) -> None:
        node = await self.get_or_create_root_node(run_id)
        node.tool_calls_json = json.dumps(tool_calls)
        await self.session.commit()

    async def add_tokens_and_cost(self, run_id: str, tokens: int, cost: float) -> None:
        run = await self.session.get(OrchestrationRun, run_id)
        if not run:
            return
        run.token_usage_total = int(run.token_usage_total or 0) + int(tokens or 0)
        run.estimated_cost_total = float(run.estimated_cost_total or 0.0) + float(cost or 0.0)
        await self.session.commit()

    async def set_run_state(self, run_id: str, state: str, final_output: str | None = None, autonomy_report: dict | None = None, error: str | None = None) -> None:
        run = await self.session.get(OrchestrationRun, run_id)
        if not run:
            return
        run.state = state
        is_terminal = state in {"COMPLETED", "FAILED", "CANCELED"}
        if is_terminal:
            run.completed_at = utcnow()

        report = autonomy_report or {}
        if final_output:
            report["final_output_excerpt"] = final_output[:1500]
        if error:
            report["error"] = error
        run.autonomy_report_json = json.dumps(report)

        if is_terminal:
            node = await self.get_or_create_root_node(run_id)
            node.state = "COMPLETED" if state == "COMPLETED" else "FAILED"
            if final_output:
                node.outputs_json = json.dumps({"final_output": final_output[:3000]})
            if error:
                node.error = error[:3000]
            node.completed_at = utcnow()
        await self.session.commit()

    async def add_edge(self, run_id: str, source_node_key: str, target_node_key: str, dependency_type: str = "depends_on") -> None:
        edge = OrchestrationTaskEdge(
            run_id=run_id,
            source_node_key=source_node_key,
            target_node_key=target_node_key,
            dependency_type=dependency_type,
        )
        self.session.add(edge)
        await self.session.commit()

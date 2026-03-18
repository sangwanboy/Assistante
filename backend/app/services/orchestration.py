"""Orchestration engine for System Agent auto-delegation.

When no @mentions are present and orchestration_mode is "autonomous",
the System Agent analyzes the task, produces a delegation plan,
chains agent execution, and synthesizes a final response.

Supports parallel agent execution within groups (same group_id).
"""

import json
import logging
import re
import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent
from app.models.chain import DelegationChain
from app.models.workflow import Workflow, Node, Edge, WorkflowRun
from app.providers.base import ChatMessage
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry
from app.services.agent_status import AgentStatusManager, AgentState
from app.services.capability_registry import CapabilityRegistry
from app.schemas.orchestration import OrchestrationPlan
from app.services.run_tracer import RunTracer

logger = logging.getLogger(__name__)


def detect_circular_invocation(agents_involved: list[str], new_agent_id: str) -> bool:
    """Returns True if adding new_agent_id would create a cycle."""
    return new_agent_id in agents_involved


def check_depth(current_depth: int, max_depth: int) -> bool:
    """Returns True if depth limit is exceeded."""
    return current_depth >= max_depth


# Removed _extract_json_from_text as we now use strictly typed structured outputs.


class OrchestrationEngine:
    """Orchestrates multi-agent workflows via the System Agent."""

    def __init__(
        self,
        session: AsyncSession,
        provider_registry: ProviderRegistry,
        tool_registry: ToolRegistry,
        chat_service=None,
    ):
        self.session = session
        self.providers = provider_registry
        self.tools = tool_registry
        self.chat_service = chat_service
        self.capability_registry = CapabilityRegistry()



    async def plan_and_execute(
        self,
        conversation_id: str,
        system_agent: Agent,
        user_message: str,
        channel_agents: list[Agent],
        temperature: float = 0.7,
    ) -> AsyncIterator[dict]:
        """
        1. Ask System Agent to analyze the task and produce a plan
        2. Parse the plan into delegation steps
        3. Execute each step, feeding outputs forward (parallel within groups)
        4. Have System Agent synthesize final response
        """
        # Create a DelegationChain record
        chain = DelegationChain(
            conversation_id=conversation_id,
            max_depth=6,
            delegation_path="[]",
        )
        self.session.add(chain)
        await self.session.commit()
        await self.session.refresh(chain)

        tracer = RunTracer(self.session)
        run = await tracer.start_run(
            conversation_id=conversation_id,
            root_agent_id=system_agent.id,
            strategy="supervisor_workers",
            user_request=user_message,
            plan={"mode": "delegation_chain"},
        )

        yield {"type": "chain_start", "chain_id": chain.id, "lifecycle_stage": "plan"}

        logger.info("Chain %s started for conversation %s", chain.id, conversation_id)

        status_manager = await AgentStatusManager.get_instance()
        
        # Create the parent task early to track orchestration progress
        from app.services.task_manager import TaskManager
        tm = TaskManager(self.session)
        parent_task = await tm.create_task(
            assigned_agent_id=system_agent.id,
            prompt=user_message,
            goal="Orchestrate delegated tasks",
            conversation_id=conversation_id
        )
        await tm.update_task_state(parent_task.id, "RUNNING")
        
        status_manager.set_status(system_agent.id, AgentState.WORKING, "Analyzing request and planning...")
        yield {"type": "agent_turn_start", "agent_name": system_agent.name}
        yield {"type": "chunk", "delta": "🔍 *System Agent is analyzing the request...*\n"}

        try:
            # ── Step 1: Ask System Agent to plan ──
            non_system_agents = [a for a in channel_agents if not a.is_system]
            available_agents_desc = "\n".join([
                f"- **{a.name}**: {a.description or 'No description'}"
                for a in non_system_agents
            ])

            planning_prompt = f"""Analyze this user request and decide how to handle it.

Available agents in this channel:
{available_agents_desc}

User request: {user_message}

Respond with ONLY a JSON object (no other text):
{{
  "needs_delegation": true or false,
  "reasoning": "Brief explanation",
  "steps": [
    {{
      "group_id": 1, 
      "agent_name": "ExactAgentName", 
      "task": "task description",
      "depends_on_groups": [] 
    }}
  ],
  "aggregation_needed": true or false
}}

Rules:
- Identify tasks that can run in parallel (e.g., searching two different topics) and give them the same `group_id`.
- For tasks that depend on previous outputs (e.g. analysis after search), increment the `group_id` and list the required `group_id`s in `depends_on_groups`.
- Use exact agent names. Keep steps minimal (1-4 typically).
"""

            plan: OrchestrationPlan | None = await self._ask_system_agent(
                system_agent, planning_prompt, temperature
            )

            if not plan or not plan.needs_delegation:
                # System Agent handles directly — run its turn
                chain.state = "COMPLETED"
                chain.plan_summary = plan.reasoning if plan else "Direct response"
                await self.session.commit()

                yield {
                    "type": "orchestration_plan",
                    "plan_summary": chain.plan_summary,
                    "chain_id": chain.id,
                }

                # Let System Agent respond to the original message
                if self.chat_service:
                    async for event in self.chat_service._run_agent_turn(
                        conversation_id, system_agent, temperature, is_group=True, task_id=str(parent_task.id)
                    ):
                        yield event
                
                await tm.update_task_state(parent_task.id, "COMPLETED")

                yield {"type": "chain_complete", "chain_id": chain.id}
                return

            # ── Step 2: Store and broadcast plan ──
            chain.plan_summary = plan.reasoning
            steps = plan.steps
            agents_involved = [system_agent.id]

            # Persist DAG nodes and dependencies for replay.
            for idx, step in enumerate(steps, start=1):
                node_key = f"step_{idx}"
                from app.models.orchestration_run import OrchestrationTaskNode
                node = OrchestrationTaskNode(
                    run_id=run.id,
                    node_key=node_key,
                    type="subtask",
                    state="PENDING",
                    prompt_excerpt=step.task[:1000],
                    inputs_json=json.dumps({"group_id": step.group_id, "depends_on_groups": step.depends_on_groups}),
                )
                self.session.add(node)

            await self.session.commit()

            # Group dependency mapping: each group depends on other groups.
            group_to_node_keys: dict[int, list[str]] = {}
            for idx, step in enumerate(steps, start=1):
                group_to_node_keys.setdefault(step.group_id, []).append(f"step_{idx}")

            for idx, step in enumerate(steps, start=1):
                target = f"step_{idx}"
                for dep_group in step.depends_on_groups:
                    for source in group_to_node_keys.get(dep_group, []):
                        await tracer.add_edge(run.id, source, target)

            # ── Step 2.5: Agent Discovery & Auto-Creation ──
            # Resolve each step's agent. If not found, auto-create or reuse closest.
            from sqlalchemy import func as sa_func
            from app.services.agent_limits import can_create_agent, find_closest_agent
            from app.models.agent import new_id as agent_new_id

            agent_name_map = {a.name.lower(): a for a in channel_agents}

            for step in steps:
                step_agent_name = step.agent_name
                if step_agent_name.lower() in agent_name_map:
                    continue  # Agent exists in channel

                # Check if agent exists globally but isn't in channel
                stmt = select(Agent).where(
                    sa_func.lower(Agent.name) == step_agent_name.lower()
                )
                result = await self.session.execute(stmt)
                existing_global = result.scalar_one_or_none()

                if existing_global:
                    agent_name_map[step_agent_name.lower()] = existing_global
                    continue

                # Agent doesn't exist — try to auto-create
                allowed, reason = await can_create_agent(self.session)
                if allowed:
                    new_agent = Agent(
                        id=agent_new_id(),
                        name=step_agent_name,
                        description=f"Auto-created for: {step.task[:100]}",
                        role=step.task[:100],
                        provider="gemini",
                        model="gemini/gemini-2.5-flash",
                        system_prompt=f"You are {step_agent_name}, a specialized agent. Your task focus: {step.task}",
                        is_active=True,
                        personality_tone="professional",
                        reasoning_style="analytical",
                        groups='["auto-created"]',
                    )
                    self.session.add(new_agent)
                    await self.session.commit()
                    await self.session.refresh(new_agent)
                    agent_name_map[step_agent_name.lower()] = new_agent
                    logger.info(
                        "Auto-created agent '%s' (id=%s) for orchestration step",
                        new_agent.name, new_agent.id,
                    )
                    yield {
                        "type": "chain_update",
                        "chain_id": chain.id,
                        "chain_state": "active",
                        "current_task": f"Auto-created agent: {new_agent.name}",
                    }
                else:
                    # Limits reached — find closest existing agent
                    fallback = await find_closest_agent(
                        self.session,
                        required_role=step.task,
                    )
                    if fallback:
                        step.agent_name = fallback.name
                        agent_name_map[fallback.name.lower()] = fallback
                        logger.info(
                            "Creation limit reached. Reusing '%s' for step '%s'",
                            fallback.name, step.task,
                        )

            # Track delegation path
            delegation_path = [system_agent.id]
            for step in steps:
                agent_name_lower = step.agent_name.lower()
                if agent_name_lower in agent_name_map:
                    ag = agent_name_map[agent_name_lower]
                    if ag.id not in agents_involved:
                        agents_involved.append(ag.id)
                    if ag.id not in delegation_path:
                        delegation_path.append(ag.id)
            chain.delegation_path = json.dumps(delegation_path)

            chain.agents_involved_json = json.dumps(agents_involved)
            await self.session.commit()

            yield {
                "type": "orchestration_plan",
                "plan_summary": chain.plan_summary,
                "steps": [{"agent": s.agent_name, "task": s.task} for s in steps],
                "chain_id": chain.id,
            }

            logger.info(
                "Chain %s plan: %d steps, agents: %s",
                chain.id, len(steps),
                ", ".join(s.agent_name for s in steps),
            )

            # ── Step 3: Broadcast Active Chain State ──
            chain.depth = len(steps)
            chain.state = "active"
            await self.session.commit()

            yield {
                "type": "chain_update",
                "chain_id": chain.id,
                "chain_state": "active",
                "chain_depth": chain.depth,
                "chain_agents": agents_involved,
                "current_task": "Executing orchestration plan",
            }

            # Parent task already created at start of plan_and_execute
            from app.services.task_queue import TaskQueue
            tq = TaskQueue()
            
            # Create subtasks and enqueue them
            subtask_entries: list[dict] = []
            for step in steps:
                agent_name = step.agent_name
                ag = agent_name_map.get(agent_name.lower())
                if not ag:
                    continue

                subtask = await tm.create_subtask(
                    parent_task_id=parent_task.id,
                    assigned_agent_id=ag.id,
                    prompt=step.task,
                    goal=step.task
                )
                subtask_entries.append({
                    "agent": ag,
                    "task_id": subtask.id,
                    "task": step.task,
                })

                # Enqueue for workers to pick up
                await tq.enqueue(
                    task_id=subtask.id,
                    agent_id=ag.id,
                    prompt=step.task,
                    chain_id=chain.id
                )

            # Ensure DB changes from task creation are committed
            await self.session.commit()

            yield {
                "type": "chain_update",
                "chain_id": chain.id,
                "chain_state": "executing",
                "lifecycle_stage": "execute",
                "current_task": "Actively monitoring delegated tasks",
            }

            # ── Step 4A: Local fallback when Redis queue is unavailable ──
            if not tq.available:
                logger.warning(
                    "TaskQueue unavailable (Redis down). Falling back to parallel inline delegation for chain %s",
                    chain.id,
                )
                
                async def _run_inline_task(entry):
                    agent = entry["agent"]
                    task_id = entry["task_id"]
                    task_prompt = entry["task"]
                    try:
                        await tm.update_task_state(task_id, "RUNNING")
                        response_text, _conv_id = await self.chat_service.delegate_to_agent(
                            target_agent_id=agent.id,
                            prompt=task_prompt,
                            delegated_by=system_agent.name,
                            task_id=str(entry["task_id"]),
                        )
                        await tm.update_task_state(task_id, "COMPLETED", result=response_text)
                    except Exception as sub_exc:
                        await tm.update_task_state(task_id, "FAILED", error_message=str(sub_exc))
                        logger.warning(f"Inline task failed for {agent.name}: {sub_exc}")

                # Start all subtasks concurrently in the background
                for entry in subtask_entries:
                    asyncio.create_task(_run_inline_task(entry))

            # ── Step 4: Active Monitoring Loop (Every 2 seconds) ──
            all_completed = False # Always monitor until active_count == 0
            last_progress_state = {}

            while not all_completed:
                # Polling frequency for delegated tasks
                await asyncio.sleep(2)
                
                # Fetch fresh status for all subtasks
                subtasks = await tm.get_subtasks(parent_task.id)
                
                current_state = {}
                active_count = 0
                completed_count = 0
                failed_count = 0
                
                for t in subtasks:
                    current_state[t.id] = {
                        "status": t.status, 
                        "progress": t.progress_percent,
                        "error": t.error_message
                    }
                    if t.status in ("QUEUED", "RUNNING", "WAITING_TOOL", "WAITING_CHILD"):
                        active_count += 1
                    elif t.status == "COMPLETED":
                        completed_count += 1
                    elif t.status == "FAILED":
                        failed_count += 1

                # Yield progress updates if state changed
                if current_state != last_progress_state:
                    last_progress_state = current_state
                    
                    # Compute simplified agent progress strings for UI
                    # e.g. "Data Analyst - Running (60%)"
                    progress_lines = []
                    for entry in subtask_entries:
                        name = entry["agent"].name
                        tid = entry["task_id"]
                        state = current_state.get(tid)
                        if not state:
                            continue
                        if state['status'] == 'COMPLETED':
                            progress_lines.append(f"{name} — Completed")
                        elif state['status'] == 'FAILED':
                            progress_lines.append(f"{name} — Failed: {state.get('error')}")
                        elif state['status'] == 'QUEUED':
                            progress_lines.append(f"{name} — Pending")
                        else:
                            progress_lines.append(f"{name} — Running ({state.get('progress')}%)")
                    
                    yield {
                        "type": "task_progress",
                        "chain_id": chain.id,
                        "progress": int((completed_count / len(subtasks)) * 100) if subtasks else 0,
                        "status_lines": progress_lines
                    }

                if active_count == 0:
                    all_completed = True

            # ── Step 5: Verify & Synthesize final response ──
            yield {
                "type": "chain_update",
                "chain_id": chain.id,
                "chain_state": "verifying",
                "lifecycle_stage": "verify",
                "current_task": "Aggregating subtask results",
            }
            
            # Gather final results
            subtasks = await tm.get_subtasks(parent_task.id)
            payload = {}
            for t in subtasks:
                agent = await self.session.get(Agent, t.assigned_agent_id)
                if agent:
                    if t.status == "COMPLETED":
                        payload[f"agent_{agent.name}_response"] = t.result
                    else:
                        error_msg = t.error_message or "Unknown failure"
                        payload[f"agent_{agent.name}_response"] = f"AGENT {agent.name} FAILED: {error_msg}. Please proceed with remaining data or decide if synthesis is possible."
            
            await tm.update_task_state(parent_task.id, "COMPLETED")

            if plan.aggregation_needed and len(steps) > 1:
                from app.services.conversation_service import ConversationService
                conv_svc = ConversationService(self.session)

                synthesis_parts = []
                for s in steps:
                    name = s.get("agent_name")
                    resp = payload.get(f"agent_{name}_response")
                    if resp:
                        synthesis_parts.append(f"**{name}**:\n{resp}")

                if synthesis_parts:
                    synthesis_prompt = (
                        f"The following agents have completed their tasks for the user's request: \"{user_message}\"\n\n"
                        f"{chr(10).join(synthesis_parts)}\n\n"
                        "Please synthesize their outputs into a single, coherent response for the user."
                    )

                    await conv_svc.add_message(
                        conversation_id, "user",
                        f"[System]: {synthesis_prompt}",
                        agent_name="System",
                    )

                    if self.chat_service:
                        async for event in self.chat_service._run_agent_turn(
                            conversation_id, system_agent, temperature, is_group=True, task_id=str(parent_task.id)
                        ):
                            yield event

            chain.state = "COMPLETED"
            await self.session.commit()

            # Broadcast chain completion via heartbeat
            try:
                from app.services.agent_heartbeat import AgentHeartbeatService
                hb = await AgentHeartbeatService.get_instance()
                await hb.update_chain_state(chain.id, chain.depth, agents_involved, "completed")
            except Exception:
                pass

            yield {"type": "chain_complete", "chain_id": chain.id}

            logger.info(
                "Chain %s completed: depth=%d, agents=%s",
                chain.id, chain.depth, chain.agents_involved_json,
            )

        except GeneratorExit:
            logger.info("Chain %s: generator closed (user stopped generation)", chain.id)
            chain.state = "cancelled"
            await self.session.commit()
            if 'parent_task' in locals():
                await tm.update_task_state(parent_task.id, "CANCELED")

        except Exception as exc:
            logger.error("Orchestration chain %s failed: %s", chain.id, exc, exc_info=True)
            chain.state = "failed"
            await self.session.commit()
            yield {"type": "chain_update", "chain_id": chain.id, "chain_state": "failed"}
            yield {"type": "chain_complete", "chain_id": chain.id}
            if 'parent_task' in locals():
                await tm.update_task_state(parent_task.id, "FAILED", error_message=str(exc))
        finally:
            status_manager.set_status(system_agent.id, AgentState.IDLE)

    async def _ask_system_agent(
        self, system_agent: Agent, prompt: str, temperature: float = 0.3
    ) -> OrchestrationPlan | None:
        """Ask the System Agent a question and return the text response (non-streaming)."""
        if not self.chat_service:
            return ""

        # Use the same robust resolution logic as ChatService for consistency and fallbacks
        _p_name, model_id, provider, _warning = await self.chat_service._resolve_provider_and_model(system_agent.model)

        # Use agent's own API key if set (ephemeral provider)
        if system_agent.api_key:
            provider = self.providers.create_ephemeral(system_agent.provider, system_agent.api_key)

        messages = [
            ChatMessage(role="system", content=(
                "You are a task orchestrator with deep capability analysis. "
                "Analyze requests and produce structured JSON plans. "
                "Match tasks to agents based on their capabilities and past performance. "
                "Respond ONLY with valid JSON, no extra text."
            )),
            ChatMessage(role="user", content=prompt),
        ]

        try:
            from app.services.llm_gateway import get_gateway
            gateway = await get_gateway(self.providers)
            
            # Use structured output if the provider/model supports it
            kwargs = {
                "temperature": temperature,
            }
            if provider.name == "gemini":
                kwargs["response_format"] = {"type": "json_object"}
                kwargs["response_schema"] = OrchestrationPlan.model_json_schema()

            result = await gateway.complete(provider, messages, model_id, system_agent.id, self.session, **kwargs)
            
            if not result or not result.content:
                return None
                
            # Parse the structured response back into the Pydantic model
            try:
                return OrchestrationPlan.model_validate_json(result.content)
            except Exception as pe:
                logger.error(f"Failed to validate orchestration plan: {pe}. Content: {result.content}")
                return None

        except Exception as e:
            logger.exception(f"Error calling system agent '{system_agent.name}' for planning: {e}")
            return None

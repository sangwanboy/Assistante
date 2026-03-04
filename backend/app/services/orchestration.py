"""Orchestration engine for System Agent auto-delegation.

When no @mentions are present and orchestration_mode is "autonomous",
the System Agent analyzes the task, produces a delegation plan,
chains agent execution, and synthesizes a final response.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.task import Task
from app.models.chain import DelegationChain
from app.providers.base import ChatMessage
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry
from app.services.agent_status import AgentStatusManager, AgentState

logger = logging.getLogger(__name__)


def detect_circular_invocation(agents_involved: list[str], new_agent_id: str) -> bool:
    """Returns True if adding new_agent_id would create a cycle."""
    return new_agent_id in agents_involved


def check_depth(current_depth: int, max_depth: int) -> bool:
    """Returns True if depth limit is exceeded."""
    return current_depth >= max_depth


def _extract_json_from_text(text: str) -> dict | None:
    """Try to extract a JSON object from LLM text output."""
    # Try the whole text first
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    # Try to find JSON block in markdown code fence
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass
    # Try to find first { ... } block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    return None


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
        3. Execute each step, feeding outputs forward
        4. Have System Agent synthesize final response
        """
        # Create a DelegationChain record
        chain = DelegationChain(
            conversation_id=conversation_id,
            max_depth=5,
        )
        self.session.add(chain)
        await self.session.commit()
        await self.session.refresh(chain)

        yield {"type": "chain_start", "chain_id": chain.id}

        logger.info("Chain %s started for conversation %s", chain.id, conversation_id)

        status_manager = await AgentStatusManager.get_instance()

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
  "reasoning": "Brief explanation of your decision",
  "steps": [
    {{"agent_name": "ExactAgentName", "task": "specific task description for this agent"}}
  ],
  "aggregation_needed": true or false
}}

Rules:
- If this is a simple question you can answer directly, set needs_delegation=false and steps=[].
- If agents are needed, assign specific sub-tasks to the most appropriate agent(s).
- Use exact agent names from the list above.
- Keep the number of steps minimal (1-3 agents typically).
"""

            plan_json = await self._ask_system_agent(
                system_agent, planning_prompt, temperature
            )
            plan = _extract_json_from_text(plan_json)

            if not plan or not plan.get("needs_delegation"):
                # System Agent handles directly — run its turn
                chain.state = "completed"
                chain.plan_summary = plan.get("reasoning", "Handling directly") if plan else "Direct response"
                await self.session.commit()

                yield {
                    "type": "orchestration_plan",
                    "plan_summary": chain.plan_summary,
                    "chain_id": chain.id,
                }

                # Let System Agent respond to the original message
                if self.chat_service:
                    async for event in self.chat_service._run_agent_turn(
                        conversation_id, system_agent, temperature, is_group=True
                    ):
                        yield event

                yield {"type": "chain_complete", "chain_id": chain.id}
                return

            # ── Step 2: Store and broadcast plan ──
            chain.plan_summary = plan.get("reasoning", "")
            steps = plan.get("steps", [])
            agents_involved = [system_agent.id]
            chain.agents_involved_json = json.dumps(agents_involved)
            await self.session.commit()

            yield {
                "type": "orchestration_plan",
                "plan_summary": chain.plan_summary,
                "steps": [{"agent": s.get("agent_name"), "task": s.get("task")} for s in steps],
                "chain_id": chain.id,
            }

            logger.info(
                "Chain %s plan: %d steps, agents: %s",
                chain.id, len(steps),
                ", ".join(s.get("agent_name", "?") for s in steps),
            )

            # ── Step 3: Execute delegation steps ──
            agent_results = []
            for i, step in enumerate(steps):
                target_name = step.get("agent_name", "")
                task_prompt = step.get("task", "")

                # Resolve agent by name
                target_agent = None
                for a in non_system_agents:
                    if a.name.lower() == target_name.lower():
                        target_agent = a
                        break

                if not target_agent:
                    agent_results.append({
                        "agent_name": target_name,
                        "result": f"Agent '{target_name}' not found in channel.",
                        "status": "failed",
                    })
                    continue

                # Check depth and circular invocation
                if check_depth(chain.depth + 1, chain.max_depth):
                    logger.warning("Chain %s: Max depth reached at step %d", chain.id, i)
                    chain.state = "halted"
                    await self.session.commit()
                    yield {"type": "chain_update", "chain_id": chain.id, "chain_state": "halted",
                           "chain_depth": chain.depth, "chain_agents": agents_involved}
                    break

                if detect_circular_invocation(agents_involved, target_agent.id):
                    agent_results.append({
                        "agent_name": target_name,
                        "result": f"Circular delegation detected — {target_name} already involved.",
                        "status": "skipped",
                    })
                    continue

                # Create Task record
                task = Task(
                    chain_id=chain.id,
                    assigned_agent_id=target_agent.id,
                    conversation_id=conversation_id,
                    status="running",
                    prompt=task_prompt,
                    timeout_seconds=60,
                    started_at=datetime.now(timezone.utc),
                )
                self.session.add(task)
                await self.session.commit()
                await self.session.refresh(task)

                # Update chain tracking
                agents_involved.append(target_agent.id)
                chain.depth += 1
                chain.agents_involved_json = json.dumps(agents_involved)
                await self.session.commit()

                yield {
                    "type": "chain_update",
                    "chain_id": chain.id,
                    "chain_state": "active",
                    "chain_depth": chain.depth,
                    "chain_agents": agents_involved,
                    "current_agent": target_agent.name,
                    "current_task": task_prompt,
                }

                # Build context from previous results
                context_parts = []
                for prev in agent_results:
                    if prev.get("status") == "completed":
                        context_parts.append(f"[{prev['agent_name']}]: {prev['result']}")

                full_prompt = task_prompt
                if context_parts:
                    full_prompt = (
                        "Context from previous agents:\n"
                        + "\n".join(context_parts)
                        + f"\n\nYour task: {task_prompt}"
                    )

                # Inject the task prompt as a user message in conversation
                from app.services.conversation_service import ConversationService
                conv_svc = ConversationService(self.session)
                await conv_svc.add_message(
                    conversation_id, "user",
                    f"[System → {target_agent.name}]: {full_prompt}",
                    agent_name="System",
                )

                # Run the agent's turn
                collected_response = ""
                if self.chat_service:
                    async for event in self.chat_service._run_agent_turn(
                        conversation_id, target_agent, temperature, is_group=True
                    ):
                        yield event
                        if event.get("type") == "chunk":
                            collected_response += event.get("delta", "")

                # Update task record
                task.status = "completed"
                task.result = collected_response[:2000]  # Truncate for DB
                task.progress = 100
                task.completed_at = datetime.now(timezone.utc)
                await self.session.commit()

                agent_results.append({
                    "agent_name": target_agent.name,
                    "result": collected_response,
                    "status": "completed",
                })

                logger.info(
                    "Chain %s step %d completed: agent=%s, task=%s",
                    chain.id, i, target_agent.name, task_prompt[:80],
                )

                # Reset failure count on success
                try:
                    from app.services.agent_heartbeat import AgentHeartbeatService
                    hb = await AgentHeartbeatService.get_instance()
                    await hb.reset_failure_count(target_agent.id)
                except Exception:
                    pass

            # ── Step 4: Synthesize final response (if aggregation needed) ──
            completed_results = [r for r in agent_results if r.get("status") == "completed"]

            if plan.get("aggregation_needed") and len(completed_results) > 1:
                synthesis_parts = "\n\n".join([
                    f"**{r['agent_name']}**:\n{r['result']}" for r in completed_results
                ])
                synthesis_prompt = (
                    f"The following agents have completed their tasks for the user's request: \"{user_message}\"\n\n"
                    f"{synthesis_parts}\n\n"
                    "Please synthesize their outputs into a single, coherent response for the user."
                )

                await conv_svc.add_message(
                    conversation_id, "user",
                    f"[System]: {synthesis_prompt}",
                    agent_name="System",
                )

                if self.chat_service:
                    async for event in self.chat_service._run_agent_turn(
                        conversation_id, system_agent, temperature, is_group=True
                    ):
                        yield event

            # ── Finalize chain ──
            chain.state = "completed"
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

        except Exception as exc:
            logger.error("Orchestration chain %s failed: %s", chain.id, exc, exc_info=True)
            chain.state = "failed"
            await self.session.commit()
            yield {"type": "chain_update", "chain_id": chain.id, "chain_state": "failed"}
            yield {"type": "chain_complete", "chain_id": chain.id}

    async def _ask_system_agent(
        self, system_agent: Agent, prompt: str, temperature: float = 0.3
    ) -> str:
        """Ask the System Agent a question and return the text response (non-streaming)."""
        provider_name, model_id = self.chat_service._parse_model_string(system_agent.model)
        provider = self.providers.get(provider_name)
        if not provider:
            return ""

        messages = [
            ChatMessage(role="system", content=(
                "You are a task orchestrator. Analyze requests and produce structured JSON plans. "
                "Respond ONLY with valid JSON, no extra text."
            )),
            ChatMessage(role="user", content=prompt),
        ]

        result = await provider.complete(messages, model_id, temperature=temperature)
        return result.content if result else ""

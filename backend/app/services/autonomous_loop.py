"""Autonomous Execution Loop — PLAN → ACT → OBSERVE → REFLECT → UPDATE PLAN.

Transforms agents from single-response bots into multi-step task workers.
Each "step" in the loop can involve a full agent turn (with tool calls),
followed by LLM-driven observation and reflection.

Uses the existing Task model's limits (max_steps, max_tool_calls, max_tokens)
to prevent runaway execution.
"""

import logging
from typing import AsyncIterator
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.task import Task
from app.providers.base import ChatMessage
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry
from app.services.agent_status import AgentStatusManager, AgentState

logger = logging.getLogger(__name__)


class AutonomousExecutionLoop:
    """Runs a continuous PLAN → ACT → OBSERVE → REFLECT cycle for an agent task.

    This sits *above* _run_agent_turn: each "step" in this loop is a full
    agent turn that may include multiple tool calls. Between steps, the loop
    asks the LLM to observe the result, reflect on progress, and decide
    whether to continue or declare the task complete.
    """

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

    async def run(
        self,
        task: Task,
        agent: Agent,
        conversation_id: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[dict]:
        """Execute the autonomous loop for a task.

        Yields streaming events (chunks, tool_calls, etc.) that can be piped
        to the WebSocket or to the orchestration event queue.
        """
        max_steps = task.max_steps or 15
        max_tool_calls = task.max_tool_calls or 20
        total_tool_calls = 0

        # Timeout protection
        started_at = datetime.now(timezone.utc)
        max_runtime_seconds = task.timeout_seconds or 600  # 10 min default

        status_manager = await AgentStatusManager.get_instance()
        agent_id = agent.id

        # Track step history for reflection
        step_history: list[dict] = []

        yield {
            "type": "autonomous_start",
            "agent_name": agent.name,
            "task_goal": task.goal or task.prompt,
            "max_steps": max_steps,
        }

        task.status = "running"
        task.started_at = started_at
        await self.session.commit()

        # ── Create persistent workspace for this task ──
        from app.services.workspace_manager import WorkspaceManager
        workspace_mgr = WorkspaceManager()
        workspace_path = workspace_mgr.create(str(task.id))
        logger.info("Task %s: workspace created at %s", task.id, workspace_path)

        try:
            for step_num in range(1, max_steps + 1):
                # ── CONVERSATION DEPTH CHECK ──
                if step_num > 6:
                    logger.warning(
                        "Task %s: conversation depth limit reached at step %d",
                        task.id, step_num,
                    )
                    yield {
                        "type": "autonomous_depth_limit",
                        "agent_name": agent.name,
                        "step": step_num,
                    }
                    break

                # ── TIMEOUT CHECK ──
                elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
                if elapsed > max_runtime_seconds:
                    logger.warning(
                        "Task %s timed out after %.1fs (limit: %ds)",
                        task.id, elapsed, max_runtime_seconds,
                    )
                    yield {
                        "type": "autonomous_timeout",
                        "agent_name": agent.name,
                        "step": step_num,
                        "elapsed": elapsed,
                    }
                    break

                # ── TOOL CALL BUDGET CHECK ──
                if total_tool_calls >= max_tool_calls:
                    logger.warning(
                        "Task %s exceeded tool call budget (%d/%d)",
                        task.id, total_tool_calls, max_tool_calls,
                    )
                    yield {
                        "type": "autonomous_budget_exceeded",
                        "agent_name": agent.name,
                        "step": step_num,
                        "tool_calls_used": total_tool_calls,
                    }
                    break

                # ── STEP 1: PLAN ──
                # On first step, use original task prompt. On subsequent steps,
                # inject reflection history so the agent knows what happened.
                status_manager.set_status(
                    agent_id, AgentState.WORKING,
                    f"Autonomous step {step_num}/{max_steps}: Planning..."
                )

                if step_num > 1 and step_history:
                    # Build a reflection prompt from the history
                    reflection_summary = self._build_history_summary(step_history)
                    plan_prompt = (
                        f"You are continuing an autonomous task. Here is your progress so far:\n\n"
                        f"{reflection_summary}\n\n"
                        f"Original goal: {task.goal or task.prompt}\n\n"
                        f"Step {step_num}/{max_steps}. "
                        f"Tool calls used: {total_tool_calls}/{max_tool_calls}. "
                        f"Time elapsed: {elapsed:.0f}s/{max_runtime_seconds}s.\n\n"
                        f"Continue working on the task. If the task is COMPLETE, "
                        f"respond with a final summary and do NOT call any tools."
                    )

                    from app.services.conversation_service import ConversationService
                    conv_svc = ConversationService(self.session)
                    await conv_svc.add_message(
                        conversation_id, "user",
                        f"[System — Autonomous Step {step_num}]: {plan_prompt}",
                        agent_name="System",
                    )

                yield {
                    "type": "autonomous_step_start",
                    "agent_name": agent.name,
                    "step": step_num,
                    "max_steps": max_steps,
                }

                # ── STEP 2: ACT — Run a full agent turn ──
                step_output = ""
                step_tool_calls = 0
                has_tool_calls = False

                if self.chat_service:
                    async for event in self.chat_service._run_agent_turn(
                        conversation_id, agent, temperature,
                        max_tool_iters=min(5, max_tool_calls - total_tool_calls),
                        is_group=True,
                    ):
                        yield event
                        # Track output
                        if event.get("type") == "chunk" and event.get("delta"):
                            step_output += str(event.get("delta", ""))
                        if event.get("type") == "tool_call":
                            step_tool_calls += 1
                            has_tool_calls = True

                total_tool_calls += step_tool_calls

                # ── STEP 3: OBSERVE — Record what happened ──
                observation = {
                    "step": step_num,
                    "output_preview": step_output[:500],
                    "tool_calls_in_step": step_tool_calls,
                    "had_tool_calls": has_tool_calls,
                }
                step_history.append(observation)

                # Update task progress
                task.step_count = step_num
                task.progress = min(100, int((step_num / max_steps) * 100))
                await self.session.commit()

                yield {
                    "type": "autonomous_step_end",
                    "agent_name": agent.name,
                    "step": step_num,
                    "tool_calls_in_step": step_tool_calls,
                    "total_tool_calls": total_tool_calls,
                    "progress": task.progress,
                }

                # ── STEP 4: REFLECT — Check if the task is complete ──
                if not has_tool_calls:
                    # Agent responded without using tools → likely done
                    logger.info(
                        "Task %s: agent responded without tools at step %d — treating as complete",
                        task.id, step_num,
                    )
                    break

                # Ask the LLM if the task is done (cheap, fast check)
                is_complete = await self._check_completion(
                    agent, task, step_history, step_output
                )
                if is_complete:
                    logger.info("Task %s: completion detected at step %d", task.id, step_num)
                    break

            # ── TASK COMPLETED ──
            task.status = "completed"
            task.progress = 100
            task.completed_at = datetime.now(timezone.utc)
            await self.session.commit()

            yield {
                "type": "autonomous_reflecting",
                "agent_name": agent.name,
            }
            
            # ── REFLECT on the task loop ──
            from app.services.reflection_service import ReflectionService
            reflector = ReflectionService(self.session, self.providers)
            await reflector.reflect_on_task(agent, task, step_history)

            status_manager.set_status(agent_id, AgentState.IDLE)

            yield {
                "type": "autonomous_complete",
                "agent_name": agent.name,
                "steps_taken": task.step_count,
                "tool_calls_total": total_tool_calls,
                "status": "completed",
            }

        except Exception as exc:
            logger.error("Autonomous loop for task %s failed: %s", task.id, exc, exc_info=True)
            task.status = "failed"
            task.completed_at = datetime.now(timezone.utc)
            await self.session.commit()

            yield {
                "type": "autonomous_reflecting",
                "agent_name": agent.name,
            }
            
            # ── REFLECT on the failure ──
            from app.services.reflection_service import ReflectionService
            reflector = ReflectionService(self.session, self.providers)
            await reflector.reflect_on_task(agent, task, step_history)

            status_manager.set_status(agent_id, AgentState.IDLE)

            yield {
                "type": "autonomous_error",
                "agent_name": agent.name,
                "error": str(exc),
                "step": task.step_count,
            }

    async def _check_completion(
        self,
        agent: Agent,
        task: Task,
        history: list[dict],
        last_output: str,
    ) -> bool:
        """Ask the LLM whether the task is complete.

        Uses a lightweight prompt — no tools, low temperature.
        Returns True if the task should stop.
        """
        try:
            provider_name, model_id = self.chat_service._parse_model_string(agent.model)
            provider = self.providers.get(provider_name)
            if not provider:
                return False

            history_text = self._build_history_summary(history)

            check_prompt = (
                f"You are evaluating if an autonomous task is complete.\n\n"
                f"Task goal: {task.goal or task.prompt}\n\n"
                f"Steps taken so far:\n{history_text}\n\n"
                f"Last agent output (preview):\n{last_output[:800]}\n\n"
                f"Is this task COMPLETE? Respond with ONLY 'YES' or 'NO'."
            )

            messages = [
                ChatMessage(role="system", content="You are a task completion evaluator. Respond with only YES or NO."),
                ChatMessage(role="user", content=check_prompt),
            ]

            result = await provider.complete(messages, model_id, temperature=0.1)
            answer = (result.content or "").strip().upper()
            return answer.startswith("YES")

        except Exception as exc:
            logger.warning("Completion check failed: %s — continuing loop", exc)
            return False

    def _build_history_summary(self, history: list[dict]) -> str:
        """Build a compact text summary of step history for the reflection prompt."""
        lines = []
        for entry in history:
            step = entry["step"]
            tools = entry["tool_calls_in_step"]
            preview = entry["output_preview"]
            # Keep it compact
            if tools > 0:
                lines.append(f"Step {step}: Used {tools} tool(s). Output: {preview[:200]}...")
            else:
                lines.append(f"Step {step}: Responded without tools. Output: {preview[:200]}...")
        return "\n".join(lines)

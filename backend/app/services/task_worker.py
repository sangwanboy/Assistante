"""Distributed Task Worker (Section 5).

Background worker that polls the task queue and dispatches work to agents.
Agents must not call each other directly — tasks flow through:
  System Agent → Task Planner → Task Queue → Agent Workers
"""

import asyncio
import json
import logging
import time

from sqlalchemy import select

from app.db.engine import async_session
from app.models.task import Task
from app.models.agent import Agent

logger = logging.getLogger(__name__)


class TaskWorker:
    """Background worker that dequeues tasks and dispatches to agents."""

    def __init__(self, redis_client=None):
        self._running = False
        # Extract the raw aioredis.Redis client (None if Redis unavailable)
        self._redis = redis_client.redis if redis_client and redis_client.available else None
        self._current_tasks: dict[str, asyncio.Task] = {}
        self._max_concurrent = 5
        self._poll_interval = 0.5  # seconds

    async def start(self):
        """Start the worker loop."""
        if not self._redis:
            logger.warning("TaskWorker: Redis unavailable — worker disabled (in-memory fallback)")
            return

        self._running = True
        logger.info("TaskWorker started (max_concurrent=%d)", self._max_concurrent)

        while self._running:
            try:
                # Clean up finished tasks
                finished = [tid for tid, t in self._current_tasks.items() if t.done()]
                for tid in finished:
                    task = self._current_tasks.pop(tid)
                    if task.exception():
                        logger.error("Task %s failed: %s", tid, task.exception())

                # Check if we have capacity
                if len(self._current_tasks) >= self._max_concurrent:
                    await asyncio.sleep(self._poll_interval)
                    continue

                # Try to dequeue a task
                task_data = await self._dequeue()
                if task_data:
                    task_id = task_data.get("task_id")
                    if task_id and task_id not in self._current_tasks:
                        # Claim the task with distributed lock
                        claimed = await self._claim_task(task_id)
                        if claimed:
                            coro = self._execute_task(task_data)
                            self._current_tasks[task_id] = asyncio.create_task(coro)
                else:
                    await asyncio.sleep(self._poll_interval)

            except Exception as e:
                logger.error("TaskWorker loop error: %s", e)
                await asyncio.sleep(1.0)

    async def stop(self):
        """Stop the worker and wait for current tasks to finish."""
        self._running = False
        if self._current_tasks:
            logger.info("TaskWorker stopping, waiting for %d tasks...", len(self._current_tasks))
            await asyncio.gather(*self._current_tasks.values(), return_exceptions=True)
        logger.info("TaskWorker stopped")

    async def _dequeue(self) -> dict | None:
        """Dequeue a task from the priority queue."""
        try:
            # Use ZPOPMIN for priority queue (lowest score = highest priority)
            result = await self._redis.zpopmin("assitance:task_queue:priority", count=1)
            if result:
                task_json, _score = result[0]
                return json.loads(task_json)

            # Fallback to standard queue
            result = await self._redis.lpop("assitance:task_queue")
            if result:
                return json.loads(result)
        except Exception as e:
            logger.error("Dequeue error: %s", e)
        return None

    async def _claim_task(self, task_id: str) -> bool:
        """Claim a task using distributed lock (SETNX)."""
        try:
            lock_key = f"assitance:task_lock:{task_id}"
            acquired = await self._redis.set(lock_key, "claimed", nx=True, ex=600)
            return bool(acquired)
        except Exception as e:
            logger.error("Failed to claim task %s: %s", task_id, e)
            return False

    async def _execute_task(self, task_data: dict):
        """Execute a task by dispatching to the assigned agent."""
        task_id = task_data.get("task_id")
        agent_id = task_data.get("agent_id")
        prompt = task_data.get("prompt", "")

        start_time = time.time()
        logger.info("Executing task %s for agent %s", task_id, agent_id)

        try:
            from app.services.task_manager import TaskManager
            
            async with async_session() as session:
                tm = TaskManager(session)
                task = await tm.get_task(task_id)
                agent = await session.get(Agent, agent_id)

                if not task or not agent:
                    logger.error("Task %s or agent %s not found", task_id, agent_id)
                    await self._move_to_dead_letter(task_data, "Task or agent not found")
                    return

                # Update task status via TaskManager (fires task_started)
                await tm.update_task_state(task_id, "running")

            # Execute the agent task via the autonomous loop or direct chat
            result = await self._run_agent_task(agent_id, task_id, prompt)

            async with async_session() as session:
                tm = TaskManager(session)
                task = await tm.get_task(task_id)
                if task:
                    await tm.update_task_state(task_id, "completed", result=result)

            elapsed = time.time() - start_time
            logger.info("Task %s completed in %.1fs", task_id, elapsed)

            # Update performance metrics
            try:
                from app.services.capability_registry import CapabilityRegistry
                registry = CapabilityRegistry.get_instance()
                await registry.update_performance_metrics(agent_id, success=True, completion_time=elapsed)
            except Exception:
                pass

        except Exception as e:
            logger.error("Task %s execution failed: %s", task_id, e)
            async with async_session() as session:
                tm = TaskManager(session)
                await tm.update_task_state(task_id, "failed", error_message=str(e))
            await self._handle_task_failure(task_data, str(e))

        finally:
            # Release lock
            try:
                await self._redis.delete(f"assitance:task_lock:{task_id}")
            except Exception:
                pass

    async def _run_agent_task(self, agent_id: str, task_id: str, prompt: str) -> str:
        """Run agent task via the autonomous execution loop with timeout protection."""
        try:
            from app.services.autonomous_loop import AutonomousExecutionLoop
            from app.services.chat_service import ChatService
            from app.providers.registry import ProviderRegistry
            from app.tools.registry import ToolRegistry
            from app.models.conversation import Conversation
            import uuid

            async with async_session() as session:
                task = await session.get(Task, task_id)
                agent = await session.get(Agent, agent_id)
                if not task or not agent:
                    return "Task or agent not found"

                # Find or create a conversation for this task
                conv_result = await session.execute(
                    select(Conversation).where(Conversation.agent_id == agent_id).limit(1)
                )
                conv = conv_result.scalar_one_or_none()
                if not conv:
                    conv = Conversation(
                        id=str(uuid.uuid4()),
                        title=f"Task: {task_id[:8]}",
                        agent_id=agent_id,
                        model=agent.model or "gemini/gemini-2.5-flash",
                    )
                    session.add(conv)
                    await session.commit()
                    await session.refresh(conv)

                provider_registry = ProviderRegistry()
                tool_registry = ToolRegistry()
                chat_service = ChatService(
                    provider_registry=provider_registry,
                    tool_registry=tool_registry,
                    session=session,
                )

                loop = AutonomousExecutionLoop(
                    session=session,
                    provider_registry=provider_registry,
                    tool_registry=tool_registry,
                    chat_service=chat_service,
                )

                last_output = ""

                async def _consume_loop():
                    nonlocal last_output
                    async for event in loop.run(task, agent, conv.id):
                        event_type = event.get("type", "")
                        if event_type == "autonomous_complete":
                            break
                        if event_type == "autonomous_error":
                            return f"Task failed: {event.get('error')}"
                        if event_type == "chunk" and event.get("delta"):
                            last_output += event["delta"]
                    return last_output or "Task completed"

                result = await asyncio.wait_for(_consume_loop(), timeout=600)
                return result
        except asyncio.TimeoutError:
            return "Task timed out after 600 seconds"
        except Exception as e:
            logger.error("Agent task execution error: %s", e)
            return f"Task failed: {e}"

    async def _handle_task_failure(self, task_data: dict, error: str):
        """Handle task failure with retry or dead-letter routing."""
        task_id = task_data.get("task_id")

        async with async_session() as session:
            task = await session.get(Task, task_id)
            if not task:
                return

            task.retry_count += 1
            if task.retry_count < task.max_retries:
                # Retry with exponential backoff
                backoff = min(2 ** task.retry_count * 5, 60)  # 5s, 10s, 20s, max 60s
                task.status = "retrying"
                await session.commit()

                logger.info("Retrying task %s in %ds (attempt %d/%d)",
                            task_id, backoff, task.retry_count, task.max_retries)

                await asyncio.sleep(backoff)

                # Re-enqueue
                try:
                    await self._redis.rpush(
                        "assitance:task_queue",
                        json.dumps(task_data),
                    )
                except Exception as e:
                    logger.error("Failed to re-enqueue task %s: %s", task_id, e)
            else:
                # Move to dead-letter queue
                task.status = "failed"
                task.result = f"Failed after {task.max_retries} retries: {error}"
                await session.commit()
                await self._move_to_dead_letter(task_data, error)

    async def _move_to_dead_letter(self, task_data: dict, error: str):
        """Move a permanently failed task to the dead-letter queue."""
        try:
            task_data["error"] = error
            task_data["dead_letter_at"] = time.time()
            await self._redis.rpush(
                "assitance:dead_letter",
                json.dumps(task_data),
            )
            logger.warning("Task %s moved to dead-letter queue: %s",
                          task_data.get("task_id"), error)
        except Exception as e:
            logger.error("Failed to move task to dead-letter: %s", e)

    async def get_queue_stats(self) -> dict:
        """Return current queue statistics."""
        if not self._redis:
            return {"error": "No Redis client"}

        try:
            queue_len = await self._redis.llen("assitance:task_queue") or 0
            priority_len = await self._redis.zcard("assitance:task_queue:priority") or 0
            dead_letter_len = await self._redis.llen("assitance:dead_letter") or 0

            return {
                "queue_depth": queue_len + priority_len,
                "priority_queue": priority_len,
                "standard_queue": queue_len,
                "dead_letter": dead_letter_len,
                "active_tasks": len(self._current_tasks),
                "max_concurrent": self._max_concurrent,
            }
        except Exception as e:
            return {"error": str(e)}

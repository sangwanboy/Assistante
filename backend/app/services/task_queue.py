"""Redis-backed task queue for agent delegation pipeline.

Provides enqueue/dequeue, progress tracking, timeout management,
distributed locking, priority levels, and dead-letter queue
for delegated agent tasks.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Timeout strategy by task type (seconds)
TIMEOUT_MAP = {
    "quick_query": 15,
    "code_gen": 60,
    "analysis": 120,
    "research": 180,
    "default": 60,
}

# Priority levels (lower = higher priority)
PRIORITY_URGENT = 0
PRIORITY_NORMAL = 5
PRIORITY_LOW = 10


class TaskQueue:
    """Redis-backed task queue with priority, locking, and dead-letter support."""

    QUEUE_KEY = "assitance:task_queue"
    PRIORITY_QUEUE_KEY = "assitance:priority_queue"
    TASK_STATE_PREFIX = "assitance:task:"
    LOCK_PREFIX = "assitance:lock:"
    DEAD_LETTER_KEY = "assitance:dead_letter"

    def __init__(self, redis_client=None):
        """Initialize with an optional RedisClient instance."""
        self._redis = redis_client.redis if redis_client and redis_client.available else None

    @property
    def available(self) -> bool:
        return self._redis is not None

    async def enqueue(
        self,
        task_id: str,
        agent_id: str,
        prompt: str,
        chain_id: str | None = None,
        priority: int = PRIORITY_NORMAL,
    ):
        """Add a task to the priority queue using ZADD."""
        if not self._redis:
            return
        payload = json.dumps({
            "task_id": task_id,
            "agent_id": agent_id,
            "prompt": prompt,
            "chain_id": chain_id,
            "priority": priority,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            # Use sorted set with priority as score (lower = dequeued first)
            await self._redis.zadd(self.PRIORITY_QUEUE_KEY, {payload: priority})
            await self._redis.setex(
                f"{self.TASK_STATE_PREFIX}{task_id}", 300, json.dumps({"status": "queued"})
            )
            logger.debug("Task %s enqueued with priority %d", task_id, priority)
        except Exception as exc:
            logger.debug("Task enqueue failed for %s: %s", task_id, exc)

    async def dequeue(self, agent_id: str | None = None) -> dict | None:
        """Dequeue the highest-priority task using ZPOPMIN with distributed locking.

        Returns the task payload dict, or None if queue is empty or lock fails.
        """
        if not self._redis:
            return None
        try:
            # Pop lowest score (highest priority) item
            results = await self._redis.zpopmin(self.PRIORITY_QUEUE_KEY, count=1)
            if not results:
                return None

            payload_str, _score = results[0]
            if isinstance(payload_str, bytes):
                payload_str = payload_str.decode()
            payload = json.loads(payload_str)
            task_id = payload.get("task_id")

            # Attempt distributed lock (SETNX)
            lock_key = f"{self.LOCK_PREFIX}{task_id}"
            acquired = await self._redis.set(lock_key, agent_id or "worker", nx=True, ex=300)
            if not acquired:
                # Another worker already claimed this task
                logger.debug("Task %s already locked by another worker", task_id)
                return None

            # Update state to claimed
            await self._redis.setex(
                f"{self.TASK_STATE_PREFIX}{task_id}", 300,
                json.dumps({"status": "claimed", "claimed_by": agent_id, "claimed_at": datetime.now(timezone.utc).isoformat()})
            )
            return payload
        except Exception as exc:
            logger.debug("Task dequeue failed: %s", exc)
            return None

    async def release_lock(self, task_id: str):
        """Release the distributed lock for a task."""
        if not self._redis:
            return
        try:
            await self._redis.delete(f"{self.LOCK_PREFIX}{task_id}")
        except Exception:
            pass

    async def move_to_dead_letter(self, task_id: str, reason: str):
        """Move a failed task to the dead-letter queue."""
        if not self._redis:
            return
        try:
            payload = json.dumps({
                "task_id": task_id,
                "reason": reason,
                "moved_at": datetime.now(timezone.utc).isoformat(),
            })
            await self._redis.lpush(self.DEAD_LETTER_KEY, payload)
            await self._redis.setex(
                f"{self.TASK_STATE_PREFIX}{task_id}", 3600,
                json.dumps({"status": "dead_letter", "reason": reason})
            )
            logger.warning("Task %s moved to dead-letter queue: %s", task_id, reason)
        except Exception as exc:
            logger.debug("Dead-letter move failed for %s: %s", task_id, exc)

    async def requeue_dead_letters(self, priority: int = PRIORITY_LOW) -> int:
        """Requeue all tasks from dead-letter queue with low priority. Returns count."""
        if not self._redis:
            return 0
        try:
            count = 0
            while True:
                item = await self._redis.rpop(self.DEAD_LETTER_KEY)
                if not item:
                    break
                if isinstance(item, bytes):
                    item = item.decode()
                data = json.loads(item)
                task_id = data.get("task_id")
                if task_id:
                    # Re-enqueue with low priority
                    requeue_payload = json.dumps({
                        "task_id": task_id,
                        "requeued_from": "dead_letter",
                        "enqueued_at": datetime.now(timezone.utc).isoformat(),
                    })
                    await self._redis.zadd(self.PRIORITY_QUEUE_KEY, {requeue_payload: priority})
                    count += 1
            logger.info("Requeued %d tasks from dead-letter queue", count)
            return count
        except Exception as exc:
            logger.debug("Dead-letter requeue failed: %s", exc)
            return 0

    async def get_queue_depth(self) -> int:
        """Get the number of tasks in the priority queue."""
        if not self._redis:
            return 0
        try:
            return await self._redis.zcard(self.PRIORITY_QUEUE_KEY)
        except Exception:
            return 0

    async def get_dead_letter_count(self) -> int:
        """Get the number of tasks in the dead-letter queue."""
        if not self._redis:
            return 0
        try:
            return await self._redis.llen(self.DEAD_LETTER_KEY)
        except Exception:
            return 0

    async def update_progress(self, task_id: str, progress: int, checkpoint: str | None = None):
        """Update task ephemeral state in Redis."""
        if not self._redis:
            return
        state = {
            "status": "running",
            "progress": progress,
            "checkpoint": checkpoint,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self._redis.setex(
                f"{self.TASK_STATE_PREFIX}{task_id}", 300, json.dumps(state)
            )
        except Exception as exc:
            logger.debug("Task progress update failed for %s: %s", task_id, exc)

    async def mark_completed(self, task_id: str):
        """Mark task as completed in Redis and release lock."""
        if not self._redis:
            return
        try:
            await self._redis.setex(
                f"{self.TASK_STATE_PREFIX}{task_id}", 60,
                json.dumps({"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()})
            )
            await self.release_lock(task_id)
        except Exception:
            pass

    async def mark_failed(self, task_id: str, error: str | None = None):
        """Mark task as failed in Redis and release lock."""
        if not self._redis:
            return
        try:
            await self._redis.setex(
                f"{self.TASK_STATE_PREFIX}{task_id}", 60,
                json.dumps({"status": "failed", "error": error, "failed_at": datetime.now(timezone.utc).isoformat()})
            )
            await self.release_lock(task_id)
        except Exception:
            pass

    async def get_state(self, task_id: str) -> dict | None:
        """Read ephemeral task state from Redis."""
        if not self._redis:
            return None
        try:
            data = await self._redis.get(f"{self.TASK_STATE_PREFIX}{task_id}")
            return json.loads(data) if data else None
        except Exception:
            return None

    async def check_task_timeouts(self, session):
        """Scan running tasks in DB and auto-kill/retry those exceeding timeout."""
        from sqlalchemy import select
        from app.models.task import Task
        from app.models.agent import Agent

        stmt = select(Task).where(Task.status == "running")
        result = await session.execute(stmt)
        running_tasks = result.scalars().all()

        from app.services.task_manager import TaskManager
        tm = TaskManager(session)

        now = datetime.now(timezone.utc)
        for task in running_tasks:
            if not task.started_at:
                continue
            elapsed = (now - task.started_at).total_seconds()
            if elapsed > task.timeout_seconds:
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    logger.info("Task %s timed out, requeuing (retry %d/%d)",
                                task.id, task.retry_count, task.max_retries)
                    # Use TaskManager to trigger status change safely
                    await tm.update_task_state(task.id, "pending")
                    # Re-enqueue with normal priority
                    await self.enqueue(task.id, task.assigned_agent_id, task.prompt, priority=PRIORITY_NORMAL)
                else:
                    # Move to dead-letter queue
                    await self.move_to_dead_letter(task.id, "Timeout exceeded after max retries")
                    stmt2 = select(Agent).where(Agent.is_system)
                    res = await session.execute(stmt2)
                    sys_agent = res.scalar_one_or_none()
                    if sys_agent:
                        task.assigned_agent_id = sys_agent.id
                        task.retry_count = 0
                        task.prompt = f"[SYSTEM ESCALATION: Task timed out repeatedly]\n\nOriginal Task:\n{task.prompt}"
                        await tm.update_task_state(task.id, "pending")
                        logger.warning("Task %s timed out and exceeded max retries. Escalated to System Agent.", task.id)
                    else:
                        logger.warning("Task %s timed out and exceeded max retries", task.id)
                        await tm.update_task_state(task.id, "failed", error_message="Timeout exceeded")
                        await self.mark_failed(task.id, "Timeout exceeded")

    @staticmethod
    def get_timeout_for_type(task_type: str) -> int:
        """Get the recommended timeout in seconds for a task type."""
        return TIMEOUT_MAP.get(task_type, TIMEOUT_MAP["default"])

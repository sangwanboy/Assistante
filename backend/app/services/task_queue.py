"""Redis-backed task queue for agent delegation pipeline.

Provides enqueue/dequeue, progress tracking, and timeout management
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


class TaskQueue:
    """Redis-backed task queue for the orchestration pipeline."""

    QUEUE_KEY = "assitance:task_queue"
    TASK_STATE_PREFIX = "assitance:task:"

    def __init__(self, redis_client=None):
        """Initialize with an optional RedisClient instance."""
        self._redis = redis_client.redis if redis_client and redis_client.available else None

    @property
    def available(self) -> bool:
        return self._redis is not None

    async def enqueue(self, task_id: str, agent_id: str, prompt: str, chain_id: str | None = None):
        """Add a task to the Redis queue."""
        if not self._redis:
            return
        payload = json.dumps({
            "task_id": task_id,
            "agent_id": agent_id,
            "prompt": prompt,
            "chain_id": chain_id,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            await self._redis.lpush(self.QUEUE_KEY, payload)
            await self._redis.setex(
                f"{self.TASK_STATE_PREFIX}{task_id}", 300, json.dumps({"status": "queued"})
            )
        except Exception as exc:
            logger.debug("Task enqueue failed for %s: %s", task_id, exc)

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
        """Mark task as completed in Redis."""
        if not self._redis:
            return
        try:
            await self._redis.setex(
                f"{self.TASK_STATE_PREFIX}{task_id}", 60,
                json.dumps({"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()})
            )
        except Exception:
            pass

    async def mark_failed(self, task_id: str, error: str | None = None):
        """Mark task as failed in Redis."""
        if not self._redis:
            return
        try:
            await self._redis.setex(
                f"{self.TASK_STATE_PREFIX}{task_id}", 60,
                json.dumps({"status": "failed", "error": error, "failed_at": datetime.now(timezone.utc).isoformat()})
            )
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

        stmt = select(Task).where(Task.status == "running")
        result = await session.execute(stmt)
        running_tasks = result.scalars().all()

        now = datetime.now(timezone.utc)
        for task in running_tasks:
            if not task.started_at:
                continue
            elapsed = (now - task.started_at).total_seconds()
            if elapsed > task.timeout_seconds:
                if task.retry_count < task.max_retries:
                    task.status = "pending"
                    task.retry_count += 1
                    logger.info("Task %s timed out, requeuing (retry %d/%d)",
                                task.id, task.retry_count, task.max_retries)
                else:
                    task.status = "failed"
                    task.completed_at = now
                    logger.warning("Task %s timed out and exceeded max retries", task.id)
                    await self.mark_failed(task.id, "Timeout exceeded")
        await session.commit()

    @staticmethod
    def get_timeout_for_type(task_type: str) -> int:
        """Get the recommended timeout in seconds for a task type."""
        return TIMEOUT_MAP.get(task_type, TIMEOUT_MAP["default"])

import json
import logging
from datetime import datetime, timezone
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.task import Task
from app.config import settings

logger = logging.getLogger(__name__)

class TaskManager:
    """Centralized service for managing tasks and broadcasting state via Redis Pub/Sub."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._redis = None
        if settings.redis_url:
            self._redis = redis.from_url(settings.redis_url)

    async def _publish_event(self, event_type: str, task: Task):
        if not self._redis:
            return
            
        payload = {
            "event": event_type,
            "task_id": task.id,
            "parent_task_id": task.parent_task_id,
            "assigned_agent_id": task.assigned_agent_id,
            "status": task.status,
            "progress_percent": task.progress,
            "conversation_id": task.conversation_id
        }
        
        try:
            await self._redis.publish("orchestrator:task_events", json.dumps(payload))
        except Exception as e:
            logger.error(f"Failed to publish task event {event_type}: {e}")

    async def create_task(self, assigned_agent_id: str, prompt: str, goal: str = "", conversation_id: str = None) -> Task:
        """Create a top-level task."""
        t = Task(
            assigned_agent_id=assigned_agent_id,
            prompt=prompt,
            goal=goal,
            conversation_id=conversation_id,
            status="pending"
        )
        self.session.add(t)
        await self.session.commit()
        await self.session.refresh(t)
        return t

    async def create_subtask(self, parent_task_id: str, assigned_agent_id: str, prompt: str, goal: str = "") -> Task:
        """Create a subtask bound to a parent orchestrator task."""
        parent = await self.get_task(parent_task_id)
        conversation_id = parent.conversation_id if parent else None
        
        t = Task(
            parent_task_id=parent_task_id,
            assigned_agent_id=assigned_agent_id,
            prompt=prompt,
            goal=goal,
            conversation_id=conversation_id,
            status="pending"
        )
        self.session.add(t)
        await self.session.commit()
        await self.session.refresh(t)
        return t

    async def get_task(self, task_id: str) -> Task | None:
        stmt = select(Task).where(Task.id == task_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_subtasks(self, parent_task_id: str) -> list[Task]:
        stmt = select(Task).where(Task.parent_task_id == parent_task_id).order_by(Task.created_at)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_task_state(self, task_id: str, status: str, result: str = None, error_message: str = None):
        """Update task status and emit standard events."""
        t = await self.get_task(task_id)
        if not t:
            return None
            
        t.status = status
        t.updated_at = datetime.now(timezone.utc)
        
        event_type = "task_progress"
        
        if status == "RUNNING" and not t.started_at:
            t.started_at = datetime.now(timezone.utc)
            t.last_heartbeat_at = datetime.now(timezone.utc)
            event_type = "task_started"
            
        if status in ("COMPLETED", "FAILED", "TIMED_OUT", "CANCELED", "DLQ"):
            t.completed_at = datetime.now(timezone.utc)
            t.progress = 100 if status == "COMPLETED" else t.progress
            if result:
                t.result = result
            if error_message:
                t.error_message = error_message
            event_type = f"task_{status.lower()}"
            
        await self.session.commit()
        await self._publish_event(event_type, t)
        
        return t

    async def update_progress(self, task_id: str, percent: int):
        """Update task progress explicitly, useful for agents streaming metrics."""
        t = await self.get_task(task_id)
        if not t:
            return None
            
        t.progress = min(max(percent, 0), 100) # Clamp 0-100
        t.updated_at = datetime.now(timezone.utc)
        
        if t.status == "QUEUED" and t.progress > 0:
            t.status = "RUNNING"
            t.started_at = t.started_at or datetime.now(timezone.utc)
            t.last_heartbeat_at = t.last_heartbeat_at or datetime.now(timezone.utc)
            await self._publish_event("task_started", t)
            
        await self.session.commit()
        await self._publish_event("task_progress", t)
        return t

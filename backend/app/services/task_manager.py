import json
import logging
from datetime import datetime, timezone
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.task import Task
from app.config import settings
from app.services.task_state_store import TaskStateStore
from app.services.history_summarization_service import HistorySummarizationService
from app.db.engine import async_session
from app.providers.registry import ProviderRegistry

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

        # Centralized task state snapshot used by prompt rehydration + frontend.
        state_store = TaskStateStore(self.session)
        await state_store.upsert(
            task_id=t.id,
            thread_id=t.conversation_id,
            status=t.status.lower(),
            progress=t.progress or 0,
            assigned_agents=[t.assigned_agent_id] if t.assigned_agent_id else [],
            results_summary=(t.result or t.error_message or "")[:1200] if status in ("COMPLETED", "FAILED", "TIMED_OUT", "CANCELED", "DLQ") else None,
        )

        # Queue async summarization for completed terminal states without blocking user response.
        if t.conversation_id and status in ("COMPLETED", "FAILED", "TIMED_OUT", "CANCELED", "DLQ"):
            try:
                service = await HistorySummarizationService.get_instance(
                    session_factory=async_session,
                    providers=ProviderRegistry(),
                )
                await service.enqueue(
                    thread_id=t.conversation_id,
                    trigger="task_completion",
                    task_id=t.id,
                    agent_id=t.assigned_agent_id,
                )
            except Exception as exc:
                logger.warning("Failed to enqueue summary for task %s: %s", t.id, exc)

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

        state_store = TaskStateStore(self.session)
        await state_store.upsert(
            task_id=t.id,
            thread_id=t.conversation_id,
            status=t.status.lower(),
            progress=t.progress,
            assigned_agents=[t.assigned_agent_id] if t.assigned_agent_id else [],
        )

        await self._publish_event("task_progress", t)
        return t

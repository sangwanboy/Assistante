"""Supervisor Service — The reaper of stale and problematic AgentRuns.

This service replaces and expands upon the legacy TaskWatchdog. It monitors the 
`Task` (AgentRun) table for:
1. Heartbeat Failures: Tasks marked 'RUNNING' but with stale `last_heartbeat_at`.
2. Step Stalls: Tasks stuck on the same step for too long.
3. Timeout Expiry: Tasks that have exceeded their `timeout_seconds`.
4. Runaway Prevention: Tasks exceeding `max_steps` that didn't terminate correctly.

When a problematic run is found, the Supervisor will:
- Mark it as 'FAILED', 'TIMED_OUT', or 'DLQ'.
- Log the reason for termination.
- Trigger any necessary cleanups.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, or_, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.db.engine import async_session

logger = logging.getLogger(__name__)

class Supervisor:
    _instance: Optional["Supervisor"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._scan_interval = 30  # seconds
        # Thresholds
        self._heartbeat_timeout = 60  # seconds
        self._max_step_duration = 300  # 5 minutes per step max

    @classmethod
    async def get_instance(cls) -> "Supervisor":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._main_loop())
        logger.info("Supervisor started (scan_interval=%ds)", self._scan_interval)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Supervisor stopped")

    async def _main_loop(self):
        # Initial delay
        await asyncio.sleep(10)
        while self._running:
            try:
                await self.scan_and_reap()
            except Exception as e:
                logger.error("Supervisor scan error: %s", e, exc_info=True)
            await asyncio.sleep(self._scan_interval)

    async def scan_and_reap(self):
        """Perform a single scan pass of all active tasks."""
        now = datetime.now(timezone.utc)
        
        async with async_session() as session:
            # Query for active runs
            stmt = select(Task).where(
                Task.status.in_(["RUNNING", "WAITING_TOOL", "WAITING_CHILD"])
            )
            result = await session.execute(stmt)
            active_tasks = result.scalars().all()

            reaped_count = 0
            for task in active_tasks:
                if await self._check_and_fix_task(session, task, now):
                    reaped_count += 1
            
            if reaped_count > 0:
                await session.commit()
                logger.info("Supervisor: reaped %d stale tasks", reaped_count)

    async def _check_and_fix_task(self, session: AsyncSession, task: Task, now: datetime) -> bool:
        """Examine a task and mark it as failed if it's stale."""
        # Ensure UTC comparison
        updated_at = task.updated_at.replace(tzinfo=timezone.utc) if task.updated_at.tzinfo is None else task.updated_at
        last_hb = task.last_heartbeat_at.replace(tzinfo=timezone.utc) if task.last_heartbeat_at and task.last_heartbeat_at.tzinfo is None else task.last_heartbeat_at
        step_started = task.step_started_at.replace(tzinfo=timezone.utc) if task.step_started_at and task.step_started_at.tzinfo is None else task.step_started_at
        started_at = task.started_at.replace(tzinfo=timezone.utc) if task.started_at and task.started_at.tzinfo is None else task.started_at

        # 1. Total Runtime Timeout
        if started_at:
            max_runtime = timedelta(seconds=task.timeout_seconds or 600)
            if now - started_at > max_runtime:
                return await self._reap(task, "TIMED_OUT", f"Overall task timeout exceeded ({task.timeout_seconds}s)")

        # 2. Heartbeat Failure (if heartbeat is enabled/recorded)
        if last_hb:
            if now - last_hb > timedelta(seconds=self._heartbeat_timeout):
                return await self._reap(task, "FAILED", f"Heartbeat lost for >{self._heartbeat_timeout}s")
        elif now - updated_at > timedelta(seconds=self._heartbeat_timeout * 2):
            # Fallback for tasks not emitting heartbeats yet
            return await self._reap(task, "FAILED", "No heartbeat recorded and updated_at is stale")

        # 3. Step Duration Timeout (stuck in one turn/iteration)
        if step_started:
            if now - step_started > timedelta(seconds=self._max_step_duration):
                return await self._reap(task, "FAILED", f"Step execution exceeded max duration ({self._max_step_duration}s)")

        # 4. Max Steps Reached (runaway prevention)
        if task.step_count >= (task.max_steps or 100):
            return await self._reap(task, "FAILED", f"Max steps limit reached ({task.max_steps})")

        return False

    async def _reap(self, task: Task, new_status: str, reason: str) -> bool:
        """Mark a task for reaping."""
        logger.warning("Supervisor: Reaping task %s (agent=%s). Reason: %s", 
                       task.id, task.assigned_agent_id, reason)
        
        task.status = new_status
        task.error_message = f"[SUPERVISOR] {reason}"
        task.completed_at = datetime.now(timezone.utc)
        
        # If we have reached max retries, move to DLQ instead of just FAILED
        if task.retry_count >= task.max_retries and new_status == "FAILED":
            task.status = "DLQ"
            task.error_message += " | Moved to Dead Letter Queue after max retries."
            
        return True

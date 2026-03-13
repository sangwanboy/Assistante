"""Agent heartbeat monitoring service using Redis pub/sub.

Three-layer heartbeat architecture:
- Layer 1: Agent process heartbeat (liveness)
- Layer 2: Task execution heartbeat (progress)
- Layer 3: Delegation chain heartbeat (orchestration flow)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AgentHeartbeatService:
    """Monitors agent liveness via Redis-backed heartbeats with in-memory fallback."""

    CHANNEL = "assitance:agent_heartbeat"
    STATE_PREFIX = "assitance:agent_state:"
    TASK_PREFIX = "assitance:task:"
    CHAIN_PREFIX = "assitance:chain:"

    UNRESPONSIVE_THRESHOLD = 10  # seconds
    STALLED_THRESHOLD = 20  # seconds
    OFFLINE_THRESHOLD = 30  # seconds
    MONITOR_INTERVAL = 5  # seconds

    _instance: "AgentHeartbeatService | None" = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._redis = None
        self._monitor_task: asyncio.Task | None = None
        self._running = False

    @classmethod
    async def get_instance(cls) -> "AgentHeartbeatService":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                from app.services.redis_client import RedisClient
                rc = await RedisClient.get_instance()
                if rc.available:
                    cls._instance._redis = rc.redis
                    logger.info("AgentHeartbeatService initialized with Redis")
                else:
                    logger.info("AgentHeartbeatService running in fallback mode (no Redis)")
            return cls._instance

    @property
    def available(self) -> bool:
        return self._redis is not None

    # ── Layer 1: Agent Process Heartbeat ──

    async def emit_heartbeat(self, agent_id: str, status: str, task_id: str | None = None):
        """Emit an agent heartbeat. Called by AgentStatusManager on status change."""
        if not self._redis:
            return
        payload = json.dumps({
            "agent_id": agent_id,
            "status": status,
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        try:
            await self._redis.setex(f"{self.STATE_PREFIX}{agent_id}", 60, payload)
            await self._redis.publish(self.CHANNEL, payload)
        except Exception as exc:
            logger.debug("Heartbeat emit failed for %s: %s", agent_id, exc)

    async def get_agent_state(self, agent_id: str) -> dict | None:
        """Get the latest heartbeat state for an agent from Redis."""
        if not self._redis:
            return None
        try:
            data = await self._redis.get(f"{self.STATE_PREFIX}{agent_id}")
            return json.loads(data) if data else None
        except Exception:
            return None

    # ── Layer 2: Task Execution Heartbeat ──

    async def update_task_progress(self, task_id: str, progress: int, checkpoint: str | None = None):
        """Update task progress in Redis."""
        if not self._redis:
            return
        payload = json.dumps({
            "task_id": task_id,
            "progress": progress,
            "checkpoint": checkpoint,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            await self._redis.setex(f"{self.TASK_PREFIX}{task_id}", 300, payload)
        except Exception as exc:
            logger.debug("Task progress update failed for %s: %s", task_id, exc)

    async def get_task_state(self, task_id: str) -> dict | None:
        """Get task ephemeral state from Redis."""
        if not self._redis:
            return None
        try:
            data = await self._redis.get(f"{self.TASK_PREFIX}{task_id}")
            return json.loads(data) if data else None
        except Exception:
            return None

    # ── Layer 3: Delegation Chain Heartbeat ──

    async def update_chain_state(self, chain_id: str, depth: int, agents: list[str], state: str):
        """Update delegation chain state in Redis and broadcast via WebSocket."""
        payload = {
            "chain_id": chain_id,
            "depth": depth,
            "agents_involved": agents,
            "state": state,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self._redis:
            try:
                await self._redis.setex(
                    f"{self.CHAIN_PREFIX}{chain_id}", 600, json.dumps(payload)
                )
            except Exception as exc:
                logger.debug("Chain state update failed for %s: %s", chain_id, exc)

        # Broadcast via status WebSocket
        from app.services.agent_status import AgentStatusManager
        status_mgr = await AgentStatusManager.get_instance()
        await status_mgr.emit_event({"type": "chain_update", **payload})

    # ── Monitor Loop ──

    async def start_monitor(self):
        """Start the background heartbeat monitor."""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Agent heartbeat monitor started (interval=%ds)", self.MONITOR_INTERVAL)

    def stop(self):
        """Stop the heartbeat monitor."""
        self._running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        logger.info("Agent heartbeat monitor stopped")

    async def _monitor_loop(self):
        """Check for stale agent heartbeats periodically."""
        while self._running:
            try:
                await self._check_stale_agents()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Heartbeat monitor error: %s", exc)
            await asyncio.sleep(self.MONITOR_INTERVAL)

    async def _check_stale_agents(self):
        """Scan all agent states and mark stalled/offline as needed."""
        if not self._redis:
            return

        from app.services.agent_status import AgentStatusManager, AgentState

        now = datetime.now(timezone.utc)
        status_mgr = await AgentStatusManager.get_instance()

        # Scan all agent state keys
        try:
            keys = []
            async for key in self._redis.scan_iter(f"{self.STATE_PREFIX}*"):
                keys.append(key)
        except Exception:
            return

        for key in keys:
            try:
                data = await self._redis.get(key)
                if not data:
                    continue
                state = json.loads(data)
                last_ts = datetime.fromisoformat(state["timestamp"])
                elapsed = (now - last_ts).total_seconds()
                agent_id = state["agent_id"]
                current = status_mgr.get_status(agent_id)

                if elapsed > self.OFFLINE_THRESHOLD and current.get("state") != AgentState.OFFLINE:
                    status_mgr.set_status(agent_id, AgentState.OFFLINE)
                    logger.warning("Agent %s marked OFFLINE (no heartbeat for %.0fs)", agent_id, elapsed)
                elif elapsed > self.STALLED_THRESHOLD and current.get("state") not in (
                    AgentState.OFFLINE, AgentState.STALLED, AgentState.ERROR
                ):
                    status_mgr.set_status(agent_id, AgentState.STALLED)
                    logger.warning("Agent %s marked STALLED (no heartbeat for %.0fs)", agent_id, elapsed)
            except Exception:
                continue

    # ── Recovery Protocol ──

    async def restart_agent(self, agent_id: str):
        """Attempt to restart a stalled agent by resetting its state."""
        from app.services.agent_status import AgentStatusManager, AgentState

        status_mgr = await AgentStatusManager.get_instance()
        current = status_mgr.get_status(agent_id)

        if current.get("state") in (AgentState.STALLED, AgentState.ERROR):
            status_mgr.set_status(agent_id, AgentState.RECOVERING)
            logger.info("Agent %s marked RECOVERING — attempting restart", agent_id)

            # Brief pause to allow cleanup
            await asyncio.sleep(1)

            # Reset to IDLE
            status_mgr.set_status(agent_id, AgentState.IDLE)
            await self.reset_failure_count(agent_id)
            logger.info("Agent %s restarted successfully — now IDLE", agent_id)
            return True

        return False

    async def reassign_agent_tasks(self, agent_id: str):
        """Reassign all pending/running tasks from a stalled agent to System Agent."""
        from app.db.engine import async_session
        from app.models.agent import Agent
        from app.models.task import Task
        from sqlalchemy import select

        async with async_session() as session:
            # Find System Agent
            stmt = select(Agent).where(Agent.is_system)
            res = await session.execute(stmt)
            sys_agent = res.scalar_one_or_none()
            if not sys_agent:
                logger.warning("Cannot reassign tasks — no System Agent found")
                return 0

            # Find tasks assigned to the stalled agent
            stmt = select(Task).where(
                Task.assigned_agent_id == agent_id,
                Task.status.in_(["pending", "running", "queued"])
            )
            result = await session.execute(stmt)
            tasks = result.scalars().all()

            count = 0
            for task in tasks:
                task.assigned_agent_id = sys_agent.id
                task.status = "pending"
                task.prompt = f"[SYSTEM ESCALATION: Agent stalled, task reassigned]\n\nOriginal Task:\n{task.prompt}"
                count += 1

            if count > 0:
                await session.commit()
                logger.info("Reassigned %d tasks from stalled agent %s to System Agent %s",
                            count, agent_id, sys_agent.name)
            return count

    async def handle_agent_failure(self, agent_id: str, task_id: str | None = None):
        """Handle agent failure: increment failure count, escalate if needed."""
        from app.db.engine import async_session
        from app.models.agent import Agent
        from app.models.task import Task
        from app.services.agent_status import AgentStatusManager, AgentState

        status_mgr = await AgentStatusManager.get_instance()

        async with async_session() as session:
            agent = await session.get(Agent, agent_id)
            if not agent:
                return

            agent.failure_count = (agent.failure_count or 0) + 1
            await session.commit()

            if agent.failure_count >= 3:
                status_mgr.set_status(agent_id, AgentState.ERROR, "Repeated failures — escalating to System Agent.")
                logger.error("[ALERT] %s failed %d times. Escalating to System Agent.", agent.name, agent.failure_count)
                
                if task_id:
                    task = await session.get(Task, task_id)
                    if task:
                        from sqlalchemy import select
                        stmt = select(Agent).where(Agent.is_system)
                        res = await session.execute(stmt)
                        sys_agent = res.scalar_one_or_none()
                        if sys_agent:
                            task.assigned_agent_id = sys_agent.id
                            task.status = "pending"
                            task.retry_count = 0
                            task.prompt = f"[SYSTEM ESCALATION: Sub-agent '{agent.name}' failed repeatedly]\n\nOriginal Task:\n{task.prompt}"
                            await session.commit()
                            logger.info("Task %s escalated to System Agent %s", task_id, sys_agent.name)
            else:
                # Requeue the task if applicable
                if task_id:
                    task = await session.get(Task, task_id)
                    if task and task.retry_count < task.max_retries:
                        task.status = "pending"
                        task.retry_count += 1
                        await session.commit()
                        logger.info("Task %s requeued (retry %d/%d)", task_id, task.retry_count, task.max_retries)

    async def reset_failure_count(self, agent_id: str):
        """Reset failure count on successful completion."""
        from app.db.engine import async_session
        from app.models.agent import Agent

        async with async_session() as session:
            agent = await session.get(Agent, agent_id)
            if agent and agent.failure_count > 0:
                agent.failure_count = 0
                await session.commit()

    async def reassign_task(self, task_id: str, reason: str = ""):
        """Reassign a stuck task to a different capable agent."""
        from app.db.engine import async_session
        from app.models.agent import Agent
        from app.models.task import Task
        from sqlalchemy import select

        async with async_session() as session:
            task = await session.get(Task, task_id)
            if not task or task.status not in ("running", "pending"):
                return False

            original_agent_id = task.assigned_agent_id

            # Find a different active agent
            stmt = select(Agent).where(
                Agent.is_active,
                Agent.id != original_agent_id,
            ).order_by(Agent.failure_count.asc())
            result = await session.execute(stmt)
            candidate = result.scalars().first()

            if candidate:
                task.assigned_agent_id = candidate.id
                task.status = "pending"
                task.prompt = f"[REASSIGNED: {reason}]\n\n{task.prompt}"
                await session.commit()
                logger.info(
                    "Task %s reassigned from %s to %s: %s",
                    task_id, original_agent_id, candidate.id, reason
                )
                return True
            return False

    async def reroute_workflow(self, workflow_run_id: str):
        """Skip a stuck workflow node and continue execution."""
        from app.db.engine import async_session
        from app.models.workflow import WorkflowRun, NodeExecution
        from sqlalchemy import select

        async with async_session() as session:
            run = await session.get(WorkflowRun, workflow_run_id)
            if not run or run.status != "running":
                return False

            # Find stuck node executions
            stmt = select(NodeExecution).where(
                NodeExecution.run_id == workflow_run_id,
                NodeExecution.status == "running",
            )
            result = await session.execute(stmt)
            stuck_nodes = result.scalars().all()

            for node_exec in stuck_nodes:
                node_exec.status = "skipped"
                node_exec.error = "Skipped by self-healing: node was stuck"
                logger.warning(
                    "Workflow %s: skipped stuck node %s",
                    workflow_run_id, node_exec.node_id
                )

            if stuck_nodes:
                await session.commit()
                return True
            return False

    async def throttle_agent(self, agent_id: str, duration_seconds: int = 60):
        """Temporarily reduce an agent's concurrency by marking it as throttled."""
        from app.services.agent_status import AgentStatusManager, AgentState

        status_mgr = await AgentStatusManager.get_instance()
        status_mgr.set_status(
            agent_id, AgentState.WORKING,
            f"Throttled for {duration_seconds}s due to repeated issues"
        )
        logger.info("Agent %s throttled for %ds", agent_id, duration_seconds)

        # Auto-unthrottle after duration
        async def _unthrottle():
            import asyncio
            await asyncio.sleep(duration_seconds)
            status_mgr.set_status(agent_id, AgentState.IDLE)
            logger.info("Agent %s unthrottled", agent_id)

        import asyncio
        asyncio.create_task(_unthrottle())

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        if cls._instance:
            cls._instance.stop()
        cls._instance = None

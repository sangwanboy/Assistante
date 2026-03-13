"""Master Heartbeat Controller — the central nervous system of the platform.

Coordinates all monitoring subsystems in a unified tick loop.
Runs continuously at 2-second intervals, dispatching sub-monitors
at their configured frequencies.

Subsystems:
- Agent Monitor: Detect stalled/crashed agents (every 5s)
- Task Monitor: Detect stuck tasks (every 10s)
- Workflow Monitor: Detect stuck workflow nodes (every 15s)
- Resource Monitor: Track API usage and throttle (every 30s)
- Communication Monitor: Check channels/mentions/queue (every 5s)
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MasterHeartbeat:
    """Centralized heartbeat controller coordinating all monitoring subsystems.
    
    Usage:
        master = MasterHeartbeat.get_instance()
        master.configure(session_factory=async_session)
        await master.start()
        ...
        master.stop()
    """

    TICK_INTERVAL = 2  # seconds — master loop frequency

    # Sub-monitor dispatch intervals (seconds)
    INTERVALS = {
        "agent": 5,
        "task": 10,
        "workflow": 15,
        "resource": 30,
        "communication": 5,
        "delegation": 10,
    }

    # Safety limits
    MAX_CONVERSATION_CHAIN_DEPTH = 6
    MAX_DELEGATION_DEPTH = 6
    MAX_AGENT_EXECUTION_TIME = 600  # 10 minutes

    _instance: "MasterHeartbeat | None" = None

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._session_factory = None
        self._rate_limiter = None
        self._tick_count = 0
        self._last_run: dict[str, datetime] = {}
        self._metrics: dict = {}

        # Sub-monitors (lazy-initialized)
        self._workflow_monitor = None
        self._resource_monitor = None
        self._communication_monitor = None

    @classmethod
    def get_instance(cls) -> "MasterHeartbeat":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def configure(self, session_factory=None, rate_limiter=None):
        """Configure with dependencies."""
        self._session_factory = session_factory
        self._rate_limiter = rate_limiter

    def _get_workflow_monitor(self):
        if self._workflow_monitor is None:
            from app.services.workflow_monitor import WorkflowMonitor
            self._workflow_monitor = WorkflowMonitor()
        return self._workflow_monitor

    def _get_resource_monitor(self):
        if self._resource_monitor is None:
            from app.services.resource_monitor import ResourceMonitor
            self._resource_monitor = ResourceMonitor()
        return self._resource_monitor

    def _get_communication_monitor(self):
        if self._communication_monitor is None:
            from app.services.communication_monitor import CommunicationMonitor
            self._communication_monitor = CommunicationMonitor()
        return self._communication_monitor

    @property
    def workflow_monitor(self):
        return self._get_workflow_monitor()

    @property
    def resource_monitor(self):
        return self._get_resource_monitor()

    @property
    def communication_monitor(self):
        return self._get_communication_monitor()

    # ── Lifecycle ──

    async def start(self):
        """Start the master heartbeat loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "[MasterHeartbeat] Started (tick=%.0fs, monitors: %s)",
            self.TICK_INTERVAL,
            ", ".join(f"{k}={v}s" for k, v in self.INTERVALS.items())
        )

    def stop(self):
        """Stop the master heartbeat."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("[MasterHeartbeat] Stopped")

    async def _loop(self):
        """Main tick loop — dispatches sub-monitors at configured intervals."""
        while self._running:
            try:
                self._tick_count += 1
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[MasterHeartbeat] Tick error: %s", exc, exc_info=True)
            await asyncio.sleep(self.TICK_INTERVAL)

    async def _tick(self):
        """Single heartbeat tick — runs due monitors and broadcasts metrics."""
        now = datetime.now(timezone.utc)
        metrics = {
            "type": "heartbeat_metrics",
            "tick": self._tick_count,
            "timestamp": now.isoformat(),
            "monitors": {},
        }

        # Dispatch sub-monitors based on intervals
        if self._should_run("agent", now):
            try:
                result = await self._monitor_agents()
                metrics["monitors"]["agent"] = result
            except Exception as exc:
                logger.error("[MasterHeartbeat] Agent monitor error: %s", exc)
                metrics["monitors"]["agent"] = {"error": str(exc)}

        if self._should_run("task", now):
            try:
                result = await self._monitor_tasks()
                metrics["monitors"]["task"] = result
            except Exception as exc:
                logger.error("[MasterHeartbeat] Task monitor error: %s", exc)
                metrics["monitors"]["task"] = {"error": str(exc)}

        if self._should_run("workflow", now):
            try:
                result = await self._monitor_workflows()
                metrics["monitors"]["workflow"] = result
            except Exception as exc:
                logger.error("[MasterHeartbeat] Workflow monitor error: %s", exc)
                metrics["monitors"]["workflow"] = {"error": str(exc)}

        if self._should_run("resource", now):
            try:
                result = await self._monitor_resources()
                metrics["monitors"]["resource"] = result
            except Exception as exc:
                logger.error("[MasterHeartbeat] Resource monitor error: %s", exc)
                metrics["monitors"]["resource"] = {"error": str(exc)}

        if self._should_run("communication", now):
            try:
                result = await self._monitor_communication()
                metrics["monitors"]["communication"] = result
            except Exception as exc:
                logger.error("[MasterHeartbeat] Communication monitor error: %s", exc)
                metrics["monitors"]["communication"] = {"error": str(exc)}

        if self._should_run("delegation", now):
            try:
                result = await self._monitor_delegation_chains()
                metrics["monitors"]["delegation"] = result
            except Exception as exc:
                logger.error("[MasterHeartbeat] Delegation monitor error: %s", exc)
                metrics["monitors"]["delegation"] = {"error": str(exc)}

        # Execution watchdog (every tick)
        try:
            watchdog_result = await self._execution_watchdog()
            if watchdog_result:
                metrics["monitors"]["watchdog"] = watchdog_result
        except Exception as exc:
            logger.error("[MasterHeartbeat] Watchdog error: %s", exc)

        self._metrics = metrics

        # Broadcast metrics via WebSocket (every 5th tick = 10s to avoid spam)
        if self._tick_count % 5 == 0:
            await self._broadcast_metrics(metrics)

    def _should_run(self, monitor: str, now: datetime) -> bool:
        """Check if a monitor is due to run based on its interval."""
        last = self._last_run.get(monitor)
        interval = self.INTERVALS.get(monitor, 10)
        if last is None or (now - last).total_seconds() >= interval:
            self._last_run[monitor] = now
            return True
        return False

    # ── Sub-Monitor Implementations ──

    async def _monitor_agents(self) -> dict:
        """Detect stalled/offline agents and attempt recovery."""
        from app.services.agent_status import AgentStatusManager, AgentState
        from app.services.agent_heartbeat import AgentHeartbeatService

        status_mgr = await AgentStatusManager.get_instance()
        heartbeat_svc = await AgentHeartbeatService.get_instance()
        statuses = status_mgr.get_all_statuses()

        counts = {"idle": 0, "working": 0, "stalled": 0, "offline": 0,
                  "error": 0, "recovering": 0, "learning": 0, "total": 0}
        stalled_agents = []

        for agent_id, status in statuses.items():
            state = status.get("state", AgentState.OFFLINE)
            state_val = state.value if isinstance(state, AgentState) else str(state)
            counts["total"] += 1
            if state_val in counts:
                counts[state_val] += 1
            if state_val == "stalled":
                stalled_agents.append(agent_id)

        # Attempt recovery for stalled agents
        recovered = 0
        for agent_id in stalled_agents:
            success = await heartbeat_svc.restart_agent(agent_id)
            if success:
                recovered += 1
            else:
                # Restart failed — reassign tasks
                await heartbeat_svc.reassign_agent_tasks(agent_id)

        counts["recovered"] = recovered
        return counts

    async def _monitor_tasks(self) -> dict:
        """Detect tasks that have stopped making progress."""
        if not self._session_factory:
            return {"active": 0, "stalled": 0}

        from sqlalchemy import select
        from app.models.task import Task

        async with self._session_factory() as session:
            stmt = select(Task).where(Task.status.in_(["running", "pending"]))
            result = await session.execute(stmt)
            tasks = result.scalars().all()

            now = datetime.now(timezone.utc)
            active = 0
            stalled = 0
            timed_out = 0

            for task in tasks:
                if task.status == "running":
                    active += 1
                    # Check for progress stall (60s no update)
                    if task.updated_at:
                        updated = task.updated_at
                        if updated.tzinfo is None:
                            updated = updated.replace(tzinfo=timezone.utc)
                        elapsed = (now - updated).total_seconds()
                        if elapsed > 90:
                            stalled += 1
                            logger.warning(
                                "[TaskMonitor] Task %s stalled (no progress for %.0fs)",
                                task.id, elapsed
                            )
                            # Attempt reassignment for long-stalled tasks
                            try:
                                from app.services.agent_heartbeat import AgentHeartbeatService
                                hb = await AgentHeartbeatService.get_instance()
                                await hb.reassign_task(task.id, f"Stalled for {elapsed:.0f}s")
                            except Exception:
                                pass
                        elif elapsed > 60:
                            stalled += 1

            # Run timeout check via TaskQueue
            try:
                from app.services.task_queue import TaskQueue
                from app.services.redis_client import RedisClient
                rc = await RedisClient.get_instance()
                tq = TaskQueue(rc)
                await tq.check_task_timeouts(session)
            except Exception as exc:
                logger.debug("Task timeout check error: %s", exc)

        return {
            "active": active,
            "pending": len(tasks) - active,
            "stalled": stalled,
            "timed_out": timed_out,
        }

    async def _monitor_workflows(self) -> dict:
        """Check for stuck workflow node executions."""
        wf_monitor = self._get_workflow_monitor()
        return await wf_monitor.check_stuck_nodes()

    async def _monitor_resources(self) -> dict:
        """Check API resource usage and throttle if needed."""
        res_monitor = self._get_resource_monitor()
        return await res_monitor.check_resources(self._rate_limiter)

    async def _monitor_communication(self) -> dict:
        """Check communication channel health."""
        comm_monitor = self._get_communication_monitor()
        return await comm_monitor.check_communication()

    async def _monitor_delegation_chains(self) -> dict:
        """Check for stalled delegation chains."""
        if not self._session_factory:
            return {"active": 0, "stalled": 0}

        from sqlalchemy import select
        from app.models.chain import DelegationChain

        async with self._session_factory() as session:
            stmt = select(DelegationChain).where(DelegationChain.state == "active")
            result = await session.execute(stmt)
            chains = result.scalars().all()

            now = datetime.now(timezone.utc)
            active = 0
            stalled = 0

            for chain in chains:
                active += 1
                if chain.updated_at:
                    updated = chain.updated_at
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=timezone.utc)
                    elapsed = (now - updated).total_seconds()
                    if elapsed > 90:
                        stalled += 1
                        logger.warning(
                            "[DelegationMonitor] Chain %s stalled (no update for %.0fs, depth=%d)",
                            chain.id, elapsed, chain.depth
                        )
                        # Auto-complete stalled chains
                        chain.state = "failed"
                        await session.commit()

            return {"active": active, "stalled": stalled}

    async def _execution_watchdog(self) -> dict | None:
        """Check for agent tasks exceeding max execution time."""
        if not self._session_factory:
            return None

        from sqlalchemy import select
        from app.models.task import Task

        async with self._session_factory() as session:
            stmt = select(Task).where(Task.status == "running")
            result = await session.execute(stmt)
            running_tasks = result.scalars().all()

            now = datetime.now(timezone.utc)
            killed = 0

            for task in running_tasks:
                if not task.started_at:
                    continue
                started = task.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                elapsed = (now - started).total_seconds()

                if elapsed > self.MAX_AGENT_EXECUTION_TIME:
                    task.status = "failed"
                    task.completed_at = now
                    task.result = (
                        f"[WATCHDOG] Terminated after {elapsed:.0f}s "
                        f"(max={self.MAX_AGENT_EXECUTION_TIME}s). "
                        f"Progress: {task.progress}%, Steps: {task.step_count}"
                    )
                    killed += 1
                    logger.warning(
                        "[Watchdog] Task %s killed after %.0fs (agent: %s)",
                        task.id, elapsed, task.assigned_agent_id
                    )

            if killed > 0:
                await session.commit()
                return {"killed": killed}

        return None

    async def _broadcast_metrics(self, metrics: dict):
        """Broadcast heartbeat metrics to WebSocket subscribers."""
        try:
            from app.services.agent_status import AgentStatusManager
            status_mgr = await AgentStatusManager.get_instance()
            await status_mgr.emit_event(metrics)
        except Exception:
            pass  # Non-critical

    def get_metrics(self) -> dict:
        """Get the latest metrics snapshot."""
        return self._metrics

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        if cls._instance:
            cls._instance.stop()
        cls._instance = None

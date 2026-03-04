import asyncio
import json
import logging
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    OFFLINE = "offline"
    INITIALIZING = "initializing"
    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"


class AgentStatusManager:
    """
    In-memory singleton to track global agent states and broadcast changes via WebSockets.
    Also emits Redis heartbeats when available.
    """
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentStatusManager, cls).__new__(cls)
            cls._instance.statuses = {}
            cls._instance.subscribers = []
        return cls._instance

    @classmethod
    async def get_instance(cls):
        async with cls._lock:
            if cls._instance is None:
                cls._instance = AgentStatusManager()
            return cls._instance

    def set_status(self, agent_id: str, state: AgentState, task: str = None):
        """Update an agent's status and broadcast to all listeners."""
        self.statuses[agent_id] = {"state": state, "task": task}
        self._broadcast(agent_id)

        # Also emit via Redis heartbeat (fire-and-forget)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit_redis_heartbeat(agent_id, state, task))
        except RuntimeError:
            pass  # No running event loop

    async def _emit_redis_heartbeat(self, agent_id: str, state: AgentState, task: str = None):
        """Push heartbeat to Redis if available."""
        try:
            from app.services.agent_heartbeat import AgentHeartbeatService
            hb = await AgentHeartbeatService.get_instance()
            if hb.available:
                await hb.emit_heartbeat(agent_id, state.value, task)
        except Exception:
            pass  # Redis not available, in-memory is sufficient

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        return self.statuses

    def get_status(self, agent_id: str) -> Dict[str, Any]:
        return self.statuses.get(agent_id, {"state": AgentState.OFFLINE, "task": None})

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    def _broadcast(self, agent_id: str):
        message = json.dumps({
            "type": "agent_status_update",
            "agent_id": agent_id,
            "status": self.statuses[agent_id]
        })
        for queue in self.subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.debug("Queue full for a status subscriber")
            except Exception as e:
                logger.debug("Error broadcasting status: %s", e)

    async def emit_event(self, event_data: dict):
        """Emit a generic JSON event to all WebSocket subscribers."""
        message = json.dumps(event_data)
        for queue in self.subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass
            except Exception as e:
                logger.debug("Error emitting event: %s", e)

import asyncio
import json
from enum import Enum
from typing import Dict, Any, List

class AgentState(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    OFFLINE = "offline"

class AgentStatusManager:
    """
    In-memory singleton to track global agent states and broadcast changes via WebSockets.
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
        print(f"DEBUG: Setting status for {agent_id} to {state} (task: {task})")
        self.statuses[agent_id] = {"state": state, "task": task}
        self._broadcast(agent_id)

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        return self.statuses

    def get_status(self, agent_id: str) -> Dict[str, Any]:
        return self.statuses.get(agent_id, {"state": AgentState.OFFLINE, "task": None})

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        print(f"DEBUG: New subscriber added. Total subscribers: {len(self.subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self.subscribers:
            self.subscribers.remove(queue)
            print(f"DEBUG: Subscriber removed. Total subscribers: {len(self.subscribers)}")

    def _broadcast(self, agent_id: str):
        message = json.dumps({
            "type": "agent_status_update",
            "agent_id": agent_id,
            "status": self.statuses[agent_id]
        })
        print(f"DEBUG: Broadcasting status update for {agent_id} to {len(self.subscribers)} subscribers")
        for queue in self.subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                print(f"DEBUG: Queue full for a subscriber!")
            except Exception as e:
                print(f"DEBUG: Error broadcasting: {e}")

    async def emit_event(self, event_data: dict):
        """Emit a generic JSON event to all WebSocket subscribers."""
        message = json.dumps(event_data)
        for queue in self.subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass
            except Exception as e:
                print(f"DEBUG: Error emitting event: {e}")

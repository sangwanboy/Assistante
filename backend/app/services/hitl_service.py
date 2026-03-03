import asyncio
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class HITLManager:
    _instance = None

    def __init__(self):
        # task_id -> {"event": asyncio.Event(), "status": "pending", "tool": str, "args": dict}
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        self.active_websockets = []

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self, websocket):
        await websocket.accept()
        self.active_websockets.append(websocket)
        # Send current pending requests on connect so if user refreshes they see it
        for task_id, data in self.pending_approvals.items():
            if data["status"] == "pending":
                await websocket.send_json({
                    "type": "APPROVAL_REQUIRED",
                    "task_id": task_id,
                    "tool": data["tool"],
                    "arguments": data["args"]
                })

    def disconnect(self, websocket):
        if websocket in self.active_websockets:
            self.active_websockets.remove(websocket)

    async def broadcast(self, message: dict):
        dead_sockets = []
        for ws in self.active_websockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.append(ws)
        for ws in dead_sockets:
            self.disconnect(ws)

    async def request_approval(self, task_id: str, tool_name: str, arguments: dict, timeout: float = 120.0) -> bool:
        """Returns True if approved, False if denied or timed out."""
        event = asyncio.Event()
        self.pending_approvals[task_id] = {
            "event": event,
            "status": "pending",
            "tool": tool_name,
            "args": arguments
        }

        logger.info("HITL approval requested: task=%s tool=%s (connected_clients=%d)",
                     task_id, tool_name, len(self.active_websockets))

        await self.broadcast({
            "type": "APPROVAL_REQUIRED",
            "task_id": task_id,
            "tool": tool_name,
            "arguments": arguments
        })

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("HITL approval timed out after %.0fs: task=%s tool=%s", timeout, task_id, tool_name)
            self.pending_approvals[task_id]["status"] = "denied"
            await self.broadcast({
                "type": "APPROVAL_TIMEOUT",
                "task_id": task_id,
                "tool": tool_name,
            })

        status = self.pending_approvals[task_id]["status"]
        logger.info("HITL approval resolved: task=%s status=%s", task_id, status)
        # Cleanup
        del self.pending_approvals[task_id]

        return status == "approved"

    def resolve_approval(self, task_id: str, action: str):
        if task_id in self.pending_approvals:
            logger.info("HITL resolve: task=%s action=%s", task_id, action)
            self.pending_approvals[task_id]["status"] = "approved" if action == "APPROVE" else "denied"
            self.pending_approvals[task_id]["event"].set()
        else:
            logger.warning("HITL resolve for unknown task_id=%s (already timed out?)", task_id)

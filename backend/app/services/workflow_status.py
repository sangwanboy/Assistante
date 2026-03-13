import json
from typing import Dict, List, Any
from fastapi import WebSocket

class WorkflowStatusManager:
    """Manages active WebSocket connections for workflow execution monitoring."""
    def __init__(self):
        # Maps workflow_id -> list of active websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Global connections that watch all workflows (e.g., for the monitor dashboard)
        self.global_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, workflow_id: str = None):
        """Connect a client, optionally scoped to a specific workflow."""
        await websocket.accept()
        if workflow_id:
            if workflow_id not in self.active_connections:
                self.active_connections[workflow_id] = []
            self.active_connections[workflow_id].append(websocket)
        else:
            self.global_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, workflow_id: str = None):
        """Disconnect a client."""
        if workflow_id:
            if workflow_id in self.active_connections:
                if websocket in self.active_connections[workflow_id]:
                    self.active_connections[workflow_id].remove(websocket)
                if not self.active_connections[workflow_id]:
                    del self.active_connections[workflow_id]
        else:
            if websocket in self.global_connections:
                self.global_connections.remove(websocket)

    async def broadcast_execution_update(
        self, workflow_id: str, run_id: str, node_id: str, status: str, data: Dict[str, Any] = None
    ):
        """Broadcast a node's execution status to interested clients."""
        message = {
            "type": "node_execution_update",
            "workflow_id": workflow_id,
            "run_id": run_id,
            "node_id": node_id,
            "status": status,  # 'running', 'completed', 'failed', 'paused'
            "data": data or {}
        }
        msg_text = json.dumps(message)

        # Send to specific workflow watchers
        if workflow_id in self.active_connections:
            for connection in self.active_connections[workflow_id]:
                try:
                    await connection.send_text(msg_text)
                except Exception:
                    pass  # Dead connection

        # Send to global watchers
        for connection in self.global_connections:
            try:
                await connection.send_text(msg_text)
            except Exception:
                pass


manager = WorkflowStatusManager()

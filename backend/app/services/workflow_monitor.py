"""Workflow execution monitor for the Master Heartbeat system.

Tracks active workflow node executions and detects stuck nodes,
triggering retry → skip → reroute → escalation recovery.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class NodeExecution:
    """Tracks an active workflow node execution."""
    workflow_id: str
    run_id: str
    node_id: str
    node_type: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    max_retries: int = 2


class WorkflowMonitor:
    """Monitors active workflow node executions for timeouts and failures.
    
    Called by MasterHeartbeat every 15 seconds.
    
    Detection: If a node runs > NODE_TIMEOUT seconds → retry.
    If retry fails → skip node and continue workflow.
    """

    NODE_TIMEOUT = 90  # seconds before a node is considered stuck
    MAX_NODE_RETRIES = 2

    def __init__(self):
        # Maps run_id:node_id → NodeExecution
        self._active_nodes: dict[str, NodeExecution] = {}
        self._lock = asyncio.Lock()

    def register_node_start(self, workflow_id: str, run_id: str, node_id: str, node_type: str = "unknown"):
        """Called when a workflow node begins execution."""
        key = f"{run_id}:{node_id}"
        self._active_nodes[key] = NodeExecution(
            workflow_id=workflow_id,
            run_id=run_id,
            node_id=node_id,
            node_type=node_type,
        )

    def register_node_complete(self, run_id: str, node_id: str):
        """Called when a workflow node finishes (success or fail)."""
        key = f"{run_id}:{node_id}"
        self._active_nodes.pop(key, None)

    def register_run_complete(self, run_id: str):
        """Remove all tracked nodes for a completed workflow run."""
        keys_to_remove = [k for k in self._active_nodes if k.startswith(f"{run_id}:")]
        for k in keys_to_remove:
            del self._active_nodes[k]

    async def check_stuck_nodes(self) -> dict:
        """Scan active nodes for timeouts. Returns metrics dict."""
        now = datetime.now(timezone.utc)
        stuck_count = 0
        retried_count = 0
        skipped_count = 0
        total_active = len(self._active_nodes)

        keys_to_remove = []

        async with self._lock:
            for key, node in list(self._active_nodes.items()):
                elapsed = (now - node.started_at).total_seconds()

                if elapsed > self.NODE_TIMEOUT:
                    stuck_count += 1

                    if node.retry_count < self.MAX_NODE_RETRIES:
                        # Retry the node
                        node.retry_count += 1
                        node.started_at = now  # Reset timer
                        retried_count += 1
                        logger.warning(
                            "[WorkflowMonitor] Node %s in workflow %s stuck (%.0fs). "
                            "Retrying (%d/%d).",
                            node.node_id, node.workflow_id, elapsed,
                            node.retry_count, self.MAX_NODE_RETRIES
                        )

                        # Broadcast retry event
                        try:
                            from app.services.workflow_status import manager as ws_mgr
                            await ws_mgr.broadcast_execution_update(
                                node.workflow_id, node.run_id, node.node_id,
                                "retrying", {"retry_count": node.retry_count}
                            )
                        except Exception:
                            pass
                    else:
                        # Max retries exceeded — skip this node
                        skipped_count += 1
                        keys_to_remove.append(key)
                        logger.error(
                            "[WorkflowMonitor] Node %s in workflow %s exceeded max retries. "
                            "Skipping node.",
                            node.node_id, node.workflow_id
                        )

                        # Broadcast skip event
                        try:
                            from app.services.workflow_status import manager as ws_mgr
                            await ws_mgr.broadcast_execution_update(
                                node.workflow_id, node.run_id, node.node_id,
                                "skipped", {"reason": "timeout_exceeded"}
                            )
                        except Exception:
                            pass

            # Clean up skipped nodes
            for key in keys_to_remove:
                del self._active_nodes[key]

        return {
            "active_nodes": total_active,
            "stuck_nodes": stuck_count,
            "retried_nodes": retried_count,
            "skipped_nodes": skipped_count,
        }

    def get_active_count(self) -> int:
        """Return the number of currently tracked node executions."""
        return len(self._active_nodes)

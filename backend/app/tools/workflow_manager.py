from typing import Any
import json
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.tools.base import BaseTool
from app.db.engine import async_session
from app.models.workflow import Workflow, Node, Edge
import uuid


class WorkflowManagerTool(BaseTool):
    @property
    def name(self) -> str:
        return "WorkflowManagerTool"

    @property
    def description(self) -> str:
        return (
            "Creates, lists, deletes, and customizes automation Workflows. "
            "Use this tool to build node-based workflow graphs that agents can execute. "
            "Actions: 'create' (new workflow), 'list' (all workflows, optionally filtered by agent_id), "
            "'get' (full graph of a workflow), 'delete' (remove a workflow), "
            "'add_node' (add a trigger or action node), 'remove_node' (remove a node), "
            "'connect' (add an edge between two nodes)."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "What to do: 'create', 'list', 'get', 'delete', 'add_node', 'remove_node', 'connect'",
                    "enum": ["create", "list", "get", "delete", "add_node", "remove_node", "connect"]
                },
                "workflow_id": {
                    "type": "string",
                    "description": "ID of the workflow (required for get, delete, add_node, remove_node, connect)"
                },
                "name": {
                    "type": "string",
                    "description": "Name of the workflow (for create)"
                },
                "description": {
                    "type": "string",
                    "description": "Description of the workflow (for create)"
                },
                "agent_id": {
                    "type": "string",
                    "description": "Optional agent ID to assign the workflow to (for create) or filter by (for list)"
                },
                "channel_id": {
                    "type": "string",
                    "description": "Optional channel/group ID to assign the workflow to (for create)"
                },
                "node_type": {
                    "type": "string",
                    "description": "Node type: 'trigger' or 'action' (for add_node)",
                    "enum": ["trigger", "action"]
                },
                "node_sub_type": {
                    "type": "string",
                    "description": "Sub-type of the node: 'webhook', 'schedule', 'llm', 'summarize', 'email', 'condition', 'branch' (for add_node)"
                },
                "node_id": {
                    "type": "string",
                    "description": "ID of the node to remove (for remove_node)"
                },
                "source_node_id": {
                    "type": "string",
                    "description": "Source node ID for edge connection (for connect)"
                },
                "target_node_id": {
                    "type": "string",
                    "description": "Target node ID for edge connection (for connect)"
                },
                "config": {
                    "type": "object",
                    "description": "Optional configuration for the node (for add_node)"
                },
                "position_x": {
                    "type": "string",
                    "description": "X position of the node on canvas (for add_node), default '250'"
                },
                "position_y": {
                    "type": "string",
                    "description": "Y position of the node on canvas (for add_node), default '200'"
                }
            },
            "required": ["action"]
        }

    async def execute(self, **params: Any) -> str:
        action = params.get("action")

        async with async_session() as session:
            # ── LIST ──
            if action == "list":
                stmt = select(Workflow)
                agent_id = params.get("agent_id")
                channel_id = params.get("channel_id")
                if agent_id:
                    stmt = stmt.where(Workflow.agent_id == agent_id)
                if channel_id:
                    stmt = stmt.where(Workflow.channel_id == channel_id)
                stmt = stmt.order_by(Workflow.created_at.desc())
                result = await session.execute(stmt)
                workflows = [
                    {
                        "id": w.id,
                        "name": w.name,
                        "description": w.description,
                        "is_active": w.is_active,
                        "agent_id": w.agent_id,
                        "channel_id": w.channel_id,
                    }
                    for w in result.scalars().all()
                ]
                if not workflows:
                    return "No workflows found."
                return json.dumps(workflows, indent=2)

            # ── CREATE ──
            if action == "create":
                wf = Workflow(
                    name=params.get("name", "Untitled Workflow"),
                    description=params.get("description", ""),
                    agent_id=params.get("agent_id"),
                    channel_id=params.get("channel_id"),
                )
                session.add(wf)
                await session.commit()
                await session.refresh(wf)
                return f"Workflow '{wf.name}' created successfully with ID: {wf.id}"

            # ── GET (full graph) ──
            if action == "get":
                wf_id = params.get("workflow_id")
                if not wf_id:
                    return "Error: workflow_id is required for 'get'."
                stmt = (
                    select(Workflow)
                    .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
                    .where(Workflow.id == wf_id)
                )
                result = await session.execute(stmt)
                wf = result.scalar_one_or_none()
                if not wf:
                    return f"Error: Workflow {wf_id} not found."
                graph = {
                    "id": wf.id,
                    "name": wf.name,
                    "description": wf.description,
                    "nodes": [
                        {"id": n.id, "type": n.type, "sub_type": n.sub_type, "config": n.config_json}
                        for n in wf.nodes
                    ],
                    "edges": [
                        {"id": e.id, "source": e.source_node_id, "target": e.target_node_id}
                        for e in wf.edges
                    ],
                }
                return json.dumps(graph, indent=2)

            # ── DELETE ──
            if action == "delete":
                wf_id = params.get("workflow_id")
                if not wf_id:
                    return "Error: workflow_id is required for 'delete'."
                wf = await session.get(Workflow, wf_id)
                if not wf:
                    return f"Error: Workflow {wf_id} not found."
                name = wf.name
                await session.delete(wf)
                await session.commit()
                return f"Workflow '{name}' deleted successfully."

            # ── ADD NODE ──
            if action == "add_node":
                wf_id = params.get("workflow_id")
                if not wf_id:
                    return "Error: workflow_id is required for 'add_node'."
                wf = await session.get(Workflow, wf_id)
                if not wf:
                    return f"Error: Workflow {wf_id} not found."
                node = Node(
                    id=str(uuid.uuid4())[:8],
                    workflow_id=wf_id,
                    type=params.get("node_type", "action"),
                    sub_type=params.get("node_sub_type", "llm"),
                    config_json=json.dumps(params.get("config", {})),
                    position_x=params.get("position_x", "250"),
                    position_y=params.get("position_y", "200"),
                )
                session.add(node)
                await session.commit()
                return f"Node '{node.sub_type}' (type: {node.type}) added to workflow '{wf.name}' with node ID: {node.id}"

            # ── REMOVE NODE ──
            if action == "remove_node":
                node_id = params.get("node_id")
                wf_id = params.get("workflow_id")
                if not node_id or not wf_id:
                    return "Error: workflow_id and node_id are required for 'remove_node'."
                node = await session.get(Node, node_id)
                if not node or node.workflow_id != wf_id:
                    return f"Error: Node {node_id} not found in workflow {wf_id}."
                await session.delete(node)
                # Also remove edges referencing this node
                edges_stmt = select(Edge).where(
                    Edge.workflow_id == wf_id,
                    (Edge.source_node_id == node_id) | (Edge.target_node_id == node_id)
                )
                edges_result = await session.execute(edges_stmt)
                for edge in edges_result.scalars().all():
                    await session.delete(edge)
                await session.commit()
                return f"Node {node_id} and its connected edges removed."

            # ── CONNECT (add edge) ──
            if action == "connect":
                wf_id = params.get("workflow_id")
                source = params.get("source_node_id")
                target = params.get("target_node_id")
                if not wf_id or not source or not target:
                    return "Error: workflow_id, source_node_id, and target_node_id are required for 'connect'."
                edge = Edge(
                    id=f"e-{source}-{target}",
                    workflow_id=wf_id,
                    source_node_id=source,
                    target_node_id=target,
                )
                session.add(edge)
                await session.commit()
                return f"Edge connected: {source} → {target}"

        return "Error: Unknown action."

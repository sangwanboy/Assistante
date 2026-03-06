from typing import Any
import json
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.tools.base import BaseTool

from app.models.workflow import Workflow, Node, Edge
import uuid


class WorkflowManagerTool(BaseTool):
    @property
    def name(self) -> str:
        return "WorkflowManagerTool"

    @property
    def description(self) -> str:
        return (
            "Use this tool to build node-based workflow graphs that agents can execute. "
            "Actions: 'create' (new workflow empty), 'list' (all workflows), "
            "'get' (full graph of a workflow), 'delete' (remove a workflow), "
            "'add_node' (add a trigger or action node), 'remove_node' (remove a node), "
            "'connect' (add an edge between two nodes), "
            "'execute' (run a workflow by its ID), "
            "'create_from_json' (create a full workflow with nodes and edges at once)."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "What to do: 'create', 'list', 'get', 'delete', 'add_node', 'remove_node', 'connect', 'execute', 'create_from_json'",
                    "enum": ["create", "list", "get", "delete", "add_node", "remove_node", "connect", "execute", "create_from_json"]
                },
                "workflow_id": {
                    "type": "string",
                    "description": "ID of the workflow (required for get, delete, add_node, remove_node, connect, execute)"
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
                "nodes_json": {
                    "type": "string",
                    "description": "JSON string of nodes array for create_from_json. Each node must have type, sub_type, config_json, position_x, position_y, label."
                },
                "edges_json": {
                    "type": "string",
                    "description": "JSON string of edges array for create_from_json. Each edge must have source_node_id, target_node_id, and optionally source_handle."
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
        from app.db.engine import async_session as workflow_session_factory
        action = params.get("action")

        async with workflow_session_factory() as session:
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

            # ── EXECUTE ──
            if action == "execute":
                wf_id = params.get("workflow_id")
                if not wf_id:
                    return "Error: workflow_id is required for 'execute'."

                # We need to get the engine to execute it.
                # To avoid circular imports, we import it here.
                from app.services.workflow_engine import WorkflowEngine
                from app.providers.registry import provider_registry
                
                try:
                    # Use the existing session from the outer 'async with' block
                    engine = WorkflowEngine(session=session, provider_registry=provider_registry)
                    result = await engine.execute_workflow(wf_id, {"trigger": "agent_call"})
                    return json.dumps({
                        "status": result.status,
                        "run_id": str(result.run_id) if result.run_id else None,
                        "payload": result.payload
                    }, indent=2)
                except Exception as e:
                    return f"Error executing workflow: {str(e)}"

            # ── CREATE FROM JSON ──
            if action == "create_from_json":
                try:
                    name = params.get("name", "Generated Workflow")
                    desc = params.get("description", "")
                    agent_id = params.get("agent_id")
                    
                    nodes_data = json.loads(params.get("nodes_json", "[]"))
                    edges_data = json.loads(params.get("edges_json", "[]"))
                    
                    wf = Workflow(
                        name=name,
                        description=desc,
                        agent_id=agent_id
                    )
                    session.add(wf)
                    await session.commit()
                    await session.refresh(wf)
                    
                    # Create mapping to link temp IDs from JSON to real UUIDs
                    id_map = {}
                    
                    for nd in nodes_data:
                        temp_id = nd.get("id") or str(uuid.uuid4())[:8]
                        real_id = str(uuid.uuid4())[:8]
                        id_map[temp_id] = real_id
                        
                        node = Node(
                            id=real_id,
                            workflow_id=wf.id,
                            type=nd.get("type", "action"),
                            sub_type=nd.get("sub_type", "llm"),
                            label=nd.get("label"),
                            config_json=nd.get("config_json", "{}"),
                            position_x=nd.get("position_x", "250"),
                            position_y=nd.get("position_y", "200")
                        )
                        session.add(node)
                    
                    for ed in edges_data:
                        source = id_map.get(ed.get("source_node_id"), ed.get("source_node_id"))
                        target = id_map.get(ed.get("target_node_id"), ed.get("target_node_id"))
                        edge = Edge(
                            id=f"e-{source}-{target}-{str(uuid.uuid4())[:4]}",
                            workflow_id=wf.id,
                            source_node_id=source,
                            target_node_id=target,
                            source_handle=ed.get("source_handle")
                        )
                        session.add(edge)
                        
                    await session.commit()
                    return f"Workflow '{wf.name}' created successfully with {len(nodes_data)} nodes and {len(edges_data)} edges. ID: {wf.id}"
                except Exception as e:
                    return f"Error creating workflow from JSON: {str(e)}"

        return "Error: Unknown action."

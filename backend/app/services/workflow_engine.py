import json
import asyncio
import httpx
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import re

from app.models.workflow import Node, WorkflowRun
from app.services.workflow_service import WorkflowService

from app.providers.registry import ProviderRegistry
from app.providers.base import ChatMessage
from app.tools.registry import ToolRegistry


class WorkflowEngine:
    """
    Executes workflows as DAGs with full run/node tracking.
    Supports: triggers, agent, tool, data, logic, and human nodes.
    """

    def __init__(
        self,
        session: AsyncSession,
        provider_registry: ProviderRegistry,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.session = session
        self.service = WorkflowService(session)
        self.provider_registry = provider_registry
        self.tool_registry = tool_registry

    # ─── Main Entry Point ─────────────────────────────────────

    async def execute_workflow(
        self, workflow_id: str, trigger_payload: Dict[str, Any], event_queue: Optional[asyncio.Queue] = None, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a workflow and track everything."""
        workflow = await self.service.get_workflow(workflow_id)
        if not workflow or not workflow.is_active:
            return {"status": "error", "message": "Workflow not found or inactive."}

        # Create run record
        run = await self.service.create_run(workflow_id, trigger_payload)
        await self.service.update_run_status(run.id, "running")

        # Build node/edge maps
        nodes_by_id: Dict[str, Node] = {n.id: n for n in workflow.nodes}
        adjacency: Dict[str, List[str]] = {n.id: [] for n in workflow.nodes}
        # Edge routing: key = (source_id, source_handle) -> [target_ids]
        handle_adjacency: Dict[str, Dict[str, List[str]]] = {n.id: {} for n in workflow.nodes}

        for edge in workflow.edges:
            if edge.source_node_id in adjacency:
                adjacency[edge.source_node_id].append(edge.target_node_id)
                handle = edge.source_handle or "default"
                handle_adjacency[edge.source_node_id].setdefault(handle, [])
                handle_adjacency[edge.source_node_id][handle].append(edge.target_node_id)

        # Find trigger node(s)
        trigger_nodes = [n for n in workflow.nodes if n.type == "trigger"]
        if not trigger_nodes:
            await self.service.update_run_status(run.id, "failed", "No trigger node found.")
            return {"status": "error", "run_id": run.id, "message": "No trigger node."}

        # Fetch persistent memory
        memory_record = await self.service.get_workflow_memory(workflow_id, workflow.agent_id, workflow.channel_id)
        memory_data = json.loads(memory_record.memory_json) if memory_record and memory_record.memory_json else {}

        # Set up initial runtime context
        context = trigger_payload.copy()
        context["memory"] = memory_data
        context["_workflow_meta"] = {
            "workflow_id": workflow_id,
            "agent_id": workflow.agent_id,
            "channel_id": workflow.channel_id,
        }

        # Save initial context to run
        run.context_json = json.dumps(context)
        await self.session.commit()

        # Execute from trigger
        try:
            context = await self._execute_from(
                trigger_nodes[0].id, nodes_by_id, adjacency, handle_adjacency, context, run.id, event_queue, conversation_id
            )

            await self.service.update_run_status(run.id, "completed")
        except WorkflowPaused as e:
            await self.service.update_run_status(run.id, "paused", str(e))
            return {"status": "paused", "run_id": run.id, "message": str(e)}
        except Exception as e:
            await self.service.update_run_status(run.id, "failed", str(e))
            return {"status": "error", "run_id": run.id, "message": str(e)}

        return {"status": "completed", "run_id": run.id, "final_payload": context}

    # ─── DAG Traversal ────────────────────────────────────────

    async def _execute_from(
        self,
        node_id: str,
        nodes_by_id: Dict[str, Node],
        adjacency: Dict[str, List[str]],
        handle_adjacency: Dict[str, Dict[str, List[str]]],
        context: Dict[str, Any],
        run_id: str,
        event_queue: Optional[asyncio.Queue] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a node and its successors."""
        node = nodes_by_id.get(node_id)
        if not node:
            return context

        config = json.loads(node.config_json) if node.config_json else {}

        # Create node execution record and broadcast 'running' state
        exe = await self.service.create_node_execution(run_id, node.id, context)
        await self.service.update_node_execution(exe.id, "running")
        
        from app.services.workflow_status import manager as workflow_ws_manager
        await workflow_ws_manager.broadcast_execution_update(
            workflow_id=node.workflow_id, run_id=run_id, node_id=node.id, status="running", data={}
        )

        try:
            result = await self._execute_node(node, config, context, event_queue, conversation_id)
            
            # Merge outputs into runtime context
            if "output" in result and isinstance(result["output"], dict):
                context.update(result["output"])
            
            # Save updated runtime context to DB
            await self.session.execute(update(WorkflowRun).where(WorkflowRun.id == run_id).values(context_json=json.dumps(context)))
            await self.session.commit()

            # Save checkpoint for resume support
            run = await self.session.get(WorkflowRun, run_id)
            if run and hasattr(run, 'checkpoint_node_id'):
                run.checkpoint_node_id = node.id
                run.checkpoint_payload = json.dumps(context) if context else None
                await self.session.commit()

            # Broadcast 'completed' state optionally with output data
            await self.service.update_node_execution(exe.id, "completed", result.get("output", {}))
            await workflow_ws_manager.broadcast_execution_update(
                workflow_id=node.workflow_id, run_id=run_id, node_id=node.id, status="completed", data=result.get("output", {})
            )

        except WorkflowPaused:
            await self.service.update_node_execution(exe.id, "completed", {"paused": True})
            await workflow_ws_manager.broadcast_execution_update(
                workflow_id=node.workflow_id, run_id=run_id, node_id=node.id, status="paused", data={}
            )
            raise
        except Exception as e:
            await self.service.update_node_execution(exe.id, "failed", error=str(e))
            await workflow_ws_manager.broadcast_execution_update(
                workflow_id=node.workflow_id, run_id=run_id, node_id=node.id, status="failed", data={"error": str(e)}
            )
            raise

        # Determine next nodes
        route_handle = result.get("route_handle")

        if route_handle and node.id in handle_adjacency:
            # Routed output (condition/switch)
            next_ids = handle_adjacency[node.id].get(route_handle, [])
            if not next_ids:
                next_ids = handle_adjacency[node.id].get("default", [])
        else:
            next_ids = adjacency.get(node.id, [])

        # Handle loop node
        if node.sub_type == "loop" and result.get("loop_items"):
            loop_items = result["loop_items"]
            loop_results = []
            for item in loop_items:
                loop_ctx = {**context, "loop_item": item}
                for nid in next_ids:
                    loop_ctx = await self._execute_from(
                        nid, nodes_by_id, adjacency, handle_adjacency, loop_ctx, run_id, event_queue, conversation_id
                    )
                loop_results.append(loop_ctx)
            context["loop_results"] = loop_results
            return context

        # Execute successors (parallel if multiple branches)
        if len(next_ids) == 1:
            context = await self._execute_from(
                next_ids[0], nodes_by_id, adjacency, handle_adjacency, context, run_id, event_queue, conversation_id
            )
        elif len(next_ids) > 1:
            # Parallel branch execution
            tasks = [
                self._execute_from(nid, nodes_by_id, adjacency, handle_adjacency, context.copy(), run_id, event_queue, conversation_id)
                for nid in next_ids
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    raise r
                context.update(r)

        return context

    # ─── Node Execution Logic ─────────────────────────────────

    async def _execute_node(
        self, node: Node, config: Dict[str, Any], payload: Dict[str, Any], 
        event_queue: Optional[asyncio.Queue] = None, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Route to the correct handler by node type/sub_type."""

        handlers = {
            # Triggers — pass through
            "trigger": self._handle_trigger,
            # Agent nodes
            "agent": self._handle_agent,
            # Tool nodes
            "tool": self._handle_tool,
            # Data nodes
            "data": self._handle_data,
            # Logic nodes
            "logic": self._handle_logic,
            # Human interaction
            "human": self._handle_human,
            # Legacy action nodes
            "action": self._handle_action,
            # Parallel execution
            "parallel": self._handle_parallel,
        }

        handler = handlers.get(node.type, self._handle_trigger)
        if node.type == "agent":
            return await handler(node, config, payload, event_queue, conversation_id)
        return await handler(node, config, payload)

    # ─── Trigger Handlers ─────────────────────────────────────

    async def _handle_trigger(
        self, node: Node, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Triggers just pass data through."""
        return {"output": payload}

    # ─── Agent Node Handlers ──────────────────────────────────

    async def _handle_agent(
        self, node: Node, config: Dict[str, Any], payload: Dict[str, Any],
        event_queue: Optional[asyncio.Queue] = None, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Call an agent with the payload, using ChatService for full tools/streaming."""
        agent_id = config.get("agent_id")
        if not agent_id:
            return {"output": {"error": "No agent_id configured"}}

        # Build the prompt from config or payload
        input_template: str = config.get("input_template", "{{message}}")
        prompt = self._render_template(input_template, payload)

        from app.models.agent import Agent
        from app.services.chat_service import ChatService
        
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self.session.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            return {"output": {"error": "Agent not found in DB"}}

        if not conversation_id:
            # Fallback to pure LLM call for headless workflows
            model = config.get("model", agent.model or "gemini/gemini-2.5-flash")
            system_prompt = f"You are {agent.name}. {agent.soul or ''} {agent.mind or ''}"
            response = await self._call_llm(prompt, model, system_prompt)
            output_key = config.get("output_key", "agent_response")
            return {"output": {output_key: response, "agent_id": agent_id}}

        # Full ChatService execution
        chat_service = ChatService(
            provider_registry=self.provider_registry,
            tool_registry=self.tool_registry,
            session=self.session
        )

        # Inject prompt into history as user message quietly first if it's substantial
        # But we'll just pass it as the "first" message dynamically handled by ChatService
        # Actually, let's just let the agent context see it by creating a fake user message, 
        # or we can just send it as a User user_message natively to ChatService.
        from app.services.conversation_service import ConversationService
        conv_svc = ConversationService(self.session)
        await conv_svc.add_message(
            conversation_id, "user", prompt,
        )

        final_response = ""
        # Route agent chunks/tool calls into the event queue
        async for event in chat_service._run_agent_turn(
            conversation_id, agent, max_tool_iters=15, is_group=True
        ):
            if event_queue:
                await event_queue.put(event)
            if event.get("type") == "chunk" and event.get("delta"):
                final_response += event["delta"]
        
        output_key = config.get("output_key", "agent_response")
        return {"output": {output_key: final_response, "agent_id": agent_id}}

    # ─── Tool Node Handlers ───────────────────────────────────

    async def _handle_tool(
        self, node: Node, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        sub = node.sub_type

        if sub == "http_request":
            return await self._tool_http_request(config, payload)
        elif sub == "web_scrape":
            return await self._tool_web_scrape(config, payload)
        elif sub == "file_read":
            return await self._tool_file_read(config, payload)
        elif sub == "db_query":
            return await self._tool_db_query(config, payload)

        return {"output": {"error": f"Unknown tool sub_type: {sub}"}}

    async def _tool_http_request(
        self, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = self._render_template(config.get("url", ""), payload)
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body_template = config.get("body", "")
        body = self._render_template(body_template, payload) if body_template else None

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, url, headers=headers, content=body)
            try:
                resp_data = resp.json()
            except Exception:
                resp_data = resp.text
            return {"output": {"status_code": resp.status_code, "response": resp_data}}

    async def _tool_web_scrape(
        self, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = self._render_template(config.get("url", ""), payload)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            return {"output": {"content": resp.text[:5000], "url": url}}

    async def _tool_file_read(
        self, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        filepath = config.get("filepath", "")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return {"output": {"file_content": content, "filepath": filepath}}
        except Exception as e:
            return {"output": {"error": str(e)}}

    async def _tool_db_query(
        self, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Placeholder — would need safe query execution
        query = config.get("query", "")
        return {"output": {"query": query, "result": "DB query execution not yet implemented"}}

    # ─── Data Node Handlers ───────────────────────────────────

    async def _handle_data(
        self, node: Node, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        sub = node.sub_type

        if sub == "set_variable":
            key = config.get("key", "variable")
            value_template = config.get("value", "")
            value = self._render_template(value_template, payload)
            
            # Special case for updating memory directly using set_variable if desired, 
            # though save_memory is better. We'll just set it in runtime context.
            return {"output": {key: value}}

        elif sub == "save_memory":
            key = config.get("key", "")
            value_template = config.get("value", "")
            value = self._render_template(value_template, payload)
            
            meta = payload.get("_workflow_meta", {})
            wf_id = meta.get("workflow_id")
            ag_id = meta.get("agent_id")
            ch_id = meta.get("channel_id")
            
            if wf_id and key:
                memory = await self.service.get_workflow_memory(wf_id, ag_id, ch_id)
                memory_data = json.loads(memory.memory_json) if memory and memory.memory_json else {}
                memory_data[key] = value
                await self.service.update_workflow_memory(wf_id, memory_data, ag_id, ch_id)
                # Also update the runtime context memory block to keep it in sync
                current_runtime_memory = payload.get("memory", {})
                current_runtime_memory[key] = value
                return {"output": {"memory": current_runtime_memory, f"saved_memory_{key}": value}}
                
            return {"output": {"error": "Missing workflow meta or key for save_memory"}}

        elif sub == "transform_json":
            # Extract or map a key path from payload using template string
            template_str = config.get("template", "")
            if template_str:
                rendered = self._render_template(template_str, payload)
                # Try to parse it back to JSON if it represents a JSON structure
                try:
                    rendered = json.loads(rendered)
                except Exception:
                    pass
                return {"output": {"transformed": rendered}}
            else:
                key_path = config.get("key_path", "")
                result = payload
                for part in key_path.split("."):
                    if isinstance(result, dict):
                        result = result.get(part, {})
                return {"output": {"transformed": result}}

        elif sub == "template":
            template_str = config.get("template", "")
            rendered = self._render_template(template_str, payload)
            return {"output": {"rendered": rendered}}

        return {"output": {}}


    # ─── Logic Node Handlers ──────────────────────────────────

    async def _handle_logic(
        self, node: Node, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        sub = node.sub_type

        if sub == "condition":
            return await self._logic_condition(config, payload)
        elif sub == "switch":
            return await self._logic_switch(config, payload)
        elif sub == "loop":
            return await self._logic_loop(config, payload)
        elif sub == "delay":
            return await self._logic_delay(config, payload)
        elif sub == "merge":
            return {"output": payload}  # Merge just passes through
        elif sub == "branch":
            return await self._logic_condition(config, payload)  # Same as condition

        return {"output": {}}

    async def _logic_condition(
        self, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a condition and route via handle."""
        field = config.get("field", "")
        operator = config.get("operator", "equals")
        compare_value = config.get("value", "")

        actual_value = str(payload.get(field, ""))

        result = False
        if operator == "equals":
            result = actual_value == compare_value
        elif operator == "not_equals":
            result = actual_value != compare_value
        elif operator == "contains":
            result = compare_value in actual_value
        elif operator == "greater_than":
            try:
                result = float(actual_value) > float(compare_value)
            except ValueError:
                result = False
        elif operator == "less_than":
            try:
                result = float(actual_value) < float(compare_value)
            except ValueError:
                result = False
        elif operator == "exists":
            result = field in payload and payload[field] is not None

        handle = "true" if result else "false"
        return {"output": {"condition_result": result}, "route_handle": handle}

    async def _logic_switch(
        self, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Multi-condition switch node."""
        field = config.get("field", "")
        cases: dict = config.get("cases", {})
        actual = str(payload.get(field, ""))

        for case_name, case_value in cases.items():
            if actual == str(case_value):
                return {"output": {"switch_matched": case_name}, "route_handle": case_name}

        return {"output": {"switch_matched": "default"}, "route_handle": "default"}

    async def _logic_loop(
        self, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare loop items — actual iteration happens in _execute_from."""
        items_field = config.get("items_field", "items")
        items = payload.get(items_field, [])
        if not isinstance(items, list):
            items = [items]
        return {"output": {}, "loop_items": items}

    async def _logic_delay(
        self, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        seconds = config.get("seconds", 1)
        await asyncio.sleep(min(seconds, 300))  # Max 5 minutes
        return {"output": {"delayed_seconds": seconds}}

    # ─── Human Interaction Handlers ───────────────────────────

    async def _handle_human(
        self, node: Node, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pause workflow for human approval."""
        sub = node.sub_type

        if sub == "human_approval":
            message = config.get("message", "Workflow requires human approval")
            # In a real system, this would create a HITL request and suspend
            # For now, raise a pause exception
            raise WorkflowPaused(f"Human approval required: {message}")

        return {"output": {}}

    # ─── Legacy Action Handlers ───────────────────────────────

    async def _handle_action(
        self, node: Node, config: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Backward-compatible action node handling."""
        sub = node.sub_type

        if sub == "summarize":
            text = payload.get("data", "") or payload.get("text", "")
            prompt = f"Summarize the following text:\n\n{text}"
            response = await self._call_llm(prompt, "gemini/gemini-2.5-flash")
            return {"output": {"summary": response}}

        elif sub == "email_draft":
            context = payload.get("summary", "") or payload.get("text", "")
            prompt = f"Draft a professional email based on this context:\n\n{context}"
            response = await self._call_llm(prompt, "gemini/gemini-2.5-flash")
            return {"output": {"email_draft": response}}

        elif sub == "notify":
            print(f"NOTIFICATION SENT: {payload}")
            return {"output": {"notified": True}}

        return {"output": {}}

    # ─── Parallel Execution Handler ──────────────────────────

    async def _handle_parallel(self, node, payload, event_queue=None, conversation_id=None):
        """Handle parallel execution node — fork into branches and gather results."""
        import asyncio

        config = {}
        if node.config_json:
            try:
                config = json.loads(node.config_json)
            except (json.JSONDecodeError, TypeError):
                pass

        branches = config.get("branches", [])
        merge_strategy = config.get("merge_strategy", "merge_all")

        if not branches:
            return payload

        async def _run_branch(branch_config):
            """Execute a single branch of the parallel node."""
            branch_payload = dict(payload)
            branch_payload.update(branch_config.get("input", {}))
            return branch_payload

        # Execute all branches concurrently
        tasks = [asyncio.create_task(_run_branch(b)) for b in branches]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results based on strategy
        merged = dict(payload)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                merged[f"branch_{i}_error"] = str(result)
            elif isinstance(result, dict):
                merged.update(result)

        if event_queue:
            await event_queue.put({
                "type": "node_complete",
                "node_id": node.id,
                "node_type": "parallel",
                "branches_executed": len(branches),
            })

        return merged

    # ─── Utilities ────────────────────────────────────────────

    def _resolve_path(self, data: Dict[str, Any], path: str) -> Any:
        parts = path.split('.')
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return ""
        return current

    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Substitute {{variables.path}} using dot-notation."""
        if not template or not isinstance(template, str):
            return template
            
        matches = re.findall(r"\{\{(.*?)\}\}", template)
        result = template
        for match in matches:
            clean_match = match.strip()
            val = self._resolve_path(data, clean_match)
            # Replace exactly the block matched
            result = result.replace(f"{{{{{match}}}}}", str(val) if val is not None else "")
        return result


    async def _call_llm(
        self, prompt: str, model_string: str, system_prompt: str = ""
    ) -> str:
        """Call an LLM provider and collect the full response."""
        if "/" in model_string:
            provider_name, model_id = model_string.split("/", 1)
        else:
            provider_name, model_id = "gemini", model_string

        provider = self.provider_registry.get(provider_name)
        messages = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        messages.append(ChatMessage(role="user", content=prompt))

        full_response = ""
        async for chunk in provider.stream(messages, model_id):
            if chunk.delta:
                full_response += chunk.delta

        return full_response


class WorkflowPaused(Exception):
    """Raised when a workflow is paused (e.g. human approval needed)."""
    pass

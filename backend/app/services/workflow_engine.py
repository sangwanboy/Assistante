import json
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import Node
from app.services.workflow_service import WorkflowService
from app.providers.registry import ProviderRegistry
from app.providers.base import ChatMessage
from app.tools.registry import ToolRegistry


class WorkflowEngine:
    def __init__(self, session: AsyncSession, provider_registry: ProviderRegistry, tool_registry: Optional[ToolRegistry] = None):
        self.session = session
        self.workflow_service = WorkflowService(session)
        self.provider_registry = provider_registry
        self.tool_registry = tool_registry

    async def execute_workflow(self, workflow_id: str, trigger_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a workflow given its ID and an initial payload (e.g. from a webhook).
        """
        workflow = await self.workflow_service.get_workflow(workflow_id)
        if not workflow or not workflow.is_active:
            return {"status": "error", "message": "Workflow not found or inactive."}

        # 1. Build adjacency list for DAG traversal
        nodes_by_id = {node.id: node for node in workflow.nodes}
        
        # Find trigger node(s)
        trigger_nodes = [node for node in workflow.nodes if node.type == "trigger"]
        if not trigger_nodes:
            return {"status": "error", "message": "No trigger node found."}

        # We assume one simple linear path for now, but could be expanded to true DAG
        adjacency = {node.id: [] for node in workflow.nodes}
        for edge in workflow.edges:
            if edge.source_node_id in adjacency:
                adjacency[edge.source_node_id].append(edge.target_node_id)

        # 2. Execution Loop
        start_node = trigger_nodes[0]
        context_payload = trigger_payload.copy()
        
        current_node_id = start_node.id
        execution_log = []

        while current_node_id:
            node = nodes_by_id[current_node_id]
            config = json.loads(node.config_json) if node.config_json else {}
            
            # Execute node logic
            try:
                result = await self._execute_node(node, config, context_payload)
                context_payload.update(result)
                execution_log.append({"node_id": node.id, "type": node.sub_type, "status": "success", "output": result})
            except Exception as e:
                execution_log.append({"node_id": node.id, "type": node.sub_type, "status": "error", "error": str(e)})
                return {"status": "error", "execution_log": execution_log}

            # Move to next node
            next_nodes = adjacency.get(current_node_id, [])
            if next_nodes:
                current_node_id = next_nodes[0]  # Just take first branch for MVP
            else:
                break
                
        return {"status": "success", "final_payload": context_payload, "execution_log": execution_log}

    async def _execute_node(self, node: Node, config: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes an individual node's logic.
        """
        if node.type == "trigger":
            # Just pass the payload through
            return payload
            
        elif node.type == "action":
            sub = node.sub_type
            if sub == "summarize":
                # Uses LLM to summarize
                text_to_summarize = payload.get("data", "") or payload.get("text", "")
                prompt = f"Summarize the following text:\n\n{text_to_summarize}"
                
                # Use default model
                response = await self._call_llm(prompt, "gemini/gemini-2.5-flash")
                return {"summary": response}
                
            elif sub == "email_draft":
                # Drafts an email
                context = payload.get("summary", "") or payload.get("text", "")
                prompt = f"Draft a professional email based on this context:\n\n{context}"
                response = await self._call_llm(prompt, "gemini/gemini-2.5-flash")
                return {"email_draft": response}
                
            elif sub == "notify":
                # Mock notification
                print(f"NOTIFICATION SENT: {payload}")
                return {"notified": True}
                
        return {}

    async def _call_llm(self, prompt: str, model_string: str) -> str:
        """Call an LLM provider with a simple prompt and collect the full response."""
        # Parse provider/model string
        if "/" in model_string:
            provider_name, model_id = model_string.split("/", 1)
        else:
            provider_name, model_id = "gemini", model_string

        provider = self.provider_registry.get(provider_name)
        messages = [ChatMessage(role="user", content=prompt)]

        full_response = ""
        async for chunk in provider.stream(messages, model_id):
            if chunk.delta:
                full_response += chunk.delta

        return full_response

from typing import Any
import json
from sqlalchemy import select
from app.tools.base import BaseTool
from app.db.engine import async_session
from app.models.agent import Agent, new_id

class AgentManagerTool(BaseTool):
    @property
    def name(self) -> str:
        return "AgentManagerTool"

    @property
    def description(self) -> str:
        return (
            "Creates, reads, updates, or deletes AI Agents in the system. "
            "Use this tool when the user asks you to create a new specialized agent, "
            "update an existing one's personality/tools, or delete an agent."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "What to do: 'create', 'update', 'delete', or 'list'",
                    "enum": ["create", "update", "delete", "list"]
                },
                "agent_id": {
                    "type": "string",
                    "description": "The ID of the agent (required for update and delete)"
                },
                "name": {"type": "string", "description": "Name of the agent"},
                "description": {"type": "string", "description": "Short description of the agent"},
                "system_prompt": {"type": "string", "description": "The system prompt defining the agent's behavior"},
                "model": {"type": "string", "description": "The model to use (e.g. 'gemini/gemini-2.5-flash')"},
                "provider": {"type": "string", "description": "The provider (e.g. 'gemini', 'openai', 'anthropic')"},
                "personality_tone": {"type": "string", "description": "e.g. professional, friendly, sarcastic"},
                "personality_traits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of traits, e.g. ['helpful', 'creative']"
                },
                "communication_style": {"type": "string", "description": "e.g. formal, casual, concise"},
                "reasoning_style": {"type": "string", "description": "e.g. analytical, creative, step-by-step"},
                "memory_context": {"type": "string", "description": "Persistent background knowledge for the agent"},
                "memory_instructions": {"type": "string", "description": "Standing rules the agent must always follow"},
                "enabled_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tool names the agent can use (e.g. ['WebSearchTool', 'FileManagerTool'])"
                }
            },
            "required": ["action"]
        }

    async def execute(self, **params: Any) -> str:
        action = params.get("action")
        
        async with async_session() as session:
            if action == "list":
                result = await session.execute(select(Agent.id, Agent.name, Agent.description))
                agents = [{"id": r[0], "name": r[1], "description": r[2]} for r in result.all()]
                return json.dumps(agents, indent=2)
                
            if action == "create":
                agent = Agent(
                    id=new_id(),
                    name=params.get("name", "New Agent"),
                    description=params.get("description", ""),
                    system_prompt=params.get("system_prompt", "You are a helpful assistant."),
                    model=params.get("model", "gemini/gemini-2.5-flash"),
                    provider=params.get("provider", "gemini"),
                    personality_tone=params.get("personality_tone", ""),
                    personality_traits=json.dumps(params.get("personality_traits", [])) if "personality_traits" in params else "[]",
                    communication_style=params.get("communication_style", ""),
                    reasoning_style=params.get("reasoning_style", ""),
                    memory_context=params.get("memory_context", ""),
                    memory_instructions=params.get("memory_instructions", ""),
                    enabled_tools=json.dumps(params.get("enabled_tools", [])) if "enabled_tools" in params else "[]",
                    is_active=True
                )
                session.add(agent)
                await session.commit()
                return f"Agent '{agent.name}' created successfully with ID: {agent.id}"
                
            # For update and delete, we need agent_id
            agent_id = params.get("agent_id")
            if not agent_id:
                return "Error: agent_id is required for update or delete actions."
                
            agent = await session.get(Agent, agent_id)
            if not agent:
                return f"Error: Agent with ID {agent_id} not found."
                
            if action == "delete":
                if getattr(agent, "is_system", False):
                    return f"Error: Cannot delete {agent.name} because it is a system agent."
                await session.delete(agent)
                await session.commit()
                return f"Agent '{agent.name}' deleted successfully."
                
            if action == "update":
                if "name" in params: agent.name = params["name"]
                if "description" in params: agent.description = params["description"]
                if "system_prompt" in params: agent.system_prompt = params["system_prompt"]
                if "model" in params: agent.model = params["model"]
                if "provider" in params: agent.provider = params["provider"]
                if "personality_tone" in params: agent.personality_tone = params["personality_tone"]
                if "personality_traits" in params: agent.personality_traits = json.dumps(params["personality_traits"])
                if "communication_style" in params: agent.communication_style = params["communication_style"]
                if "reasoning_style" in params: agent.reasoning_style = params["reasoning_style"]
                if "memory_context" in params: agent.memory_context = params["memory_context"]
                if "memory_instructions" in params: agent.memory_instructions = params["memory_instructions"]
                if "enabled_tools" in params: agent.enabled_tools = json.dumps(params["enabled_tools"])
                
                await session.commit()
                return f"Agent '{agent.name}' updated successfully."
                
        return "Error: Unknown action."

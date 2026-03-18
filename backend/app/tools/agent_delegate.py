from typing import Any
import json
from sqlalchemy import select, func
from app.tools.base import BaseTool
from app.db.engine import async_session
from app.models.agent import Agent


class AgentDelegationTool(BaseTool):
    """Tool that allows the Main Agent to delegate tasks to other specialized agents.

    The delegated work is persisted in the target agent's own conversation,
    so users can browse the full work history by clicking on that agent in Chat.
    """

    def __init__(self, provider_registry=None, tool_registry=None):
        self._provider_registry = provider_registry
        self._tool_registry = tool_registry

    @property
    def name(self) -> str:
        return "AgentDelegationTool"

    @property
    def description(self) -> str:
        return (
            "Delegates a task to another specialized agent and returns their response. "
            "The task is sent to the agent's own chat, so the user can view the full "
            "work history by opening that agent's conversation. "
            "You can specify the agent by name (case-insensitive) or by ID. "
            "Use this tool when the user asks you to send work to another agent "
            "(e.g. 'ask Marketing to create a campaign plan')."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": (
                        "The name of the target agent (case-insensitive). "
                        "E.g. 'Marketing', 'Coder', 'Analyst'. "
                        "Either agent_name or agent_id must be provided."
                    )
                },
                "target_agent_id": {
                    "type": "string",
                    "description": "The UUID of the target agent. Use agent_name instead if you know the name."
                },
                "task": {
                    "type": "string",
                    "description": (
                        "A clear, detailed description of the task to delegate. "
                        "Be specific about what output is expected. "
                        "This will be sent as-is to the target agent."
                    )
                }
            },
            "required": ["task"]
        }

    async def execute(self, **params: Any) -> str:
        agent_name = params.get("agent_name")
        target_agent_id = params.get("target_agent_id")
        task = params.get("task")

        if not task:
            return "Error: 'task' parameter is required."

        if not agent_name and not target_agent_id:
            return "Error: Either 'agent_name' or 'target_agent_id' must be provided."

        try:
            async with async_session() as session:
                # Resolve agent by name or ID
                target_agent = None
                if target_agent_id:
                    target_agent = await session.get(Agent, target_agent_id)
                elif agent_name:
                    # Case-insensitive name lookup
                    stmt = select(Agent).where(
                        func.lower(Agent.name) == agent_name.lower()
                    )
                    result = await session.execute(stmt)
                    target_agent = result.scalar_one_or_none()

                if not target_agent:
                    identifier = agent_name or target_agent_id
                    # List available agents so the LLM can self-correct
                    all_stmt = select(Agent.id, Agent.name, Agent.description)
                    all_result = await session.execute(all_stmt)
                    available = [
                        {"id": r[0], "name": r[1], "description": r[2]}
                        for r in all_result.all()
                    ]
                    return (
                        f"Error: No agent found matching '{identifier}'.\n"
                        f"Available agents:\n{json.dumps(available, indent=2)}"
                    )

                # 1. Determine origin agent (the one calling the tool)
                origin_agent_id = params.get("_agent_id") or params.get("agent_id")

                # Prevent self-delegation
                if target_agent.id == origin_agent_id:
                    return f"Error: You attempted to delegate to '{target_agent.name}', which is yourself. You are already handling this conversation. Please delegate to a DIFFERENT specialized agent instead (e.g., 'Web Researcher', 'Data Analyst', 'Research Specialist', 'Technical Assistant', 'Content Creator')."

                if getattr(target_agent, "is_system", False) and origin_agent_id != target_agent.id:
                    # Allow delegation to system only if not self
                    pass 

                # Use ChatService to delegate — this persists work in the agent's conversation
                from app.services.chat_service import ChatService

                service = ChatService(
                    provider_registry=self._provider_registry,
                    tool_registry=self._tool_registry,
                    session=session,
                )

                response_text, conv_id = await service.delegate_to_agent(
                    target_agent_id=target_agent.id,
                    prompt=task,
                    delegated_by="Main Agent",
                )

                return (
                    f"### ✅ Delegation Success\n"
                    f"**Target Agent:** {target_agent.name}\n"
                    f"**Task Description:** {task}\n"
                    f"**Agent Response:**\n\n{response_text}\n\n"
                    f"---\n"
                    f"*Work history for this task is stored in [{target_agent.name}'s conversation](/chat/{conv_id}).*"
                )

        except Exception as e:
            return f"Error during delegation: {str(e)}"

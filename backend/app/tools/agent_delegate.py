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
                "agent_id": {
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
        agent_id = params.get("agent_id")
        task = params.get("task")

        if not task:
            return "Error: 'task' parameter is required."

        if not agent_name and not agent_id:
            return "Error: Either 'agent_name' or 'agent_id' must be provided."

        try:
            async with async_session() as session:
                # Resolve agent by name or ID
                target_agent = None
                if agent_id:
                    target_agent = await session.get(Agent, agent_id)
                elif agent_name:
                    # Case-insensitive name lookup
                    stmt = select(Agent).where(
                        func.lower(Agent.name) == agent_name.lower()
                    )
                    result = await session.execute(stmt)
                    target_agent = result.scalar_one_or_none()

                if not target_agent:
                    identifier = agent_name or agent_id
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

                # Prevent self-delegation
                if getattr(target_agent, "is_system", False):
                    return "Error: Cannot delegate tasks to the system orchestrator (yourself)."

                # Use ChatService to delegate — this persists work in the agent's conversation
                from app.services.chat_service import ChatService
                from app.providers.registry import ProviderRegistry

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
                    f"✅ Task completed by {target_agent.name}.\n\n"
                    f"**Response:**\n{response_text}\n\n"
                    f"(Work history saved in {target_agent.name}'s conversation: {conv_id})"
                )

        except Exception as e:
            return f"Error during delegation: {str(e)}"

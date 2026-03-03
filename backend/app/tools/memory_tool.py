"""
Memory tools that allow agents to save and recall persistent memories.
These memories persist across conversations via the agent's memory_context field.
"""
import logging
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class SaveMemoryTool(BaseTool):
    """Tool for agents to save persistent facts/notes to their memory."""

    @property
    def name(self) -> str:
        return "save_memory"

    @property
    def description(self) -> str:
        return (
            "Save a persistent memory or fact that you want to remember across conversations. "
            "Use this when the user tells you something important about themselves, their preferences, "
            "their project, or any other fact you should remember for future conversations. "
            "Each call appends to your memory — it does not overwrite previous memories."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "The fact or piece of information to remember. Be concise but specific. Example: 'User prefers Python over JavaScript' or 'User is building a trading platform'.",
                },
            },
            "required": ["fact"],
        }

    async def execute(self, **kwargs) -> str:
        fact = kwargs.get("fact", "").strip()
        if not fact:
            return "Error: No fact provided to save."

        # We need a DB session to persist this. Access via the tool context.
        agent_id = kwargs.get("_agent_id")
        session = kwargs.get("_session")

        if not agent_id or not session:
            return "Error: Cannot save memory — no agent context available."

        from app.models.agent import Agent
        agent = await session.get(Agent, agent_id)
        if not agent:
            return f"Error: Agent {agent_id} not found."

        # Append to existing memory
        current = agent.memory_context or ""
        if current:
            current += "\n"
        current += f"- {fact}"
        agent.memory_context = current
        await session.commit()

        logger.info(f"[Memory] Agent '{agent.name}' saved memory: {fact}")
        return f"Memory saved: '{fact}'. You now have {len(current.splitlines())} memories stored."


class RecallMemoriesTool(BaseTool):
    """Tool for agents to recall all their stored memories."""

    @property
    def name(self) -> str:
        return "recall_memories"

    @property
    def description(self) -> str:
        return (
            "Recall all your stored persistent memories. Use this when you want to check "
            "what you know about the user or their project from previous conversations."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs) -> str:
        agent_id = kwargs.get("_agent_id")
        session = kwargs.get("_session")

        if not agent_id or not session:
            return "No agent context available — cannot recall memories."

        from app.models.agent import Agent
        agent = await session.get(Agent, agent_id)
        if not agent:
            return f"Agent {agent_id} not found."

        memories = agent.memory_context or ""
        instructions = agent.memory_instructions or ""

        parts = []
        if memories:
            parts.append(f"## Stored Memories\n{memories}")
        if instructions:
            parts.append(f"## Standing Instructions\n{instructions}")

        if not parts:
            return "You have no stored memories or standing instructions."

        return "\n\n".join(parts)

"""
Memory tools that allow agents to save and recall persistent memories.
These memories persist across conversations via the agent's memory_context field.
"""
import logging
from app.tools.base import BaseTool
from app.services.brain_service import AgentBrainService

logger = logging.getLogger(__name__)

class SaveMemoryTool(BaseTool):
    """Tool for agents to save persistent facts/notes to their memory."""

    @property
    def name(self) -> str:
        return "save_memory"

    @property
    def description(self) -> str:
        return (
            "Save a persistent memory or fact about the user or project. "
            "This writes directly to your MEMORY.md brain file, ensuring "
            "it is remembered across all future conversations. "
            "Each call appends to your memory."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "The fact to remember. Example: 'User prefers Python over JavaScript'.",
                },
            },
            "required": ["fact"],
        }

    async def execute(self, **kwargs) -> str:
        fact = kwargs.get("fact", "").strip()
        if not fact:
            return "Error: No fact provided to save."

        agent_id = kwargs.get("_agent_id")
        session = kwargs.get("_session")
        if not agent_id or not session:
            return "Error: Cannot save memory — no agent context available."

        from app.models.agent import Agent
        agent = await session.get(Agent, agent_id)
        if not agent:
            return f"Error: Agent {agent_id} not found."

        # File-based memory append
        total_lines = AgentBrainService.append_memory(agent.name, fact)
        
        # Also append to DB for backward compatibility if needed, but file is primary
        current = agent.memory_context or ""
        if current:
            current += "\n"
        current += f"- {fact}"
        agent.memory_context = current
        await session.commit()

        logger.info(f"[Memory] Agent '{agent.name}' saved memory: {fact}")
        return f"Memory saved to MEMORY.md: '{fact}'. Total entries: {total_lines}."


class RecallMemoriesTool(BaseTool):
    """Tool for agents to recall all their stored memories."""

    @property
    def name(self) -> str:
        return "recall_memories"

    @property
    def description(self) -> str:
        return "Recall all your stored persistent memories from your MEMORY.md file and recent daily logs."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs) -> str:
        agent_id = kwargs.get("_agent_id")
        session = kwargs.get("_session")

        if not agent_id or not session:
            return "No agent context available."

        from app.models.agent import Agent
        agent = await session.get(Agent, agent_id)
        if not agent:
            return f"Agent {agent_id} not found."

        memory_file = AgentBrainService.read_memory(agent.name)
        recent_logs = AgentBrainService.read_recent_logs(agent.name, days=2)

        parts = []
        if memory_file.strip():
            parts.append(f"## MEMORY.md\n{memory_file}")
        elif agent.memory_context:
            parts.append(f"## Memory (Legacy DB)\n{agent.memory_context}")

        if recent_logs.strip():
            parts.append(f"## Recent Daily Logs\n{recent_logs}")

        if not parts:
            return "You have no stored memories."

        return "\n\n".join(parts)


class WriteDailyLogTool(BaseTool):
    """Tool for agents to write entries to their daily log."""

    @property
    def name(self) -> str:
        return "write_daily_log"

    @property
    def description(self) -> str:
        return (
            "Write an entry to today's daily log file. "
            "Use this to summarize completed tasks, note important progress, "
            "or leave a handoff message for your future self. "
            "Entries are timestamped automatically."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "entry": {
                    "type": "string",
                    "description": "The log entry content. Can be multi-line markdown.",
                },
            },
            "required": ["entry"],
        }

    async def execute(self, **kwargs) -> str:
        entry = kwargs.get("entry", "").strip()
        if not entry:
            return "Error: No entry provided."

        agent_id = kwargs.get("_agent_id")
        session = kwargs.get("_session")
        if not agent_id or not session:
            return "Error: Cannot write log — no agent context available."

        from app.models.agent import Agent
        agent = await session.get(Agent, agent_id)
        if not agent:
            return f"Error: Agent {agent_id} not found."

        log_path = AgentBrainService.append_daily_log(agent.name, entry)
        logger.info(f"[DailyLog] Agent '{agent.name}' wrote log entry.")

        import os
        filename = os.path.basename(log_path)
        return f"Successfully appended to today's log ({filename})."

from app.tools.base import BaseTool
from sqlalchemy import select
from app.models.agent import Agent

class SessionStatusTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_session_status"

    @property
    def description(self) -> str:
        return "Get information about your current session, including what model and provider you are running on."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, **kwargs) -> str:
        agent_id = kwargs.get("_agent_id")
        session = kwargs.get("_session")
        
        if not agent_id or not session:
            return "Unable to determine session details: Missing agent_id or database session context."

        stmt = select(Agent).where(Agent.id == agent_id)
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            return "Unable to resolve your agent identity from the database."

        response = (
            f"**Session Status Report**\n"
            f"- **Agent ID**: {agent.id}\n"
            f"- **Agent Name**: {agent.name}\n"
            f"- **Active Provider**: {agent.provider}\n"
            f"- **Running Model**: {agent.model}\n"
        )
        return response

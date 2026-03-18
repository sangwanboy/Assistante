import json
import asyncio
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent
from app.tools.registry import ToolRegistry

async def main():
    registry = ToolRegistry()
    registry.register_defaults()
    
    async with async_session() as session:
        await registry.load_custom_tools(session)
        result = await session.execute(select(Agent).where(Agent.is_system == True))
        janny = result.scalar_one_or_none()
        
        all_tools = registry.as_provider_format()
        all_tool_names = [t["name"] for t in all_tools]
        
        if janny and janny.enabled_tools:
            enabled_list = json.loads(janny.enabled_tools)
            print("ENABLED:", enabled_list)
            filtered = [t for t in all_tools if t["name"] in enabled_list]
            print("FILTERED:", [t["name"] for t in filtered])
            missing = set(enabled_list) - set(all_tool_names)
            print("MISSING:", missing)

if __name__ == "__main__":
    import sys
    sys.tracebacklimit = 0
    import logging
    logging.disable(logging.CRITICAL)
    asyncio.run(main())
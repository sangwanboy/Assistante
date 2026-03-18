import asyncio
import sys
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent

async def main():
    async with async_session() as session:
        result = await session.execute(select(Agent).where(Agent.is_system == True))
        janny = result.scalar_one_or_none()
        if janny:
            rule = "\n\nCRITICAL CONCURRENCY RULE: If you delegate tasks to multiple agents using the AgentDelegationTool, the system now natively runs these tool calls concurrently in the background. You MUST NOT try to manually mock or bypass the wait time. Always trigger the parallel tools and gracefully await their execution response instead of hallucinating results to save time."
            if "CRITICAL CONCURRENCY RULE" not in janny.system_prompt:
                janny.system_prompt += rule
                await session.commit()
                print("Successfully updated Janny's system prompt.")
            else:
                print("Already updated.")
        else:
            print("Janny not found")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

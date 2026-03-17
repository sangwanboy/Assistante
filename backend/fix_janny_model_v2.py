
import asyncio
import sys
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent

async def fix_janny_model():
    async with async_session() as session:
        # Find Janny (System Agent)
        result = await session.execute(select(Agent).where(Agent.is_system == True))
        janny = result.scalar_one_or_none()
        
        if janny:
            name_safe = janny.name.encode('ascii', 'ignore').decode('ascii')
            print(f"Found Janny: {name_safe}, Current Model: {janny.model}")
            if janny.model == "gemini/gemini-3.1-flash-lite":
                janny.model = "gemini/gemini-2.5-flash"
                await session.commit()
                print(f"Updated Janny model to: {janny.model}")
            else:
                print("Janny model is already updated or different.")
        else:
            print("System Agent (Janny) not found.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_janny_model())

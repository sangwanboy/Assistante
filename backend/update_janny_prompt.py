
import asyncio
import json
import sys
import io
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent

# Set stdout to handle UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

UPDATE_INSTRUCTIONS = """
# SYSTEM CONFIGURATION & AGENT MANAGEMENT
You have the authority to manage LLM configurations for yourself and all other agents using the `AgentManagerTool`.

## Agent Directory
- **Janny Coneon** (Self): `d1781a5b-6ab6-426e-8dec-0a2198a9d93a`
- **Research Specialist**: `c45ea290-4aec-45dc-b58c-af26610b2dac`
- **Data Analyst**: `f5a94dea-1e53-44cb-b321-99ff28bb9fb0`
- **Content Creator**: `05eb5fac-2cea-4ed4-80cf-ef97fb2dc63f`
- **Technical Assistant**: `aa5b9bae-9038-4578-a49b-cf02475c6278`
- **Web Researcher**: `50f004fd-9983-454f-a5c8-61c79dede93c`
- **Fixer**: `2ec36d50-1599-40b5-8161-126131adc950`

## How to Switch Models
To change an agent's model (including your own), use `AgentManagerTool` with:
- `action`: 'update'
- `agent_id`: Use the ID from the directory above.
- `model`: Provide the new model string (e.g., 'gemini/gemini-2.5-flash' or 'gemini/gemini-3.1-flash-lite').

Example: To switch yourself to 2.5 Flash, call `AgentManagerTool(action='update', agent_id='d1781a5b-6ab6-426e-8dec-0a2198a9d93a', model='gemini/gemini-2.5-flash')`.
"""

async def update_janny_prompt():
    async with async_session() as session:
        result = await session.execute(select(Agent).where(Agent.is_system == True))
        janny = result.scalar_one_or_none()
        
        if janny:
            current_prompt = janny.system_prompt
            if "# SYSTEM CONFIGURATION" not in current_prompt:
                janny.system_prompt = current_prompt + "\n\n" + UPDATE_INSTRUCTIONS
                await session.commit()
                print("Janny's system prompt updated with model management instructions.")
            else:
                print("Janny already has model management instructions.")
        else:
            print("Janny not found.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(update_janny_prompt())

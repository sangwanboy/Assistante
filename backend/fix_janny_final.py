import asyncio
import json
from sqlalchemy import select
from app.db.engine import async_session
from app.models.agent import Agent

async def main():
    async with async_session() as session:
        # Get Sentinel ID
        res = await session.execute(select(Agent).where(Agent.name.like('%Sentinel%')))
        sentinel = res.scalar_one_or_none()
        s_text = f"\n- **{sentinel.name}**: `{sentinel.id}`" if sentinel else ""
        
        # Get Janny
        res = await session.execute(select(Agent).where(Agent.is_system == True))
        janny = res.scalar_one_or_none()
        
        if janny:
            tools = json.loads(janny.enabled_tools) if janny.enabled_tools else []
            added_tools = False
            for t in ["workspace_write", "get_datetime"]:
                if t not in tools:
                    tools.append(t)
                    added_tools = True
            
            if added_tools:
                janny.enabled_tools = json.dumps(tools)
            
            prompt_updated = False
            if sentinel and str(sentinel.id) not in (janny.system_prompt or ""):
                print("Adding Sentinel to directory...")
                janny.system_prompt += s_text
                prompt_updated = True
                
            rule = "CRITICAL RULE: When checking the session status, time, or system configuration, you MUST ALWAYS strictly use the tools `get_datetime`, `get_session_status`, and `SystemConfigTool`. NEVER guess."
            if rule not in (janny.system_prompt or ""):
                print("Adding strict time/config rules...")
                janny.system_prompt += f"\n\n{rule}"
                prompt_updated = True
                
            if added_tools or prompt_updated:
                await session.commit()
                print("Janny completely updated!")
            else:
                print("Janny already up to date.")

if __name__ == "__main__":
    asyncio.run(main())
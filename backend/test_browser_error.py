import asyncio
import base64
from app.tools.browser_tool import BrowserTool

async def test():
    tool = BrowserTool()
    print("Testing navigate...")
    res = await tool.execute(action="navigate", url="https://google.com")
    print("Result:", res)
    print("Testing screenshot...")
    res2 = await tool.execute(action="screenshot")
    if "image_base64" in res2:
        print("Screenshot success (omitting base64).")
    else:
        print("Result:", res2)

asyncio.run(test())

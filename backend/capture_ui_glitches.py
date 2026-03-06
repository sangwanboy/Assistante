import asyncio
from playwright.async_api import async_playwright
import time
import os

async def capture_ui_glitches():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        print("Navigating to UI...")
        await page.goto("http://localhost:5173")
        await page.wait_for_timeout(2000)

        await page.screenshot(path=os.path.join(os.getcwd(), "ui_glitch_1_home.png"))

        # Go to Chat
        print("Opening Chat...")
        await page.click("text=Chat")
        await page.wait_for_timeout(1000)

        # Select Janny
        print("Selecting Janny...")
        try:
            await page.click("text=Janny")
        except:
            await page.click(".agent-list-item:has-text('Janny')")
        
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(os.getcwd(), "ui_glitch_2_chat_open.png"))

        # Send test message
        print("Sending test message for get_datetime...")
        await page.fill("textarea", "Use the get_datetime tool to tell me the time.")
        await page.press("textarea", "Enter")

        # Wait a bit to capture any immediate UI feedback (loading state, errors)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(os.getcwd(), "ui_glitch_3_message_sent.png"))
        
        # Wait for potential response or error
        await page.wait_for_timeout(4000)
        await page.screenshot(path=os.path.join(os.getcwd(), "ui_glitch_4_after_wait.png"))

        # Try another tool that triggers HITL (Command Executor)
        print("Sending test message for command_executor...")
        await page.fill("textarea", "Run the command: echo UI Glitch Test")
        await page.press("textarea", "Enter")
        
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(os.getcwd(), "ui_glitch_5_hitl_triggered.png"))
        
        await page.wait_for_timeout(4000)
        await page.screenshot(path=os.path.join(os.getcwd(), "ui_glitch_6_hitl_wait.png"))

        print("Done. Screenshots saved to backend directory.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_ui_glitches())

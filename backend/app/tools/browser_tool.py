from typing import Any
from app.tools.base import BaseTool
from playwright.async_api import async_playwright, Page, BrowserContext
import markdownify
import asyncio

class BrowserManager:
    _playwright = None
    _browser = None
    _context: BrowserContext = None
    _page: Page = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_page(cls) -> Page:
        async with cls._lock:
            if cls._page is None:
                cls._playwright = await async_playwright().start()
                cls._browser = await cls._playwright.chromium.launch(headless=True)
                cls._context = await cls._browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                cls._page = await cls._context.new_page()
            return cls._page

class BrowserTool(BaseTool):
    @property
    def name(self) -> str:
        return "BrowserTool"

    @property
    def description(self) -> str:
        return (
            "A built-in web browser that can navigate to URLs, read content, click elements, "
            "and type text. Use this tool when you need to interact with a specific website or "
            "read its content. Actions: 'navigate', 'read', 'click', 'type', 'evaluate'."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The browser action: 'navigate', 'read', 'click', 'type', 'evaluate'",
                    "enum": ["navigate", "read", "click", "type", "evaluate"]
                },
                "url": {
                    "type": "string",
                    "description": "URL to navigate to (required for 'navigate')"
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to click or type into (required for 'click' and 'type')"
                },
                "text": {
                    "type": "string",
                    "description": "Text to type (required for 'type')"
                },
                "js_code": {
                    "type": "string",
                    "description": "JavaScript code to execute (required for 'evaluate')"
                }
            },
            "required": ["action"]
        }

    async def execute(self, **params: Any) -> str:
        action = params.get("action")
        try:
            page = await BrowserManager.get_page()

            if action == "navigate":
                url = params.get("url")
                if not url: return "Error: url is required for 'navigate'."
                if not url.startswith("http"): url = "https://" + url
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                return f"Navigated to {page.url}. Page title: {await page.title()}"

            elif action == "read":
                # Convert page to Markdown using clean text
                html = await page.content()
                md = markdownify.markdownify(html, heading_style="ATX", strip=["script", "style"])
                # Clean up multiple newlines
                clean_md = "\n".join([line for line in md.split("\n") if line.strip() != ""])
                # Truncate to avoid huge LLM prompts
                return clean_md[:8000] + ("\n...[truncated]" if len(clean_md) > 8000 else "")

            elif action == "click":
                selector = params.get("selector")
                if not selector: return "Error: selector is required for 'click'."
                await page.click(selector, timeout=5000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except:
                    pass
                return f"Clicked element matching '{selector}'."

            elif action == "type":
                selector = params.get("selector")
                text = params.get("text")
                if not selector or not text: return "Error: selector and text are required for 'type'."
                await page.fill(selector, text, timeout=5000)
                return f"Typed text into '{selector}'."

            elif action == "evaluate":
                js_code = params.get("js_code")
                if not js_code: return "Error: js_code is required for 'evaluate'."
                result = await page.evaluate(js_code)
                return f"Evaluation result: {result}"

            else:
                return "Error: Unknown action."

        except Exception as e:
            return f"Browser error: {str(e)}"

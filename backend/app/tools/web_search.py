from app.tools.base import BaseTool
import asyncio
import logging

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for current information. Use this when you need up-to-date facts, news, or information not in your training data."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5,
                },
                "region": {
                    "type": "string",
                    "description": "The region code for search (e.g., 'us-en', 'wt-wt', 'uk-en'). Default: 'us-en'",
                    "default": "us-en",
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, max_results: int = 5, region: str = "us-en", **kwargs) -> str:
        try:
            import random
            from duckduckgo_search import DDGS

            # Add random jitter (100ms - 1500ms) to avoid anti-bot triggers during parallel delegation
            await asyncio.sleep(random.uniform(0.1, 1.5))

            results = []
            with DDGS() as ddgs:
                # Use region='us-en' by default to ensure English results for English queries
                for r in ddgs.text(query, region=region, max_results=max_results):
                    results.append(f"**{r['title']}**\n{r['href']}\n{r['body']}\n")

            if not results:
                # Fallback: Try a broader query if first attempt yielded nothing
                words = query.split()
                if len(words) > 3:
                    broader_query = " ".join(words[:max(3, len(words)//2)])
                    logger.info(f"WebSearchTool: No results for '{query}', trying broader query: '{broader_query}'")
                    for r in ddgs.text(broader_query, region=region, max_results=max_results):
                        results.append(f"**{r['title']}**\n{r['href']}\n{r['body']}\n")
                
                if not results:
                    return f"No results found for query: '{query}'. Try broading your search terms."

            return "\n---\n".join(results)
        except Exception as e:
            return f"Search failed: {str(e)}"

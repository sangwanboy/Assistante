from app.tools.base import BaseTool
import httpx
import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)

class BraveSearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "brave_search"

    @property
    def description(self) -> str:
        return "Search the web using Brave Search API. Use this as a high-quality alternative to DuckDuckGo when deeper or more reliable results are needed."

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
                    "description": "Maximum number of results to return (default: 5, max: 20)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, max_results: int = 5, **kwargs) -> str:
        from app.services.secret_manager import get_secret_manager
        
        api_key = get_secret_manager().get_api_key("brave_search")
        if not api_key:
            return "Brave Search API key not configured. Please provide it in the settings."

        max_retries = 3
        retry_delay = 2.0  # Initial delay in seconds

        for attempt in range(max_retries + 1):
            try:
                headers = {
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                }
                params = {
                    "q": query,
                    "count": min(max_results, 20),
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers=headers,
                        params=params,
                        timeout=15.0
                    )
                    
                    if response.status_code == 429:
                        if attempt < max_retries:
                            import random
                            wait_time = retry_delay * (2 ** attempt) + random.uniform(0.1, 1.0)
                            logger.warning(f"BraveSearchTool: 429 Rate Limit hit. Retrying in {wait_time:.1f}s (Attempt {attempt+1}/{max_retries})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"BraveSearchTool: 429 Rate Limit persists after {max_retries} retries. Falling back to DuckDuckGo.")
                            break # Fallback below
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    results = []
                    web_results = data.get("web", {}).get("results", [])
                    
                    for r in web_results:
                        title = r.get("title", "No title")
                        url = r.get("url", "No URL")
                        description = r.get("description", "No description")
                        results.append(f"**{title}**\n{url}\n{description}\n")
                        
                    if not results:
                        # Fallback within Brave: simplify query
                        words = query.split()
                        if len(words) > 3:
                            broader_query = " ".join(words[:max(3, len(words)//2)])
                            logger.info(f"BraveSearchTool: No results for '{query}', trying broader query: '{broader_query}'")
                            params["q"] = broader_query
                            async with httpx.AsyncClient() as client:
                                response = await client.get(
                                    "https://api.search.brave.com/res/v1/web/search",
                                    headers=headers,
                                    params=params,
                                )
                                if response.is_success:
                                    data = response.json()
                                    web_results = data.get("web", {}).get("results", [])
                                    for r in web_results:
                                        results.append(f"**{r.get('title')}**\n{r.get('url')}\n{r.get('description')}\n")

                    if not results:
                        return f"No Brave search results found for: '{query}'."
                        
                    return "\n---\n".join(results)
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"Brave search HTTP error: {e}")
                if e.response.status_code == 422:
                    return "Error: The Brave Search API key is invalid or expired. Please inform the user they need to update it in the settings. DO NOT retry this search."
                if attempt == max_retries:
                    break # Fallback below
            except Exception as e:
                logger.error(f"Brave search failed: {e}")
                if attempt == max_retries:
                    break # Fallback below

        # Final Fallback to WebSearchTool (DuckDuckGo)
        try:
            from app.tools.web_search import WebSearchTool
            logger.info(f"BraveSearchTool: Entering final fallback to WebSearchTool for query: '{query}'")
            ddg_tool = WebSearchTool()
            return await ddg_tool.execute(query=query, max_results=max_results)
        except Exception as fallback_err:
            logger.error(f"BraveSearchTool: Fallback to WebSearchTool failed: {fallback_err}")
            return f"Search failed after multiple attempts and fallback: {str(fallback_err)}"

import logging
import asyncio
import httpx
from typing import Optional

from app.tools.base import BaseTool
from app.services.secret_manager import get_secret_manager

logger = logging.getLogger(__name__)

class VideoGenerationTool(BaseTool):
    """Tool for generating videos using Luma AI (Dream Machine)."""

    @property
    def name(self) -> str:
        return "video_gen"

    @property
    def description(self) -> str:
        return (
            "Generate high-quality 5-second videos from text descriptions using Luma AI Dream Machine. "
            "Returns a URL to the generated video."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A detailed description of the video to generate.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "16:9", "9:16", "4:3", "3:4"],
                    "description": "Aspect ratio of the generated video.",
                    "default": "16:9",
                },
                "loop": {
                    "type": "boolean",
                    "description": "Whether to make the video a seamless loop.",
                    "default": False,
                },
            },
            "required": ["prompt"],
        }

    async def execute(self, prompt: str, aspect_ratio: str = "16:9", loop: bool = False, **kwargs) -> str:
        sm = get_secret_manager()
        api_key = sm.get_api_key("luma_ai")
        
        if not api_key:
            return "Error: Luma AI API key not found in SecretManager. Please configure it in settings."

        base_url = "https://api.lumalabs.ai/dream-machine/v1/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "loop": loop,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Create generation
                response = await client.post(base_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                gen_id = data.get("id")

                if not gen_id:
                    return f"Error: Failed to get generation ID from Luma AI. Response: {data}"

                # 2. Poll for completion (max 120 seconds)
                # Note: Real-world generation might take longer, but we'll try to give a quick result.
                max_polls = 24  # 120 seconds / 5 seconds
                for i in range(max_polls):
                    # Sleep first to give it a head start
                    await asyncio.sleep(5)
                    
                    status_url = f"{base_url}/{gen_id}"
                    status_response = await client.get(status_url, headers=headers)
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    state = status_data.get("state")
                    if state == "completed":
                        video_url = status_data.get("assets", {}).get("video")
                        if video_url:
                            return f"Generated Video (Luma AI):\n\n<video controls width='100%'>\n  <source src='{video_url}' type='video/mp4'>\n  Your browser does not support the video tag.\n</video>\n\n[Download Video]({video_url})"
                        return f"Error: Video generation completed but no URL was found."
                    
                    if state == "failed":
                        failure_reason = status_data.get("failure_reason", "Unknown error")
                        return f"Error: Luma AI video generation failed: {failure_reason}"
                    
                    # Still processing
                    logger.info(f"Luma AI generation {gen_id} state: {state} (Poll {i+1}/{max_polls})")

                return f"Video generation is still in progress. Generation ID: `{gen_id}`. You can check back in a moment."

        except httpx.HTTPStatusError as e:
            logger.error(f"Luma AI API error: {e}")
            return f"Error calling Luma AI API: {e.response.text}"
        except Exception as e:
            logger.error(f"Luma AI generation failed: {e}")
            return f"Error generating video with Luma AI: {str(e)}"

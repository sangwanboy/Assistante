import logging
import json
from typing import Optional
import httpx
from openai import AsyncOpenAI
from google import genai
from google.genai import types

from app.tools.base import BaseTool
from app.services.secret_manager import get_secret_manager
from app.config import settings

logger = logging.getLogger(__name__)

class ImageGenerationTool(BaseTool):
    """Tool for generating images using DALL-E 3 or Imagen 3."""

    @property
    def name(self) -> str:
        return "image_gen"

    @property
    def description(self) -> str:
        return (
            "Generate high-quality images from text descriptions. "
            "Supports 'dalle-3' (OpenAI) and 'imagen-3' (Google). "
            "Returns a URL to the generated image."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A detailed description of the image to generate.",
                },
                "provider": {
                    "type": "string",
                    "enum": ["openai", "google"],
                    "description": "The AI provider to use. Defaults to 'google'.",
                    "default": "google",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "4:3", "3:4", "16:9", "9:16"],
                    "description": "Aspect ratio of the generated image. Only supported by some providers.",
                    "default": "1:1",
                },
            },
            "required": ["prompt"],
        }

    async def execute(self, prompt: str, provider: str = "google", aspect_ratio: str = "1:1", **kwargs) -> str:
        sm = get_secret_manager()
        
        provider_lower = (provider or "google").lower()
        
        if provider_lower in ("openai", "dalle-3", "dalle3", "dall-e-3"):
            return await self._generate_openai(prompt, sm)
        elif provider_lower in ("google", "imagen-3", "imagen3", "imagen"):
            return await self._generate_google(prompt, sm, aspect_ratio)
        else:
            return f"Error: Unsupported provider '{provider}'. Supported: 'google' (Imagen 3), 'openai' (DALL-E 3)."

    async def _generate_openai(self, prompt: str, sm) -> str:
        api_key = sm.get_api_key("openai")
        if not api_key:
            return "Error: OpenAI API key not found in SecretManager. Please configure it in settings."

        try:
            client = AsyncOpenAI(api_key=api_key)
            response = await client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size="1024x1024",
                quality="standard",
                response_format="url",
            )
            image_url = response.data[0].url
            return f"Generated Image (OpenAI DALL-E 3):\n\n![Generated Image]({image_url})"
        except Exception as e:
            logger.error(f"OpenAI Image Generation failed: {e}")
            return f"Error generating image with OpenAI: {str(e)}"

    async def _generate_google(self, prompt: str, sm, aspect_ratio: str) -> str:
        api_key = sm.get_api_key("gemini")
        if not api_key:
            return "Error: Google Gemini API key not found in SecretManager. Please configure it in settings."

        try:
            # Use the google-genai SDK
            client = genai.Client(api_key=api_key)
            
            response = client.models.generate_images(
                model='imagen-3',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio if aspect_ratio in ["1:1", "4:3", "3:4", "16:9", "9:16"] else "1:1",
                    output_mime_type="image/jpeg",
                )
            )
            
            if not response.generated_images:
                return "Error: Google Imagen 3 failed to generate an image (no results)."
            
            img = response.generated_images[0]
            if hasattr(img, 'image') and img.image.image_bytes:
                import uuid
                import os
                
                # Save to disk
                filename = f"gen_{uuid.uuid4().hex}.jpg"
                save_path = os.path.join("data", "generated_images", filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                with open(save_path, "wb") as f:
                    f.write(img.image.image_bytes)
                
                # Use local URL (8322 is our active port)
                image_url = f"http://127.0.0.1:8322/api/images/{filename}"
                return f"Generated Image (Google Imagen 3):\n\n![Generated Image]({image_url})"
            
            return f"Generated Image (Google Imagen 3): Generated successfully, but bytes were not provided by the SDK."
            
        except Exception as e:
            logger.error(f"Google Image Generation failed: {e}")
            return f"Error generating image with Google: {str(e)}"

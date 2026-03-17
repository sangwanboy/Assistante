from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class SettingsOut(BaseModel):
    openai_api_key_set: bool
    anthropic_api_key_set: bool
    gemini_api_key_set: bool
    brave_search_api_key_set: bool
    ollama_base_url: str
    default_model: str
    default_temperature: float
    default_system_prompt: str


class SettingsUpdate(BaseModel):
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    brave_search_api_key: str | None = None
    ollama_base_url: str | None = None
    default_model: str | None = None
    default_temperature: float | None = None
    default_system_prompt: str | None = None


@router.get("", response_model=SettingsOut)
async def get_settings(request: Request):
    from app.config import settings
    from app.services.secret_manager import get_secret_manager
    sm = get_secret_manager()
    
    return SettingsOut(
        openai_api_key_set=sm.has_api_key("openai"),
        anthropic_api_key_set=sm.has_api_key("anthropic"),
        gemini_api_key_set=sm.has_api_key("gemini"),
        brave_search_api_key_set=sm.has_api_key("brave_search"),
        ollama_base_url=settings.ollama_base_url,
        default_model=settings.default_model,
        default_temperature=settings.default_temperature,
        default_system_prompt=settings.default_system_prompt,
    )


@router.put("")
async def update_settings(req: SettingsUpdate, request: Request):
    from app.config import settings
    from app.services.secret_manager import get_secret_manager
    sm = get_secret_manager()

    if req.openai_api_key is not None:
        settings.openai_api_key = req.openai_api_key
        sm.set_api_key("openai", req.openai_api_key)
        # Re-register provider
        if req.openai_api_key:
            from app.providers.openai_provider import OpenAIProvider
            request.app.state.provider_registry.add_provider("openai", OpenAIProvider(req.openai_api_key))
        else:
            request.app.state.provider_registry.remove_provider("openai")

    if req.anthropic_api_key is not None:
        settings.anthropic_api_key = req.anthropic_api_key
        sm.set_api_key("anthropic", req.anthropic_api_key)
        if req.anthropic_api_key:
            from app.providers.anthropic_provider import AnthropicProvider
            request.app.state.provider_registry.add_provider("anthropic", AnthropicProvider(req.anthropic_api_key))
        else:
            request.app.state.provider_registry.remove_provider("anthropic")

    if req.gemini_api_key is not None:
        settings.gemini_api_key = req.gemini_api_key
        sm.set_api_key("gemini", req.gemini_api_key)
        if req.gemini_api_key:
            from app.providers.gemini_provider import GeminiProvider
            request.app.state.provider_registry.add_provider("gemini", GeminiProvider(req.gemini_api_key))
        else:
            request.app.state.provider_registry.remove_provider("gemini")

    if req.brave_search_api_key is not None:
        settings.brave_search_api_key = req.brave_search_api_key
        sm.set_api_key("brave_search", req.brave_search_api_key)

    if req.ollama_base_url is not None:
        settings.ollama_base_url = req.ollama_base_url
    if req.default_model is not None:
        settings.default_model = req.default_model
    if req.default_temperature is not None:
        settings.default_temperature = req.default_temperature
    if req.default_system_prompt is not None:
        settings.default_system_prompt = req.default_system_prompt

    return {"status": "updated"}

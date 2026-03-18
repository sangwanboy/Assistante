from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.engine import get_session
from app.models.model_config import ModelConfig
from app.providers.litellm_provider import LiteLLMProvider
from app.providers.ollama_provider import OllamaProvider
from app.services.secret_manager import get_secret_manager

router = APIRouter()


MAIN_PROVIDERS = [
    {"id": "openai", "name": "OpenAI", "credential_kind": "api_key", "credential_field": "openai_api_key"},
    {"id": "anthropic", "name": "Anthropic", "credential_kind": "api_key", "credential_field": "anthropic_api_key"},
    {"id": "gemini", "name": "Google Gemini", "credential_kind": "api_key", "credential_field": "gemini_api_key"},
    {"id": "ollama", "name": "Ollama", "credential_kind": "base_url", "credential_field": "ollama_base_url"},
]


class ProviderModelOut(BaseModel):
    id: str
    name: str


class ProviderSettingsOut(BaseModel):
    id: str
    name: str
    credential_kind: str
    credential_field: str
    connected: bool
    models: list[ProviderModelOut]


class SettingsOut(BaseModel):
    openai_api_key_set: bool
    anthropic_api_key_set: bool
    gemini_api_key_set: bool
    brave_search_api_key_set: bool
    ollama_base_url: str
    default_model: str
    default_temperature: float
    default_system_prompt: str
    providers: list[ProviderSettingsOut]


class SettingsUpdate(BaseModel):
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    brave_search_api_key: str | None = None
    ollama_base_url: str | None = None
    default_model: str | None = None
    default_temperature: float | None = None
    default_system_prompt: str | None = None
    provider_keys: dict[str, str | None] | None = None


async def _models_by_provider(db: AsyncSession) -> dict[str, list[ProviderModelOut]]:
    stmt = select(ModelConfig).where(ModelConfig.is_active)
    result = await db.execute(stmt)
    configs = result.scalars().all()

    grouped: dict[str, list[ProviderModelOut]] = {}
    for conf in configs:
        grouped.setdefault(conf.provider, []).append(
            ProviderModelOut(
                id=f"{conf.provider}/{conf.id}",
                name=conf.name,
            )
        )
    return grouped


async def _build_provider_settings(request: Request, db: AsyncSession) -> list[ProviderSettingsOut]:
    sm = get_secret_manager()
    models_grouped = await _models_by_provider(db)

    providers: list[ProviderSettingsOut] = []
    for provider in MAIN_PROVIDERS:
        provider_id = provider["id"]
        connected = True if provider_id == "ollama" else sm.has_api_key(provider_id)

        models: list[ProviderModelOut] = []
        if connected:
            try:
                provider_instance = request.app.state.provider_registry.get(provider_id)
                live_models = await provider_instance.list_models()
                models = [
                    ProviderModelOut(id=f"{provider_id}/{m.id}", name=m.name)
                    for m in live_models
                ]
            except Exception:
                models = models_grouped.get(provider_id, [])

        providers.append(
            ProviderSettingsOut(
                id=provider_id,
                name=provider["name"],
                credential_kind=provider["credential_kind"],
                credential_field=provider["credential_field"],
                connected=connected,
                models=models,
            )
        )

    return providers


def _attach_provider(request: Request, provider_id: str, key_or_url: str):
    registry = request.app.state.provider_registry
    if provider_id == "ollama":
        registry.add_provider("ollama", OllamaProvider(key_or_url or settings.ollama_base_url))
        return

    if settings.use_litellm and provider_id in {"openai", "anthropic", "gemini"}:
        registry.add_provider(provider_id, LiteLLMProvider(provider_id, key_or_url))
        return

    if provider_id == "openai":
        from app.providers.openai_provider import OpenAIProvider

        registry.add_provider("openai", OpenAIProvider(key_or_url))
    elif provider_id == "anthropic":
        from app.providers.anthropic_provider import AnthropicProvider

        registry.add_provider("anthropic", AnthropicProvider(key_or_url))
    elif provider_id == "gemini":
        from app.providers.gemini_provider import GeminiProvider

        registry.add_provider("gemini", GeminiProvider(key_or_url))


@router.get("", response_model=SettingsOut)
async def get_settings(request: Request, db: AsyncSession = Depends(get_session)):
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
        providers=await _build_provider_settings(request, db),
    )


@router.put("")
async def update_settings(req: SettingsUpdate, request: Request):
    sm = get_secret_manager()

    # Dynamic provider updates (new path).
    if req.provider_keys:
        for provider_id, provider_value in req.provider_keys.items():
            if provider_id in {"openai", "anthropic", "gemini"}:
                clean_val = (provider_value or "").strip()
                sm.set_api_key(provider_id, clean_val)
                setattr(settings, f"{provider_id}_api_key", clean_val or None)

                if clean_val:
                    _attach_provider(request, provider_id, clean_val)
                else:
                    request.app.state.provider_registry.remove_provider(provider_id)

            elif provider_id == "ollama":
                new_url = (provider_value or "").strip() or settings.ollama_base_url
                settings.ollama_base_url = new_url
                _attach_provider(request, "ollama", new_url)

    if req.openai_api_key is not None:
        clean_val = req.openai_api_key.strip()
        settings.openai_api_key = clean_val or None
        sm.set_api_key("openai", clean_val)
        if clean_val:
            _attach_provider(request, "openai", clean_val)
        else:
            request.app.state.provider_registry.remove_provider("openai")

    if req.anthropic_api_key is not None:
        clean_val = req.anthropic_api_key.strip()
        settings.anthropic_api_key = clean_val or None
        sm.set_api_key("anthropic", clean_val)
        if clean_val:
            _attach_provider(request, "anthropic", clean_val)
        else:
            request.app.state.provider_registry.remove_provider("anthropic")

    if req.gemini_api_key is not None:
        clean_val = req.gemini_api_key.strip()
        settings.gemini_api_key = clean_val or None
        sm.set_api_key("gemini", clean_val)
        if clean_val:
            _attach_provider(request, "gemini", clean_val)
        else:
            request.app.state.provider_registry.remove_provider("gemini")

    if req.brave_search_api_key is not None:
        settings.brave_search_api_key = req.brave_search_api_key
        sm.set_api_key("brave_search", req.brave_search_api_key)

    if req.ollama_base_url is not None:
        settings.ollama_base_url = req.ollama_base_url
        _attach_provider(request, "ollama", req.ollama_base_url)
    if req.default_model is not None:
        settings.default_model = req.default_model
    if req.default_temperature is not None:
        settings.default_temperature = req.default_temperature
    if req.default_system_prompt is not None:
        settings.default_system_prompt = req.default_system_prompt

    return {"status": "updated"}

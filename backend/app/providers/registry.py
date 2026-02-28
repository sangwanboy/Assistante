from app.config import Settings
from app.providers.base import BaseProvider, ModelInfo


class ProviderRegistry:
    def __init__(self, config: Settings):
        self._providers: dict[str, BaseProvider] = {}

        if config.openai_api_key:
            from app.providers.openai_provider import OpenAIProvider
            self._providers["openai"] = OpenAIProvider(config.openai_api_key)

        if config.anthropic_api_key:
            from app.providers.anthropic_provider import AnthropicProvider
            self._providers["anthropic"] = AnthropicProvider(config.anthropic_api_key)

        if config.gemini_api_key:
            from app.providers.gemini_provider import GeminiProvider
            self._providers["gemini"] = GeminiProvider(config.gemini_api_key)

        from app.providers.ollama_provider import OllamaProvider
        self._providers["ollama"] = OllamaProvider(config.ollama_base_url)

    def get(self, provider_name: str) -> BaseProvider:
        provider = self._providers.get(provider_name)
        if not provider:
            available = list(self._providers.keys())
            raise ValueError(f"Provider '{provider_name}' not found. Available: {available}")
        return provider

    def available_providers(self) -> list[str]:
        return [name for name, p in self._providers.items() if p.is_available()]

    async def all_models(self) -> list[ModelInfo]:
        models = []
        for provider in self._providers.values():
            if provider.is_available():
                try:
                    provider_models = await provider.list_models()
                    models.extend(provider_models)
                except Exception:
                    continue
        return models

    def add_provider(self, name: str, provider: BaseProvider):
        self._providers[name] = provider

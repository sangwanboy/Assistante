from app.providers.base import BaseProvider, ModelInfo
from app.config import settings


class ProviderRegistry:
    def __init__(self):
        import logging
        logger = logging.getLogger(__name__)

        self._providers: dict[str, BaseProvider] = {}

        openai_key = settings.openai_api_key
        if openai_key:
            from app.providers.openai_provider import OpenAIProvider
            self._providers["openai"] = OpenAIProvider(openai_key)
            logger.info("OpenAI provider initialized.")

        anthropic_key = settings.anthropic_api_key
        if anthropic_key:
            from app.providers.anthropic_provider import AnthropicProvider
            self._providers["anthropic"] = AnthropicProvider(anthropic_key)
            logger.info("Anthropic provider initialized.")

        gemini_key = settings.gemini_api_key
        logger.info(f"Gemini API key loaded from settings: {'present' if gemini_key else 'MISSING'}")
        if gemini_key:
            from app.providers.gemini_provider import GeminiProvider
            self._providers["gemini"] = GeminiProvider(gemini_key)
            logger.info("Gemini provider initialized.")

        from app.providers.ollama_provider import OllamaProvider
        self._providers["ollama"] = OllamaProvider(settings.ollama_base_url)
        logger.info("Ollama provider initialized.")

    def get(self, provider_name: str) -> BaseProvider:
        provider = self._providers.get(provider_name)
        if not provider:
            available = list(self._providers.keys())
            raise ValueError(f"Provider '{provider_name}' not found. Available: {available}")
        return provider

    def available_providers(self) -> list[str]:
        return [name for name, p in self._providers.items() if p.is_available()]

    def registered_providers(self) -> list[str]:
        return list(self._providers.keys())

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

    def create_ephemeral(self, provider_name: str, api_key: str) -> BaseProvider:
        """Create a one-off provider instance with a custom API key."""
        if provider_name == "openai":
            from app.providers.openai_provider import OpenAIProvider
            return OpenAIProvider(api_key)
        elif provider_name == "anthropic":
            from app.providers.anthropic_provider import AnthropicProvider
            return AnthropicProvider(api_key)
        elif provider_name == "gemini":
            from app.providers.gemini_provider import GeminiProvider
            return GeminiProvider(api_key)
        elif provider_name == "ollama":
            from app.providers.ollama_provider import OllamaProvider
            return OllamaProvider(api_key)  # api_key = base_url for ollama
        else:
            raise ValueError(f"Cannot create ephemeral provider for '{provider_name}'")

    def add_provider(self, name: str, provider: BaseProvider):
        self._providers[name] = provider

    def remove_provider(self, name: str):
        # Never remove ollama baseline provider from registry.
        if name == "ollama":
            return
        self._providers.pop(name, None)

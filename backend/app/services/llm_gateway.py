import logging
import asyncio
import random
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.providers.base import BaseProvider, ChatMessage, StreamChunk
from app.services.rate_limiter import RateLimitManager
from app.services.redis_client import RedisClient

logger = logging.getLogger(__name__)

_gateway_instance = None


def _is_quota_error(message: str) -> bool:
    msg = (message or "").lower()
    return (
        "resource_exhausted" in msg
        or "quota exceeded" in msg
        or "rate limit" in msg
        or "429" in msg
    )


def _sanitize_provider_error(message: str) -> str:
    if _is_quota_error(message):
        return "Model quota exceeded. Please wait about a minute and retry, or switch to another model/provider."
    return message


def _is_expected_provider_error(message: str) -> bool:
    msg = (message or "").lower()
    return _is_quota_error(msg) or "api key" in msg or "api_key_invalid" in msg or "not configured" in msg

async def get_gateway(registry=None) -> "LLMGateway":
    global _gateway_instance
    if _gateway_instance is None:
        rc = await RedisClient.get_instance()
        _gateway_instance = LLMGateway(RateLimitManager(rc), registry)
    elif registry and _gateway_instance.registry is None:
        _gateway_instance.registry = registry
    return _gateway_instance


class LLMGateway:
    """
    Central gateway for all LLM Provider requests.
    Enforces Global Concurrency Control, Rate Limiting, and Model Routing.
    """

    def __init__(self, rate_limiter: RateLimitManager, registry=None):
        self.rate_limiter = rate_limiter
        self.registry = registry
        self.global_semaphore = asyncio.Semaphore(settings.global_request_limit)
        self._provider_semaphores: dict[str, asyncio.Semaphore] = {}

    def _get_agent_semaphore(self, agent_id: str) -> asyncio.Semaphore:
        if agent_id not in self._provider_semaphores:
            self._provider_semaphores[agent_id] = asyncio.Semaphore(settings.max_requests_per_agent)
        return self._provider_semaphores[agent_id]

    def _estimate_tokens(self, messages: list[ChatMessage]) -> int:
        """Naive token estimation before generation."""
        # roughly 4 chars per token + fixed output expectation
        text_length = sum(len(m.content) for m in messages if isinstance(m.content, str))
        return (text_length // 4) + 1000

    async def stream(
        self,
        provider: BaseProvider,
        messages: list[ChatMessage],
        model: str,
        agent_id: str,
        db: AsyncSession,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        from app.services.model_registry_service import ModelRegistryService
        
        # Determine Limits for Model dynamically from DB/Settings
        caps = await ModelRegistryService.get_effective_capabilities(model, db)
        rpm = caps.get("rpm", 100)
        tpm = caps.get("tpm", 1000000)
        rpd = caps.get("rpd", 10000)
        
        canonical_id = caps.get("canonical_id", model)
        
        estimated_tokens = self._estimate_tokens(messages)

        # 1. Enforce Concurrency Limits
        agent_sem = self._get_agent_semaphore(agent_id)
        async with self.global_semaphore, agent_sem:
            
            # 2. Check Rate Limits
            max_wait_attempts: int = 90 # 3 minutes max wait (at 2s intervals)
            attempts: int = 0
            while attempts < max_wait_attempts:
                status = await self.rate_limiter.check_limits(canonical_id, rpm, tpm, rpd, estimated_tokens)
                
                if status == "allow":
                    break
                elif status == "block":
                    if self.registry:
                        # Attempt to find a fallback provider/model
                        registered = self.registry.registered_providers()
                        available = [p for p in registered if self.registry.get(p).is_available() and p != provider.name]
                        if available:
                            fallback_name = available[0]
                            fallback_provider = self.registry.get(fallback_name)
                            models = await fallback_provider.list_models()
                            if models:
                                logger.warning(f"RPD Blocked for {model}. Falling back to {fallback_name}/{models[0].id}")
                                async for chunk in fallback_provider.stream(messages, models[0].id, **kwargs):
                                    yield chunk
                                return
                    yield StreamChunk(delta="", error=f"Rate limit exceeded (RPD max reached for {model}). Task blocked.")
                    return
                elif status == "delay":
                    attempts += 1
                    # Reduced delay to 2s with small jitter to avoid thundering herd
                    wait_time = 2.0 + random.uniform(-0.5, 0.5)
                    logger.info(f"LLMGateway: Delaying request to {model} for {wait_time:.1f}s (Attempt {attempts}/{max_wait_attempts})")
                    await asyncio.sleep(wait_time)
            
            if attempts >= max_wait_attempts:
                yield StreamChunk(delta="", error=f"Timeout waiting for Rate Limiter for {model}.")
                return

            # 3. Route to Provider
            try:
                async for chunk in provider.stream(messages, model, **kwargs):
                    yield chunk
            except Exception as e:
                message = str(e)
                if _is_expected_provider_error(message):
                    logger.warning("LLMGateway: Provider stream warning: %s", message)
                else:
                    logger.error("LLMGateway: Provider stream error: %s", message, exc_info=True)
                yield StreamChunk(delta="", error=_sanitize_provider_error(message))

    async def complete(
        self,
        provider: BaseProvider,
        messages: list[ChatMessage],
        model: str,
        agent_id: str,
        db: AsyncSession,
        **kwargs
    ) -> ChatMessage:
        from app.services.model_registry_service import ModelRegistryService
        # 1. Resolve limits
        caps = await ModelRegistryService.get_effective_capabilities(model, db)
        rpm = caps.get("rpm", 100)
        tpm = caps.get("tpm", 1000000)
        rpd = caps.get("rpd", 10000)
        canonical_id = caps.get("canonical_id", model)
        
        estimated_tokens = self._estimate_tokens(messages)

        agent_sem = self._get_agent_semaphore(agent_id)
        async with self.global_semaphore, agent_sem:
            max_wait_attempts: int = 90 # 3 minutes max wait (at 2s intervals)
            attempts: int = 0
            while attempts < max_wait_attempts:
                status = await self.rate_limiter.check_limits(canonical_id, rpm, tpm, rpd, estimated_tokens)
                if status == "allow":
                    break
                elif status == "block":
                    if self.registry:
                        registered = self.registry.registered_providers()
                        available = [p for p in registered if self.registry.get(p).is_available() and p != provider.name]
                        if available:
                            fallback_name = available[0]
                            fallback_provider = self.registry.get(fallback_name)
                            models = await fallback_provider.list_models()
                            if models:
                                logger.warning(f"RPD Blocked for {model}. Falling back (complete) to {fallback_name}/{models[0].id}")
                                return await fallback_provider.complete(messages, models[0].id, **kwargs)
                    raise Exception(f"Rate limit exceeded (RPD max reached for {model}). Task blocked.")
                elif status == "delay":
                    attempts += 1
                    wait_time = 2.0 + random.uniform(-0.5, 0.5)
                    logger.info(f"LLMGateway: Delaying complete request to {model} for {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
            
            if attempts >= max_wait_attempts:
                raise Exception(f"Timeout waiting for Rate Limiter for {model}.")

            try:
                return await provider.complete(messages, model, **kwargs)
            except Exception as e:
                message = str(e)
                if _is_expected_provider_error(message):
                    logger.warning("LLMGateway: Provider complete warning: %s", message)
                else:
                    logger.error("LLMGateway: Provider complete error: %s", message, exc_info=True)
                raise Exception(_sanitize_provider_error(message))

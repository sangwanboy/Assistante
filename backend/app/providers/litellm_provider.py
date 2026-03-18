import logging
import importlib
from typing import AsyncIterator

from app.providers.base import BaseProvider, ChatMessage, ModelInfo, StreamChunk, TokenUsage

logger = logging.getLogger(__name__)


class LiteLLMProvider(BaseProvider):
    """Provider adapter backed by LiteLLM.

    This adapter keeps the existing provider interface while delegating model
    execution and token usage accounting to LiteLLM.
    """

    def __init__(self, provider_name: str, api_key: str | None = None):
        self._provider_name = provider_name
        self._api_key = api_key

    @property
    def name(self) -> str:
        return self._provider_name

    def is_available(self) -> bool:
        # For local providers such as ollama we may not require an API key.
        if self._provider_name in {"ollama"}:
            return True
        return bool(self._api_key)

    def _model_for_litellm(self, model: str) -> str:
        if "/" in model:
            return model
        return f"{self._provider_name}/{model}"

    @staticmethod
    def _acompletion():
        litellm_module = importlib.import_module("litellm")
        return litellm_module.acompletion

    def _sanitize_tool_sequence(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        """Ensure tool messages strictly follow assistant tool_calls with matching ids."""
        sanitized: list[ChatMessage] = []
        pending_ids: set[str] = set()

        for msg in messages:
            if msg.role == "assistant":
                pending_ids = set()
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tc_id = ""
                        if isinstance(tc, dict):
                            tc_id = str(tc.get("id") or "").strip()
                        else:
                            tc_id = str(getattr(tc, "id", "") or "").strip()
                        if tc_id:
                            pending_ids.add(tc_id)
                sanitized.append(msg)
                continue

            if msg.role == "tool":
                tc_id = str(msg.tool_call_id or "").strip()
                if tc_id and tc_id in pending_ids:
                    pending_ids.discard(tc_id)
                    sanitized.append(msg)
                else:
                    logger.warning(
                        "LiteLLMProvider dropping orphan tool message (tool_call_id=%s)",
                        tc_id or "<missing>",
                    )
                continue

            if pending_ids:
                pending_ids = set()
            sanitized.append(msg)

        return sanitized

    def _format_messages(self, messages: list[ChatMessage]) -> list[dict]:
        formatted: list[dict] = []
        for msg in self._sanitize_tool_sequence(messages):
            m = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            formatted.append(m)
        return formatted

    def _format_tools(self, tools: list[dict] | None) -> list[dict] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in tools
        ]

    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> ChatMessage:
        litellm_model = self._model_for_litellm(model)
        resp = await self._acompletion()(
            model=litellm_model,
            messages=self._format_messages(messages),
            tools=self._format_tools(tools),
            temperature=temperature,
            api_key=self._api_key,
            **kwargs,
        )

        choice = resp.choices[0]
        tool_calls = None
        if getattr(choice.message, "tool_calls", None):
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]

        usage = None
        if getattr(resp, "usage", None):
            usage = TokenUsage(
                prompt_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(resp.usage, "total_tokens", 0) or 0,
            )

        return ChatMessage(
            role="assistant",
            content=choice.message.content or "",
            tool_calls=tool_calls,
            usage=usage,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        litellm_model = self._model_for_litellm(model)
        stream = await self._acompletion()(
            model=litellm_model,
            messages=self._format_messages(messages),
            tools=self._format_tools(tools),
            temperature=temperature,
            api_key=self._api_key,
            stream=True,
            stream_options={"include_usage": True},
            **kwargs,
        )

        accumulated_tool_calls: dict[int, dict] = {}

        async for chunk in stream:
            choice = chunk.choices[0] if getattr(chunk, "choices", None) else None
            if not choice:
                continue

            delta = choice.delta
            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": tc.id or "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.id:
                        accumulated_tool_calls[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            accumulated_tool_calls[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            accumulated_tool_calls[idx]["function"]["arguments"] += tc.function.arguments

            text = getattr(delta, "content", "") or ""
            finish = choice.finish_reason

            tool_calls_list = None
            if finish and accumulated_tool_calls:
                tool_calls_list = list(accumulated_tool_calls.values())

            usage = None
            if getattr(chunk, "usage", None):
                usage = TokenUsage(
                    prompt_tokens=getattr(chunk.usage, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(chunk.usage, "completion_tokens", 0) or 0,
                    total_tokens=getattr(chunk.usage, "total_tokens", 0) or 0,
                )

            yield StreamChunk(delta=text, finish_reason=finish, tool_calls=tool_calls_list, usage=usage)

    async def list_models(self) -> list[ModelInfo]:
        # Curated list validated against live Gemini API availability.
        if self._provider_name == "gemini":
            return [
                ModelInfo(id="gemini-2.5-flash", name="Gemini 2.5 Flash", provider="gemini", context_window=1048576),
                ModelInfo(id="gemini-2.5-flash-lite", name="Gemini 2.5 Flash Lite", provider="gemini", context_window=1048576),
                ModelInfo(id="gemini-2.5-pro", name="Gemini 2.5 Pro", provider="gemini", context_window=1048576),
                ModelInfo(id="gemini-3-flash-preview", name="Gemini 3 Flash Preview", provider="gemini", context_window=1048576),
                ModelInfo(id="gemini-3-pro-preview", name="Gemini 3 Pro Preview", provider="gemini", context_window=1048576),
                ModelInfo(id="gemini-3.1-pro-preview", name="Gemini 3.1 Pro Preview", provider="gemini", context_window=1048576),
                ModelInfo(id="gemini-3.1-flash-lite-preview", name="Gemini 3.1 Flash Lite Preview", provider="gemini", context_window=1048576),
            ]
        if self._provider_name == "openai":
            return [
                ModelInfo(id="gpt-4o", name="GPT-4o", provider="openai", context_window=128000),
                ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", provider="openai", context_window=128000),
            ]
        if self._provider_name == "anthropic":
            return [
                ModelInfo(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet", provider="anthropic", context_window=200000),
            ]
        return []

from typing import AsyncIterator

from openai import AsyncOpenAI

from app.providers.base import BaseProvider, ChatMessage, StreamChunk, ModelInfo


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _format_messages(self, messages: list[ChatMessage]) -> list[dict]:
        formatted = []
        for msg in messages:
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
    ) -> ChatMessage:
        kwargs = {
            "model": model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
        }
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            kwargs["tools"] = formatted_tools

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        tool_calls = None
        if choice.message.tool_calls:
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

        return ChatMessage(
            role="assistant",
            content=choice.message.content or "",
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        kwargs = {
            "model": model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
            "stream": True,
        }
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            kwargs["tools"] = formatted_tools

        response = await self.client.chat.completions.create(**kwargs)

        accumulated_tool_calls = {}

        async for chunk in response:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            delta = choice.delta

            # Handle tool call chunks
            if delta.tool_calls:
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

            # Yield text delta
            text = delta.content or ""
            finish = choice.finish_reason

            tool_calls_list = None
            if finish == "tool_calls" and accumulated_tool_calls:
                tool_calls_list = list(accumulated_tool_calls.values())

            yield StreamChunk(
                delta=text,
                finish_reason=finish,
                tool_calls=tool_calls_list,
            )

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="gpt-4o", name="GPT-4o", provider="openai", context_window=128000),
            ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", provider="openai", context_window=128000),
            ModelInfo(id="gpt-4-turbo", name="GPT-4 Turbo", provider="openai", context_window=128000),
            ModelInfo(id="gpt-3.5-turbo", name="GPT-3.5 Turbo", provider="openai", context_window=16385),
        ]

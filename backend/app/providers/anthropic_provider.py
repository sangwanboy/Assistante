import json
from typing import AsyncIterator

from anthropic import AsyncAnthropic

from app.providers.base import BaseProvider, ChatMessage, StreamChunk, ModelInfo


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _format_messages(self, messages: list[ChatMessage]) -> tuple[str | None, list[dict]]:
        """Returns (system_prompt, messages) in Anthropic format."""
        system = None
        formatted = []

        for msg in messages:
            if msg.role == "system":
                system = msg.content
                continue

            if msg.role == "tool":
                formatted.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content,
                        }
                    ],
                })
                continue

            if msg.role == "assistant" and msg.tool_calls:
                content = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        args = json.loads(args)
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": args,
                    })
                formatted.append({"role": "assistant", "content": content})
                continue

            formatted.append({"role": msg.role, "content": msg.content})

        return system, formatted

    def _format_tools(self, tools: list[dict] | None) -> list[dict] | None:
        if not tools:
            return None
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
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
        system, formatted = self._format_messages(messages)

        kwargs = {
            "model": model,
            "messages": formatted,
            "max_tokens": 4096,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            kwargs["tools"] = formatted_tools

        response = await self.client.messages.create(**kwargs)

        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })

        return ChatMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls if tool_calls else None,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        system, formatted = self._format_messages(messages)

        kwargs = {
            "model": model,
            "messages": formatted,
            "max_tokens": 4096,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            kwargs["tools"] = formatted_tools

        current_tool_call = None

        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    if hasattr(event.content_block, "type") and event.content_block.type == "tool_use":
                        current_tool_call = {
                            "id": event.content_block.id,
                            "type": "function",
                            "function": {
                                "name": event.content_block.name,
                                "arguments": "",
                            },
                        }
                    continue

                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield StreamChunk(delta=event.delta.text)
                    elif hasattr(event.delta, "partial_json"):
                        if current_tool_call:
                            current_tool_call["function"]["arguments"] += event.delta.partial_json
                    continue

                if event.type == "content_block_stop":
                    if current_tool_call:
                        yield StreamChunk(
                            finish_reason="tool_calls",
                            tool_calls=[current_tool_call],
                        )
                        current_tool_call = None
                    continue

                if event.type == "message_delta":
                    if hasattr(event, "delta") and hasattr(event.delta, "stop_reason"):
                        if event.delta.stop_reason == "end_turn":
                            yield StreamChunk(finish_reason="stop")
                    continue

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="claude-sonnet-4-20250514", name="Claude Sonnet 4", provider="anthropic", context_window=200000),
            ModelInfo(id="claude-haiku-4-20250414", name="Claude Haiku 4", provider="anthropic", context_window=200000),
            ModelInfo(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet", provider="anthropic", context_window=200000),
        ]

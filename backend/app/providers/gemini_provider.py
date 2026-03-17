import json
import uuid
from typing import AsyncIterator

from google import genai
from google.genai import types
import logging
import base64

from app.providers.base import BaseProvider, ChatMessage, StreamChunk, ModelInfo, TokenUsage

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key
        self.client = genai.Client(api_key=api_key)
        logger.info(f"GeminiProvider loaded from: {__file__}")

    @property
    def name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _format_tools(self, tools: list[dict] | None) -> list[types.Tool] | None:
        if not tools:
            return None

        declarations = []
        for t in tools:
            # Build a clean schema without unsupported keys
            params = t.get("parameters", {})
            schema = types.Schema(
                type=params.get("type", "OBJECT"),
                properties={
                    k: types.Schema(
                        type=v.get("type", "STRING"),
                        description=v.get("description", ""),
                        items=types.Schema(type=v.get("items", {}).get("type", "STRING")) if v.get("type") == "array" else None,
                    )
                    for k, v in params.get("properties", {}).items()
                },
                required=params.get("required", []),
            )
            declarations.append(types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=schema,
            ))

        return [types.Tool(function_declarations=declarations)]

    def _build_contents(self, messages: list[ChatMessage]) -> tuple[list[types.Content], str | None]:
        """Convert ChatMessage list to Gemini contents format.
        Returns (contents, system_instruction)."""
        contents: list[types.Content] = []
        system_instruction = None

        # Build a lookup: tool_call_id -> function name (from assistant messages)
        tool_call_id_to_name: dict[str, str] = {}
        for msg in messages:
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_id = tc.get("id", "")
                    tc_name = tc.get("function", {}).get("name", "")
                    if tc_id and tc_name:
                        tool_call_id_to_name[tc_id] = tc_name

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
                continue

            if msg.role == "user":
                parts = [types.Part.from_text(text=msg.content)]
                if msg.images:
                    for b64 in msg.images:
                        parts.append(types.Part.from_bytes(
                            data=base64.b64decode(b64),
                            mime_type="image/jpeg",
                        ))
                contents.append(types.Content(role="user", parts=parts))
            elif msg.role == "assistant":
                parts = []
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        func = tc.get("function", {})
                        args_str = func.get("arguments", "{}")
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        kwargs = {"name": func.get("name", ""), "args": args}
                        func_call = types.FunctionCall(**kwargs)
                        part_kwargs = {"function_call": func_call}
                        if tc.get("thought"):
                            part_kwargs["thought"] = tc["thought"]
                        if tc.get("thought_signature"):
                            part_kwargs["thought_signature"] = bytes.fromhex(tc["thought_signature"])
                        parts.append(types.Part(**part_kwargs))
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            elif msg.role == "tool":
                # Use the actual function name so Gemini can match the result to its call
                func_name = tool_call_id_to_name.get(msg.tool_call_id or "", "tool_response")
                tool_part = types.Part.from_function_response(
                    name=func_name,
                    response={"result": msg.content},
                )
                
                # Gemini requirement: tool response MUST follow model turn.
                # If the last content was 'user' (which we use for tool responses), append to its parts.
                # Otherwise start a new 'user' content. 
                # Note: The 'model' turn containing the call should be immediately before.
                if contents and contents[-1].role == "user":
                    contents[-1].parts.append(tool_part)
                else:
                    contents.append(types.Content(role="user", parts=[tool_part]))
                
                if msg.images:
                    target = contents[-1]
                    for b64 in msg.images:
                        target.parts.append(types.Part.from_bytes(
                            data=base64.b64decode(b64),
                            mime_type="image/jpeg",
                        ))

        logger.info(f"Gemini contents built: {[f'{c.role}:{len(c.parts)}' for c in contents]}")
        return contents, system_instruction
    def _map_model_id(self, model_id: str) -> str:
        # Map user-friendly "2.5+" IDs to stable 3.1 endpoints to avoid 404s on decommissioned 2.x/1.x
        mapping = {
            "gemini-2.5-flash": "gemini-3.1-flash-preview",
            "gemini-2.5-flash-lite": "gemini-3.1-flash-lite-preview",
            "gemini-2.5-pro": "gemini-3.1-pro-preview",
            "gemini-3-flash-preview": "gemini-3.1-flash-preview",
            "gemini-3-pro-preview": "gemini-3.1-pro-preview",
            "gemini-3.1-flash-preview": "gemini-3.1-flash-preview",
            "gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
            "gemini-3.1-flash-lite": "gemini-3.1-flash-lite-preview",
        }
        mapped = mapping.get(model_id, "gemini-3.1-flash-lite-preview")
        logger.info(f"Mapping Gemini model '{model_id}' -> '{mapped}'")
        return mapped

    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> ChatMessage:
        contents, system_instruction = self._build_contents(messages)
        gemini_tools = self._format_tools(tools)
        mapped_model = self._map_model_id(model)

        if not contents:
            raise ValueError(f"No user/assistant messages to send to Gemini (got {len(messages)} messages total)")

        config_kwargs = {
            "temperature": temperature,
            "tools": gemini_tools,
        }
        
        # Handle structured output
        if "response_format" in kwargs:
            fmt = kwargs["response_format"]
            if isinstance(fmt, dict) and fmt.get("type") == "json_object":
                config_kwargs["response_mime_type"] = "application/json"
                if "response_schema" in kwargs:
                    config_kwargs["response_schema"] = kwargs["response_schema"]
            elif hasattr(fmt, "type") and getattr(fmt, "type") == "json_object":
                config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**config_kwargs)
        if system_instruction:
            config.system_instruction = system_instruction

        response = self.client.models.generate_content(
            model=mapped_model,
            contents=contents,
            config=config,
        )

        # Parse response
        text = ""
        tool_calls = None

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.text:
                    text += part.text
                if part.function_call:
                    if tool_calls is None:
                        tool_calls = []
                    tc = {
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": part.function_call.name,
                            "arguments": json.dumps(dict(part.function_call.args) if part.function_call.args else {}),
                        },
                    }
                    if hasattr(part, "thought") and part.thought:
                        tc["thought"] = part.thought
                    if hasattr(part, "thought_signature") and getattr(part, "thought_signature", None):
                        tc["thought_signature"] = part.thought_signature.hex() if isinstance(part.thought_signature, bytes) else str(part.thought_signature)
                    tool_calls.append(tc)

        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            md = response.usage_metadata
            usage = TokenUsage(
                prompt_tokens=md.prompt_token_count or 0,
                completion_tokens=md.candidates_token_count or 0,
                total_tokens=md.total_token_count or 0
            )

        return ChatMessage(role="assistant", content=text, tool_calls=tool_calls, usage=usage)

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        contents, system_instruction = self._build_contents(messages)
        gemini_tools = self._format_tools(tools)
        mapped_model = self._map_model_id(model)

        if not contents:
            raise ValueError(f"No user/assistant messages to send to Gemini (got {len(messages)} messages total)")

        config_kwargs = {
            "temperature": temperature,
            "tools": gemini_tools,
        }
        
        # Handle structured output (note: Gemini stream also supports this)
        if "response_format" in kwargs:
            fmt = kwargs["response_format"]
            if isinstance(fmt, dict) and fmt.get("type") == "json_object":
                config_kwargs["response_mime_type"] = "application/json"
                if "response_schema" in kwargs:
                    config_kwargs["response_schema"] = kwargs["response_schema"]

        config = types.GenerateContentConfig(**config_kwargs)
        if system_instruction:
            config.system_instruction = system_instruction

        response = self.client.models.generate_content_stream(
            model=mapped_model,
            contents=contents,
            config=config,
        )

        accumulated_tool_calls = []

        for chunk in response:
            if not chunk.candidates:
                continue

            candidate = chunk.candidates[0]
            if not candidate.content or not candidate.content.parts:
                continue

            text = ""
            for part in candidate.content.parts:
                if part.text:
                    text += part.text
                if part.function_call:
                    tc = {
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": part.function_call.name,
                            "arguments": json.dumps(dict(part.function_call.args) if part.function_call.args else {}),
                        },
                    }
                    if hasattr(part, "thought") and part.thought:
                        tc["thought"] = part.thought
                    if hasattr(part, "thought_signature") and getattr(part, "thought_signature", None):
                        tc["thought_signature"] = part.thought_signature.hex() if isinstance(part.thought_signature, bytes) else str(part.thought_signature)
                    accumulated_tool_calls.append(tc)

            finish = None
            if candidate.finish_reason:
                finish = str(candidate.finish_reason)

            tool_calls_out = None
            if finish and accumulated_tool_calls:
                tool_calls_out = accumulated_tool_calls
                
            usage = None
            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                md = chunk.usage_metadata
                usage = TokenUsage(
                    prompt_tokens=md.prompt_token_count or 0,
                    completion_tokens=md.candidates_token_count or 0,
                    total_tokens=md.total_token_count or 0
                )

            yield StreamChunk(
                delta=text,
                finish_reason=finish,
                tool_calls=tool_calls_out,
                usage=usage
            )

    async def list_models(self) -> list[ModelInfo]:
        from app.config import settings
        cw = settings.gemini_context_window
        tpm = settings.gemini_tpm
        rpm = settings.gemini_rpm
        rpd = settings.gemini_rpd
        return [
            ModelInfo(id="gemini-2.5-flash", name="Gemini 2.5 Flash", provider="gemini", context_window=cw, tpm=tpm, rpm=rpm, rpd=rpd),
            ModelInfo(id="gemini-2.5-flash-lite", name="Gemini 2.5 Flash Lite", provider="gemini", context_window=cw, tpm=tpm, rpm=rpm, rpd=rpd),
            ModelInfo(id="gemini-2.5-pro", name="Gemini 2.5 Pro", provider="gemini", context_window=cw, tpm=tpm, rpm=rpm, rpd=rpd),
            ModelInfo(id="gemini-3-flash-preview", name="Gemini 3 Flash Preview", provider="gemini", context_window=cw, tpm=tpm, rpm=rpm, rpd=rpd),
            ModelInfo(id="gemini-3-pro-preview", name="Gemini 3 Pro Preview", provider="gemini", context_window=cw, tpm=tpm, rpm=rpm, rpd=rpd),
            ModelInfo(id="gemini-3.1-flash-lite", name="Gemini 3.1 Flash Lite", provider="gemini", context_window=cw, tpm=tpm, rpm=rpm, rpd=rpd),
            ModelInfo(id="gemini-3.1-flash-preview", name="Gemini 3.1 Flash Preview", provider="gemini", context_window=cw, tpm=tpm, rpm=rpm, rpd=rpd),
            ModelInfo(id="gemini-3.1-pro-preview", name="Gemini 3.1 Pro Preview", provider="gemini", context_window=cw, tpm=tpm, rpm=rpm, rpd=rpd),
        ]

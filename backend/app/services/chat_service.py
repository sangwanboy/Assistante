import json
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent
from app.providers.base import ChatMessage, StreamChunk
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry
from app.services.conversation_service import ConversationService


class ChatService:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        tool_registry: ToolRegistry,
        session: AsyncSession,
    ):
        self.providers = provider_registry
        self.tools = tool_registry
        self.conv_service = ConversationService(session)
        self.session = session

    def _parse_model_string(self, model_string: str) -> tuple[str, str]:
        """Parse 'provider/model' into (provider_name, model_id)."""
        if "/" in model_string:
            provider, model = model_string.split("/", 1)
            return provider, model
        return "openai", model_string

    def _build_agent_prompt(self, agent: Agent) -> str:
        """Build a composite system prompt from agent personality fields."""
        parts = []
        if agent.system_prompt:
            parts.append(agent.system_prompt)
        # Soul
        soul = []
        if agent.personality_tone:
            soul.append(f"Your tone is {agent.personality_tone}.")
        if agent.personality_traits:
            try:
                traits = json.loads(agent.personality_traits)
                if traits:
                    soul.append(f"Your personality traits are: {', '.join(traits)}.")
            except (json.JSONDecodeError, TypeError):
                pass
        if agent.communication_style:
            soul.append(f"Communicate in a {agent.communication_style} style.")
        if soul:
            parts.append("## Personality\n" + " ".join(soul))
        # Mind
        if agent.reasoning_style:
            parts.append(f"## Reasoning\nApproach problems with a {agent.reasoning_style} reasoning style.")
        # Memory
        if agent.memory_context:
            parts.append(f"## Memory\n{agent.memory_context}")
        if agent.memory_instructions:
            parts.append(f"## Standing Instructions\n{agent.memory_instructions}")

        # Smart default: if no personality is configured at all, set a helpful baseline
        if not parts:
            desc = agent.description or "a capable AI assistant"
            parts.append(
                f"You are {agent.name}, {desc}. "
                f"Be helpful, clear, and professional. "
                f"Use tools when they would improve your response."
            )

        return "\n\n".join(parts)

    def _filter_tools_for_agent(self, agent: Agent) -> list[dict] | None:
        """Return only the tools enabled for this agent."""
        if not self.tools:
            return None
        all_tools = self.tools.as_provider_format()
        if not agent.enabled_tools:
            return all_tools
        try:
            enabled = json.loads(agent.enabled_tools)
            if not enabled:
                return all_tools
            return [t for t in all_tools if t["name"] in enabled]
        except (json.JSONDecodeError, TypeError):
            return all_tools

    def _db_messages_to_chat(self, db_messages, system_prompt: str | None = None) -> list[ChatMessage]:
        messages = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))

        for msg in db_messages:
            tool_calls = None
            if msg.tool_calls_json:
                try:
                    tool_calls = json.loads(msg.tool_calls_json)
                except json.JSONDecodeError:
                    pass

            messages.append(ChatMessage(
                role=msg.role,
                content=msg.content,
                tool_calls=tool_calls,
                tool_call_id=msg.tool_call_id,
            ))

        return messages

    async def _execute_tool_calls(self, tool_calls: list[dict]) -> list[ChatMessage]:
        """Execute tool calls and return tool result messages."""
        results = []
        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            args_str = func.get("arguments", "{}")

            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}

            try:
                tool = self.tools.get(tool_name)
                result = await tool.execute(**args)
            except Exception as e:
                result = f"Tool error: {str(e)}"

            results.append(ChatMessage(
                role="tool",
                content=result,
                tool_call_id=tc.get("id", ""),
            ))

        return results

    async def chat(
        self,
        conversation_id: str,
        user_message: str,
        model_string: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Non-streaming chat. Returns the assistant response text."""
        provider_name, model_id = self._parse_model_string(model_string)
        provider = self.providers.get(provider_name)

        # Ensure conversation exists
        conv = await self.conv_service.get(conversation_id)
        if not conv:
            conv = await self.conv_service.create(model=model_string)
            conversation_id = conv.id

        # Save user message
        await self.conv_service.add_message(conversation_id, "user", user_message)

        # Build message history
        db_messages = await self.conv_service.get_messages(conversation_id)
        prompt = system_prompt or conv.system_prompt
        messages = self._db_messages_to_chat(db_messages, prompt)

        # Get tool schemas
        tool_schemas = self.tools.as_provider_format() if self.tools else None

        # Agentic loop
        max_iterations = 10
        for _ in range(max_iterations):
            result = await provider.complete(messages, model_id, tools=tool_schemas, temperature=temperature)

            if result.tool_calls:
                # Save assistant message with tool calls
                await self.conv_service.add_message(
                    conversation_id, "assistant", result.content,
                    tool_calls_json=json.dumps(result.tool_calls),
                )
                messages.append(result)

                # Execute tools
                tool_results = await self._execute_tool_calls(result.tool_calls)
                for tr in tool_results:
                    await self.conv_service.add_message(
                        conversation_id, "tool", tr.content,
                        tool_call_id=tr.tool_call_id,
                    )
                    messages.append(tr)
            else:
                # Final response
                await self.conv_service.add_message(conversation_id, "assistant", result.content)
                return result.content

        return "Max tool iterations reached."

    async def stream_chat(
        self,
        conversation_id: str,
        user_message: str,
        model_string: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[dict]:
        """Streaming chat. Yields event dicts for the WebSocket."""
        provider_name, model_id = self._parse_model_string(model_string)
        provider = self.providers.get(provider_name)

        # Ensure conversation exists
        conv = await self.conv_service.get(conversation_id)
        if not conv:
            conv = await self.conv_service.create(model=model_string)
            conversation_id = conv.id

        # Save user message
        await self.conv_service.add_message(conversation_id, "user", user_message)

        # Build message history
        db_messages = await self.conv_service.get_messages(conversation_id)
        prompt = system_prompt or conv.system_prompt
        messages = self._db_messages_to_chat(db_messages, prompt)

        # Get tool schemas
        tool_schemas = self.tools.as_provider_format() if self.tools else None

        # Agentic loop with streaming
        max_iterations = 10
        for _ in range(max_iterations):
            full_response = ""
            final_tool_calls = None

            yield {"type": "agent_turn_start", "agent_name": "Assistant"}

            async for chunk in provider.stream(messages, model_id, tools=tool_schemas, temperature=temperature):
                if chunk.delta:
                    full_response += chunk.delta
                    yield {"type": "chunk", "delta": chunk.delta}

                if chunk.tool_calls:
                    final_tool_calls = chunk.tool_calls

            if final_tool_calls:
                # Save assistant message with tool calls
                await self.conv_service.add_message(
                    conversation_id, "assistant", full_response,
                    tool_calls_json=json.dumps(final_tool_calls),
                )
                messages.append(ChatMessage(
                    role="assistant", content=full_response, tool_calls=final_tool_calls,
                ))

                # Execute tools and stream results
                for tc in final_tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")

                    yield {
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "tool_args": json.loads(func.get("arguments", "{}")),
                    }

                tool_results = await self._execute_tool_calls(final_tool_calls)
                for tr in tool_results:
                    await self.conv_service.add_message(
                        conversation_id, "tool", tr.content,
                        tool_call_id=tr.tool_call_id,
                    )
                    messages.append(tr)
                    yield {
                        "type": "tool_result",
                        "tool_name": "",
                        "tool_result": tr.content,
                    }
            else:
                # Final response
                msg = await self.conv_service.add_message(conversation_id, "assistant", full_response)
                yield {
                    "type": "agent_turn_end",
                    "agent_name": "Assistant",
                    "message_id": msg.id,
                }
                yield {
                    "type": "done",
                    "message_id": msg.id,
                    "conversation_id": conversation_id,
                }
                return

        yield {"type": "done", "conversation_id": conversation_id}

    async def stream_group_chat(
        self,
        conversation_id: str,
        user_message: str,
        temperature: float = 0.7,
        max_turns: int = 10,  # Keeping param for API compat, but unused
    ) -> AsyncIterator[dict]:
        """Streaming group chat orchestrating active agents."""
        # Ensure conversation exists and is marked as group
        conv = await self.conv_service.get(conversation_id)
        if not conv:
            conv = await self.conv_service.create(title="Group Chat", is_group=True)
            conversation_id = conv.id

        # Save user message
        await self.conv_service.add_message(conversation_id, "user", user_message)

        # Get all active agents
        result = await self.session.execute(select(Agent).where(Agent.is_active == True).order_by(Agent.id))
        active_agents = list(result.scalars().all())

        if not active_agents:
            yield {
                "type": "error",
                "content": "No active agents found for group chat.",
                "conversation_id": conversation_id
            }
            return

        # Each agent gets exactly ONE top-level turn to reply to the user's message
        for agent in active_agents:
            provider_name, model_id = self._parse_model_string(agent.model)
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            # Fetch fresh history (includes whatever previous agents just said!)
            db_messages = await self.conv_service.get_messages(conversation_id)
            
            agent_msgs = []
            
            # 1. System Prompt (Personality + Strict anti-hallucination instruction)
            agent_prompt = self._build_agent_prompt(agent)
            multi_agent_instruction = (
                f"\n\nIMPORTANT: You are in a multi-agent chat room. Your name is {agent.name}. "
                "Respond ONLY as yourself. Do NOT simulate conversations. "
                "Do NOT prefix your response with your name like 'Name: '. Just output your response directly."
            )
            final_prompt = (agent_prompt or "") + multi_agent_instruction
            agent_msgs.append(ChatMessage(role="system", content=final_prompt))
                
            # 2. Reconstruct history specifically for this agent's viewpoint
            for msg in db_messages:
                tool_calls = None
                if msg.tool_calls_json:
                    try:
                        tool_calls = json.loads(msg.tool_calls_json)
                    except json.JSONDecodeError:
                        pass
                
                if msg.role == "assistant":
                    if msg.agent_name == agent.name:
                        # This agent's own past message
                        agent_msgs.append(ChatMessage(
                            role="assistant", content=msg.content,
                            tool_calls=tool_calls, tool_call_id=msg.tool_call_id
                        ))
                    else:
                        # Another agent's message -> treat as user input so it doesn't try to continue the text
                        sender = msg.agent_name or "Another Agent"
                        agent_msgs.append(ChatMessage(
                            role="user", content=f"[{sender}]: {msg.content}"
                        ))
                else:
                    agent_msgs.append(ChatMessage(
                        role=msg.role, content=msg.content,
                        tool_calls=tool_calls, tool_call_id=msg.tool_call_id
                    ))

            # Filter tools for this agent
            agent_tools = self._filter_tools_for_agent(agent)

            yield {
                "type": "agent_turn_start",
                "agent_name": agent.name,
                "model": agent.model
            }

            msg_record = None
            
            # Agentic tool loop (allow the agent to use tools and observe results during its turn)
            for _ in range(5):  # Max 5 tool iterations per agent turn
                full_response = ""
                final_tool_calls = None

                async for chunk in provider.stream(agent_msgs, model_id, tools=agent_tools, temperature=temperature):
                    if chunk.delta:
                        full_response += chunk.delta
                        yield {
                            "type": "chunk", 
                            "delta": chunk.delta,
                            "agent_name": agent.name
                        }
                    
                    if chunk.tool_calls:
                        final_tool_calls = chunk.tool_calls

                if final_tool_calls:
                    msg_record = await self.conv_service.add_message(
                        conversation_id, "assistant", full_response,
                        agent_name=agent.name,
                        tool_calls_json=json.dumps(final_tool_calls),
                    )
                    agent_msgs.append(ChatMessage(
                        role="assistant", content=full_response, tool_calls=final_tool_calls
                    ))
                    
                    # Execute tools and stream results
                    for tc in final_tool_calls:
                        yield {
                            "type": "tool_call",
                            "tool_name": tc.get("function", {}).get("name"),
                            "tool_args": tc.get("function", {}).get("arguments", {}),
                        }
                    
                    tool_results = await self._execute_tool_calls(final_tool_calls)
                    for tr in tool_results:
                        await self.conv_service.add_message(
                            conversation_id, "tool", tr.content, tool_call_id=tr.tool_call_id
                        )
                        agent_msgs.append(tr)
                        yield {
                            "type": "tool_result",
                            "tool_name": tr.tool_name,
                            "tool_result": tr.content,
                        }
                    # Loop continues, agent observes tool output and replies again
                else:
                    msg_record = await self.conv_service.add_message(
                        conversation_id, "assistant", full_response, agent_name=agent.name
                    )
                    break # Finished turn
            
            yield {
                "type": "agent_turn_end",
                "agent_name": agent.name,
                "message_id": msg_record.id if msg_record else None
            }

        yield {"type": "done", "conversation_id": conversation_id}

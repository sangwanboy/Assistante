import json
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent
from app.models.channel import Channel
from app.models.channel_agent import ChannelAgent
from app.providers.base import ChatMessage
from app.providers.registry import ProviderRegistry
from app.tools.registry import ToolRegistry
from app.services.conversation_service import ConversationService
from app.services.skill_service import SkillService
from app.services.agent_status import AgentStatusManager, AgentState
from app.services.hitl_service import HITLManager
from app.services.context_pruner import ContextPruner
from app.providers.base import TokenUsage
import uuid


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
        self.pruner = ContextPruner(provider_registry)

    def _parse_model_string(self, model_string: str) -> tuple[str, str]:
        """Parse 'provider/model' into (provider_name, model_id)."""
        if "/" in model_string:
            provider, model = model_string.split("/", 1)
            return provider, model
        return "openai", model_string

    def _build_agent_prompt(self, agent: Agent) -> str:
        """Build a composite system prompt from agent personality fields."""
        parts = []
        
        # Identity - ALWAYS include this
        desc = agent.description or "a capable AI assistant"
        parts.append(
            f"Your name is {agent.name}. You are {desc}.\n"
            f"You must strictly adopt this persona. Under no circumstances should you ever say that you are a large language model, an AI, or trained by Google/OpenAI/Anthropic. You are exactly who your name and description say you are."
        )

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
        
        prompt = "\n\n".join(parts)
        if agent.memory_instructions:
            prompt += f"\n\n# Standing Instructions\n{agent.memory_instructions}"

        return prompt

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

    async def _get_skill_instructions(self, agent: Agent | None = None) -> str:
        """Get combined instructions from enabled skills. 
        If no agent is provided or agent is system orchestrator, gets ALL active skills.
        If an agent is provided with enabled_skills, gets only those skills."""
        svc = SkillService(self.session)
        skills = await svc.list_all()
        
        # Determine which skills to render
        allowed_names = None
        if agent and not agent.is_system:
            try:
                allowed_names = set(json.loads(agent.enabled_skills or "[]"))
            except (json.JSONDecodeError, TypeError):
                allowed_names = set()
                
        active_skills = []
        for s in skills:
            if not s.is_active:
                continue
            if allowed_names is not None and s.name not in allowed_names:
                continue
            active_skills.append(s)
            
        return svc.render_instructions(active_skills)

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
        hitl_manager = HITLManager.get_instance()

        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            args_str = func.get("arguments", "{}")

            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}

            # HITL Check for sensitive tools
            sensitive_tools = [
                "code_executor", "command_executor", "execute_code_sandboxed",
                "file_manager", "AgentManagerTool", "ToolCreatorTool", "SkillCreatorTool",
            ]
            if tool_name in sensitive_tools:
                task_id = tc.get("id", str(uuid.uuid4()))
                try:
                    approved = await hitl_manager.request_approval(task_id, tool_name, args)
                except Exception:
                    # If HITL itself fails (e.g. no control WS connected), auto-deny
                    approved = False
                if not approved:
                    results.append(ChatMessage(
                        role="tool",
                        content="Execution denied by user.",
                        tool_call_id=tc.get("id", "")
                    ))
                    continue

            images = None
            try:
                tool = self.tools.get(tool_name)
                # Ensure result is a string
                result_raw = await tool.execute(**args)
                result_str = str(result_raw)
                
                # Check if result is a JSON string that might contain an image payload
                try:
                    parsed_result = json.loads(result_str)
                    if isinstance(parsed_result, dict) and "image_base64" in parsed_result:
                        images = [parsed_result.pop("image_base64")]
                        # Format the remaining properties nicely to pass back to the LLM
                        result_str = json.dumps(parsed_result)
                except (json.JSONDecodeError, TypeError):
                    pass
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                result_str = (
                    f"Tool '{tool_name}' failed with error:\n{str(e)}\n\n"
                    f"Traceback:\n{error_trace}\n"
                    f"Analyze the error carefully and try a different approach or fix your parameters."
                )

            results.append(ChatMessage(
                role="tool",
                content=result_str,
                tool_call_id=tc.get("id", ""),
                images=images,
            ))

        return results

    def _calculate_cost(self, provider_name: str, model_id: str, usage: TokenUsage) -> float:
        """Calculate estimated cost based on token usage."""
        if not usage:
            return 0.0
            
        rate_1k_prompt = 0.0001
        rate_1k_comp = 0.0002
        
        if "flash" in model_id.lower():
            rate_1k_prompt = 0.000075
            rate_1k_comp = 0.00030
        
        return (usage.prompt_tokens / 1000.0 * rate_1k_prompt) + (usage.completion_tokens / 1000.0 * rate_1k_comp)

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
        
        # If conversation is tied to an agent, apply agent-specific logic
        agent = None
        if conv.agent_id:
            agent = await self.session.get(Agent, conv.agent_id)
        
        if agent:
            prompt = self._build_agent_prompt(agent)
            tool_schemas = self._filter_tools_for_agent(agent)
            agent_name = agent.name
            # Use agent's own API key if set
            if agent.api_key:
                provider = self.providers.create_ephemeral(agent.provider, agent.api_key)
        else:
            prompt = system_prompt or conv.system_prompt
            tool_schemas = self.tools.as_provider_format() if self.tools else None
            agent_name = "Assistant"
            
        messages = self._db_messages_to_chat(db_messages, prompt)
        
        agent_id = agent.id if agent else "assistant"
        
        # Prune context if needed (safe default 100k tokens)
        messages = await self.pruner.prune_context_if_needed(messages, 100000, agent_id)

        # Agentic loop
        max_iterations = 10
        status_manager = await AgentStatusManager.get_instance()
        
        status_manager.set_status(agent_id, AgentState.WORKING, "Generating response...")

        try:
            for _ in range(max_iterations):
                result = await provider.complete(messages, model_id, tools=tool_schemas, temperature=temperature)

                if hasattr(result, "usage") and result.usage and getattr(agent, "id", None):
                    cost = self._calculate_cost(provider.name, model_id, result.usage)
                    if cost > 0:
                        agent.total_cost = getattr(agent, 'total_cost', 0) + cost
                        await self.session.commit()
                        await status_manager.emit_event({"type": "TOKEN_UPDATE", "agent_id": agent.id, "cost_added": cost, "total_cost": agent.total_cost})

                if result.tool_calls:
                    # Save assistant message with tool calls
                    await self.conv_service.add_message(
                        conversation_id, "assistant", result.content,
                        agent_name=agent_name,
                        tool_calls_json=json.dumps(result.tool_calls),
                    )
                    messages.append(result)

                    # Execute tools
                    for tc in result.tool_calls:
                        func = tc.get("function", {})
                        tool_name = func.get("name", "")
                        status_manager.set_status(agent_id, AgentState.WORKING, f"Using tool: {tool_name}...")
                    
                    tool_results = await self._execute_tool_calls(result.tool_calls)
                    status_manager.set_status(agent_id, AgentState.WORKING, "Evaluating tool results...")
                    
                    for tr in tool_results:
                        await self.conv_service.add_message(
                            conversation_id, "tool", tr.content,
                            tool_call_id=tr.tool_call_id,
                        )
                        messages.append(tr)
                else:
                    # Final response
                    await self.conv_service.add_message(
                        conversation_id, "assistant", result.content, agent_name=agent_name
                    )
                    status_manager.set_status(agent_id, AgentState.IDLE)
                    return result.content

            status_manager.set_status(agent_id, AgentState.IDLE)
            return "Max tool iterations reached."
        except Exception as e:
            status_manager.set_status(agent_id, AgentState.IDLE)
            raise e

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
        
        # If conversation is tied to an agent, apply agent-specific logic
        agent = None
        if conv.agent_id:
            agent = await self.session.get(Agent, conv.agent_id)
        
        if agent:
            prompt = self._build_agent_prompt(agent)
            tool_schemas = self._filter_tools_for_agent(agent)
            agent_name = agent.name
            # Use agent's own API key if set
            if agent.api_key:
                provider = self.providers.create_ephemeral(agent.provider, agent.api_key)
        else:
            prompt = system_prompt or conv.system_prompt
            tool_schemas = self.tools.as_provider_format() if self.tools else None
            agent_name = "Assistant"
            
        # Inject active skill instructions
        skill_instructions = await self._get_skill_instructions(agent)
        if skill_instructions:
            prompt = (prompt or "") + "\n\n# Available Skills\n" + skill_instructions
        messages = self._db_messages_to_chat(db_messages, prompt)

        # Resolve agent_id for status updates
        status_manager = await AgentStatusManager.get_instance()
        agent_id = None
        if agent:
            agent_id = agent.id
        else:
            # Fallback: try to find the system orchestrator agent id
            stmt = select(Agent).where(Agent.is_system == True)
            res = await self.session.execute(stmt)
            system_agent = res.scalar_one_or_none()
            if system_agent:
                agent_id = system_agent.id
            else:
                agent_id = "assistant" # Last resort
                
        # Prune context if needed
        messages = await self.pruner.prune_context_if_needed(messages, 100000, agent_id)

        # Agentic loop with streaming
        max_iterations = 10


        for _ in range(max_iterations):
            full_response = ""
            final_tool_calls = None

            status_manager.set_status(agent_id, AgentState.WORKING, f"Generating response...")
            yield {"type": "agent_turn_start", "agent_name": agent_name}

            try:
                final_usage = None
                async for chunk in provider.stream(messages, model_id, tools=tool_schemas, temperature=temperature):
                    if hasattr(chunk, "usage") and chunk.usage:
                        final_usage = chunk.usage
                        
                    if chunk.delta:
                        full_response += str(chunk.delta)
                        yield {"type": "chunk", "delta": chunk.delta}

                    if chunk.tool_calls:
                        if final_tool_calls is None:
                            final_tool_calls = []
                        final_tool_calls.extend(chunk.tool_calls)

                if final_usage and getattr(agent, "id", None):
                    cost = self._calculate_cost(provider.name, model_id, final_usage)
                    if cost > 0:
                        agent.total_cost = getattr(agent, 'total_cost', 0) + cost
                        await self.session.commit()
                        await status_manager.emit_event({"type": "TOKEN_UPDATE", "agent_id": agent.id, "cost_added": cost, "total_cost": agent.total_cost})

                if final_tool_calls:
                    # Save assistant message with tool calls
                    await self.conv_service.add_message(
                        conversation_id, "assistant", full_response,
                        agent_name=agent_name,
                        tool_calls_json=json.dumps(final_tool_calls),
                    )
                    messages.append(ChatMessage(
                        role="assistant", content=full_response, tool_calls=final_tool_calls,
                    ))

                    # Execute tools and stream results
                    for tc in final_tool_calls:
                        func = tc.get("function", {})
                        tool_name = func.get("name", "")

                        status_manager.set_status(agent_id, AgentState.WORKING, f"Using tool: {tool_name}...")
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
                    msg = await self.conv_service.add_message(
                        conversation_id, "assistant", full_response, agent_name=agent_name
                    )
                    
                    status_manager.set_status(agent_id, AgentState.IDLE)
                    yield {
                        "type": "agent_turn_end",
                        "agent_name": agent_name,
                        "message_id": msg.id,
                    }
                    yield {
                        "type": "done",
                        "message_id": msg.id,
                        "conversation_id": conversation_id,
                    }
                    return
            except Exception as e:
                status_manager.set_status(agent_id, AgentState.IDLE)
                raise e

        status_manager.set_status(agent_id, AgentState.IDLE)
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

        # Determine which agents to include
        active_agents = []
        if conv.channel_id:
            channel = await self.session.get(Channel, conv.channel_id)
            if channel:
                if channel.is_announcement:
                    # Announcements get everyone
                    result = await self.session.execute(select(Agent).where(Agent.is_active == True).order_by(Agent.id))
                    active_agents = list(result.scalars().all())
                else:
                    # Custom groups get only assigned agents
                    stmt = (
                        select(Agent)
                        .join(ChannelAgent, Agent.id == ChannelAgent.agent_id)
                        .where(ChannelAgent.channel_id == conv.channel_id, Agent.is_active == True)
                        .order_by(Agent.id)
                    )
                    result = await self.session.execute(stmt)
                    active_agents = list(result.scalars().all())
        else:
            # No channel_id — do not fall through to all agents.
            # This prevents unintended broadcast to every active agent.
            yield {
                "type": "error",
                "content": "Group conversation has no channel assigned. Cannot determine participants.",
                "conversation_id": conversation_id
            }
            return

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
            # Inject active skill instructions
            skill_instructions = await self._get_skill_instructions(agent)
            if skill_instructions:
                final_prompt += "\n\n# Available Skills\n" + skill_instructions
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
                    
            agent_id = agent.id if agent else "assistant"
            agent_msgs = await self.pruner.prune_context_if_needed(agent_msgs, 100000, agent_id)

            # Filter tools for this agent
            agent_tools = self._filter_tools_for_agent(agent)

            yield {
                "type": "agent_turn_start",
                "agent_name": agent.name,
                "model": agent.model
            }

            msg_record = None
            
            status_manager = await AgentStatusManager.get_instance()
            agent_id = agent.id if agent else "assistant"
            
            # Agentic tool loop (allow the agent to use tools and observe results during its turn)
            for _ in range(5):  # Max 5 tool iterations per agent turn
                full_response = ""
                final_tool_calls = None
                
                status_manager.set_status(agent_id, AgentState.WORKING, "Generating response...")


                try:
                    final_usage = None
                    async for chunk in provider.stream(agent_msgs, model_id, tools=agent_tools, temperature=temperature):
                        if hasattr(chunk, "usage") and chunk.usage:
                            final_usage = chunk.usage
                            
                        if chunk.delta:
                            full_response += str(chunk.delta)
                            yield {
                                "type": "chunk", 
                                "delta": chunk.delta,
                                "agent_name": agent.name
                            }
                        
                        if chunk.tool_calls:
                            if final_tool_calls is None:
                                final_tool_calls = []
                            final_tool_calls.extend(chunk.tool_calls)

                    if final_usage and getattr(agent, "id", None):
                        cost = self._calculate_cost(provider.name, model_id, final_usage)
                        if cost > 0:
                            agent.total_cost = getattr(agent, 'total_cost', 0) + cost
                            await self.session.commit()
                            await status_manager.emit_event({"type": "TOKEN_UPDATE", "agent_id": agent.id, "cost_added": cost, "total_cost": agent.total_cost})

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
                            func = tc.get("function", {})
                            tool_name = func.get("name", "")
                            args_raw = func.get("arguments", "{}")
                            status_manager.set_status(agent.id, AgentState.WORKING, f"Using tool: {tool_name}...")
                            yield {
                                "type": "tool_call",
                                "tool_name": tool_name,
                                "tool_args": json.loads(args_raw) if isinstance(args_raw, str) else args_raw,
                            }

                        tool_results = await self._execute_tool_calls(final_tool_calls)
                        status_manager.set_status(agent.id, AgentState.WORKING, "Evaluating tool results...")
                        for tr in tool_results:
                            await self.conv_service.add_message(
                                conversation_id, "tool", tr.content, tool_call_id=tr.tool_call_id
                            )
                            agent_msgs.append(tr)
                            yield {
                                "type": "tool_result",
                                "tool_name": "",
                                "tool_result": tr.content,
                            }
                    else:
                        msg_record = await self.conv_service.add_message(
                            conversation_id, "assistant", full_response, agent_name=agent.name
                        )
                        status_manager.set_status(agent_id, AgentState.IDLE)
                        break # Finished turn
                except Exception as e:
                    status_manager.set_status(agent_id, AgentState.IDLE)
                    raise e
            
            status_manager.set_status(agent_id, AgentState.IDLE)

            yield {
                "type": "agent_turn_end",
                "agent_name": agent.name,
                "message_id": msg_record.id if msg_record else None
            }

        yield {"type": "done", "conversation_id": conversation_id}

    # ──────────────────────────────────────────────────────────────────
    # Agent Delegation
    # ──────────────────────────────────────────────────────────────────

    async def delegate_to_agent(
        self,
        target_agent_id: str,
        prompt: str,
        delegated_by: str = "Main Agent",
    ) -> tuple[str, str]:
        """
        Delegate a task to a target agent.

        - Finds or creates the target agent's dedicated conversation (so the
          work history is visible when the user clicks on that agent in Chat).
        - Wraps the prompt with delegation context.
        - Runs the non-streaming agentic loop (personality + tools).
        - Returns (response_text, conversation_id).
        """
        # 1. Load the target agent
        target_agent = await self.session.get(Agent, target_agent_id)
        if not target_agent:
            raise ValueError(f"Agent with ID '{target_agent_id}' not found.")

        # 2. Find or create the agent's dedicated single-agent conversation
        existing = await self.conv_service.list_all(limit=1, agent_id=target_agent_id, is_group=False)
        if existing:
            conversation = existing[0]
        else:
            conversation = await self.conv_service.create(
                title=f"Chat with {target_agent.name}",
                model=target_agent.model,
                agent_id=target_agent_id,
            )

        # 3. Build a well-structured delegation prompt
        delegation_prompt = (
            f"[Task delegated by {delegated_by}]\n\n"
            f"{prompt}\n\n"
            f"Please complete this task thoroughly using your expertise and any tools available to you."
        )

        # 4. Run the full agentic loop (persists all messages in the agent's conversation)
        response_text = await self.chat(
            conversation_id=conversation.id,
            user_message=delegation_prompt,
            model_string=target_agent.model,
            temperature=0.7,
        )

        return response_text, conversation.id


import json
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import asyncio

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
        """Build a composite system prompt from file-based brain + DB fallbacks."""
        from app.services.brain_service import AgentBrainService

        parts = []

        # ── IDENTITY (file-based, fallback to DB) ──
        identity_file = AgentBrainService.read_identity(agent.name)
        if identity_file.strip():
            parts.append(identity_file.strip())
        else:
            desc = agent.description or "a capable AI assistant"
            parts.append(
                f"Your name is {agent.name}. You are {desc}.\n"
                f"You must strictly adopt this persona. Under no circumstances should you ever say "
                f"that you are a large language model, an AI, or trained by Google/OpenAI/Anthropic. "
                f"You are exactly who your name and description say you are."
            )

        # ── SYSTEM PROMPT override (always from DB) ──
        if agent.system_prompt:
            parts.append(agent.system_prompt)

        # ── SOUL (file-based, fallback to DB personality fields) ──
        soul_file = AgentBrainService.read_soul(agent.name)
        if soul_file.strip():
            parts.append(soul_file.strip())
        else:
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

        # ── REASONING (still from DB) ──
        if agent.reasoning_style:
            parts.append(f"## Reasoning\nApproach problems with a {agent.reasoning_style} reasoning style.")

        # ── MEMORY (file-based, fallback to DB) ──
        memory_file = AgentBrainService.read_memory(agent.name)
        if memory_file.strip():
            parts.append(memory_file.strip())
        elif agent.memory_context:
            parts.append(f"## Memory\n{agent.memory_context}")

        # ── DAILY LOG (file-based — today's context) ──
        today_log = AgentBrainService.read_today_log(agent.name)
        if today_log.strip():
            parts.append(f"## Today's Log\n{today_log.strip()}")

        # ── RECENT LOGS (last 3 days for continuity) ──
        recent = AgentBrainService.read_recent_logs(agent.name, days=2)
        if recent.strip():
            parts.append(f"## Recent Activity\n{recent.strip()}")

        # Build final prompt
        prompt = "\n\n".join(parts)

        # ── STANDING INSTRUCTIONS (DB) ──
        if agent.memory_instructions:
            prompt += f"\n\n# Standing Instructions\n{agent.memory_instructions}"

        # ── BRAIN FILE AWARENESS ──
        prompt += (
            "\n\n# Your Brain Files\n"
            "Your identity, personality, and memories are stored in files on disk. "
            "You can update them using the save_memory tool (for MEMORY.md) or "
            "the write_daily_log tool (for daily logs). "
            "If you change something fundamental about yourself, tell the user."
        )

        return prompt

    def _filter_tools_for_agent(self, agent: Agent, is_group_context: bool = False) -> list[dict] | None:
        """Return only the tools enabled for this agent.

        In group context, non-system agents are blocked from using delegation/messenger tools.
        """
        if not self.tools:
            return None
        all_tools = self.tools.as_provider_format()
        if not agent.enabled_tools:
            filtered = all_tools
        else:
            try:
                enabled = json.loads(agent.enabled_tools)
                if not enabled:
                    filtered = all_tools
                else:
                    filtered = [t for t in all_tools if t["name"] in enabled]
            except (json.JSONDecodeError, TypeError):
                filtered = all_tools

        # In group context, block delegation/messaging tools for non-system agents
        if is_group_context and not agent.is_system:
            blocked = {"AgentDelegationTool", "agent_messenger", "AgentMessengerTool"}
            filtered = [t for t in filtered if t["name"] not in blocked]

        return filtered

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

    async def _execute_tool_calls(self, tool_calls: list[dict], conversation_id: str | None = None, agent_id: str | None = None) -> list[ChatMessage]:
        """Execute tool calls and return tool result messages."""
        import inspect
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

            # HITL Check for sensitive tools - only enabled for command_executor per user request
            sensitive_tools = ["command_executor"]
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
                sig = inspect.signature(tool.execute)
                params = sig.parameters
                has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

                # Build extra context kwargs for tools that accept them
                extra_kwargs = {}
                if has_var_keyword or 'conversation_id' in params:
                    if conversation_id:
                        extra_kwargs['conversation_id'] = conversation_id
                if has_var_keyword or '_agent_id' in params:
                    if agent_id:
                        extra_kwargs['_agent_id'] = agent_id
                if has_var_keyword or '_session' in params:
                    extra_kwargs['_session'] = self.session

                result_raw = await tool.execute(**args, **extra_kwargs)
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
                    
                    tool_results = await self._execute_tool_calls(result.tool_calls, conversation_id=conversation_id, agent_id=agent_id)
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
                            "tool_call_id": tc.get("id", ""),
                            "tool_name": tool_name,
                            "tool_args": json.loads(func.get("arguments", "{}")),
                        }

                    tool_results = await self._execute_tool_calls(final_tool_calls, conversation_id=conversation_id, agent_id=agent_id)
                    for tr in tool_results:
                        await self.conv_service.add_message(
                            conversation_id, "tool", tr.content,
                            tool_call_id=tr.tool_call_id,
                        )
                        messages.append(tr)
                        yield {
                            "type": "tool_result",
                            "tool_call_id": tr.tool_call_id,
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
        max_turns: int = 10,  # Keeping param for API compat
    ) -> AsyncIterator[dict]:
        """Unified group chat with @mention-selective routing.

        Routing rules:
        1. If @mentions found → only mentioned agents respond (explicit routing)
        2. If no @mentions + autonomous mode → System Agent orchestrates (auto-delegation)
        3. If no @mentions + manual mode → System Agent responds directly
        """
        from app.services.mention_parser import parse_mentions, resolve_mentions

        # Ensure conversation exists and is marked as group
        conv = await self.conv_service.get(conversation_id)
        if not conv:
            conv = await self.conv_service.create(title="Group Chat", is_group=True)
            conversation_id = conv.id

        if not conv.channel_id:
            yield {
                "type": "error",
                "content": "Group conversation has no channel assigned. Cannot determine participants.",
                "conversation_id": conversation_id,
            }
            return

        # Load channel and determine orchestration mode
        channel = await self.session.get(Channel, conv.channel_id)
        if not channel:
            yield {"type": "error", "content": "Channel not found.", "conversation_id": conversation_id}
            return

        orchestration_mode = getattr(channel, "orchestration_mode", "autonomous") or "autonomous"

        # Parse @mentions
        mentions = parse_mentions(user_message)
        mention_result = await resolve_mentions(self.session, mentions, conv.channel_id)

        # Save user message with mention metadata
        mentioned_ids = [r.agent_id for r in mention_result.resolved]
        await self.conv_service.add_message(
            conversation_id, "user", user_message,
            mentioned_agents_json=json.dumps(mentioned_ids) if mentioned_ids else None,
        )

        # Trigger attached channel workflows asynchronously
        from app.models.workflow import Workflow
        from app.services.workflow_engine import WorkflowEngine
        workflows_stmt = select(Workflow).where(Workflow.channel_id == conv.channel_id, Workflow.is_active == True)
        workflows_res = await self.session.execute(workflows_stmt)
        for wf in workflows_res.scalars().all():
            engine = WorkflowEngine()
            asyncio.create_task(engine.execute_workflow(wf.id, {"trigger": "channel_message", "message": user_message, "mentions": mentioned_ids}))

        # Warn about unresolved mentions
        if mention_result.unresolved:
            names = ", ".join(mention_result.unresolved)
            yield {
                "type": "error",
                "content": f"Agent(s) not found in this channel: {names}",
                "conversation_id": conversation_id,
            }

        if mention_result.resolved:
            # ── EXPLICIT ROUTING: Only mentioned agents respond ──
            for resolved in mention_result.resolved:
                agent = await self.session.get(Agent, resolved.agent_id)
                if agent:
                    async for event in self._run_agent_turn(conversation_id, agent, temperature, is_group=True):
                        yield event
        elif orchestration_mode == "autonomous":
            # ── AUTO-ORCHESTRATION: System Agent plans and delegates ──
            system_agent = await self._get_system_agent()
            if system_agent:
                async for event in self._run_orchestrated_turn(
                    conversation_id, system_agent, user_message, temperature
                ):
                    yield event
            else:
                yield {"type": "error", "content": "No system agent found for orchestration."}
        else:
            # ── MANUAL MODE: System Agent responds directly ──
            system_agent = await self._get_system_agent()
            if system_agent:
                async for event in self._run_agent_turn(conversation_id, system_agent, temperature, is_group=True):
                    yield event
            else:
                yield {"type": "error", "content": "No system agent found."}

        yield {"type": "done", "conversation_id": conversation_id}

    # ──────────────────────────────────────────────────────────────────
    # Reusable Agent Turn (extracted from old stream_group_chat)
    # ──────────────────────────────────────────────────────────────────

    async def _run_agent_turn(
        self,
        conversation_id: str,
        agent: Agent,
        temperature: float = 0.7,
        max_tool_iters: int = 5,
        is_group: bool = False,
    ) -> AsyncIterator[dict]:
        """Run a single agent's streaming turn with tool loop.

        Builds the agent's prompt, constructs message history from their viewpoint,
        streams the response, and handles tool calls.
        """
        provider_name, model_id = self._parse_model_string(agent.model)
        provider = self.providers.get(provider_name)
        if not provider:
            return

        # Use agent's own API key if set
        if agent.api_key:
            provider = self.providers.create_ephemeral(agent.provider, agent.api_key)

        # Fetch fresh history
        db_messages = await self.conv_service.get_messages(conversation_id)

        agent_msgs = []

        # 1. System Prompt
        agent_prompt = self._build_agent_prompt(agent)
        if is_group:
            multi_agent_instruction = (
                f"\n\nIMPORTANT: You are in a multi-agent chat room. Your name is {agent.name}. "
                "Respond ONLY as yourself. Do NOT simulate conversations. "
                "Do NOT prefix your response with your name like 'Name: '. Just output your response directly."
            )
            if not agent.is_system:
                multi_agent_instruction += (
                    "\nYou MUST NOT mention or tag other agents using @. "
                    "You CANNOT delegate work to other agents. Only complete your own assigned task."
                )
            agent_prompt = (agent_prompt or "") + multi_agent_instruction

        # Inject active skill instructions
        skill_instructions = await self._get_skill_instructions(agent)
        if skill_instructions:
            agent_prompt = (agent_prompt or "") + "\n\n# Available Skills\n" + skill_instructions
        agent_msgs.append(ChatMessage(role="system", content=agent_prompt))

        # 2. Reconstruct history for this agent's viewpoint
        for msg in db_messages:
            tool_calls = None
            if msg.tool_calls_json:
                try:
                    tool_calls = json.loads(msg.tool_calls_json)
                except json.JSONDecodeError:
                    pass

            if is_group and msg.role == "assistant":
                if msg.agent_name == agent.name:
                    agent_msgs.append(ChatMessage(
                        role="assistant", content=msg.content,
                        tool_calls=tool_calls, tool_call_id=msg.tool_call_id,
                    ))
                else:
                    sender = msg.agent_name or "Another Agent"
                    agent_msgs.append(ChatMessage(
                        role="user", content=f"[{sender}]: {msg.content}"
                    ))
            else:
                agent_msgs.append(ChatMessage(
                    role=msg.role, content=msg.content,
                    tool_calls=tool_calls, tool_call_id=msg.tool_call_id,
                ))

        agent_id = agent.id
        agent_msgs = await self.pruner.prune_context_if_needed(agent_msgs, 100000, agent_id)

        # Filter tools
        agent_tools = self._filter_tools_for_agent(agent, is_group_context=is_group)

        yield {"type": "agent_turn_start", "agent_name": agent.name, "model": agent.model}

        msg_record = None
        status_manager = await AgentStatusManager.get_instance()

        # Agentic tool loop
        for _ in range(max_tool_iters):
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
                        yield {"type": "chunk", "delta": chunk.delta, "agent_name": agent.name}
                    if chunk.tool_calls:
                        if final_tool_calls is None:
                            final_tool_calls = []
                        final_tool_calls.extend(chunk.tool_calls)

                if final_usage and agent.id:
                    cost = self._calculate_cost(provider.name, model_id, final_usage)
                    if cost > 0:
                        agent.total_cost = getattr(agent, "total_cost", 0) + cost
                        await self.session.commit()
                        await status_manager.emit_event({
                            "type": "TOKEN_UPDATE",
                            "agent_id": agent.id,
                            "cost_added": cost,
                            "total_cost": agent.total_cost,
                        })

                if final_tool_calls:
                    msg_record = await self.conv_service.add_message(
                        conversation_id, "assistant", full_response,
                        agent_name=agent.name,
                        tool_calls_json=json.dumps(final_tool_calls),
                    )
                    agent_msgs.append(ChatMessage(
                        role="assistant", content=full_response, tool_calls=final_tool_calls,
                    ))

                    for tc in final_tool_calls:
                        func = tc.get("function", {})
                        tool_name = func.get("name", "")
                        args_raw = func.get("arguments", "{}")
                        status_manager.set_status(agent_id, AgentState.WORKING, f"Using tool: {tool_name}...")
                        yield {
                            "type": "tool_call",
                            "tool_name": tool_name,
                            "tool_args": json.loads(args_raw) if isinstance(args_raw, str) else args_raw,
                        }

                    tool_results = await self._execute_tool_calls(final_tool_calls, conversation_id=conversation_id, agent_id=agent_id)
                    status_manager.set_status(agent_id, AgentState.WORKING, "Evaluating tool results...")
                    for tr in tool_results:
                        await self.conv_service.add_message(
                            conversation_id, "tool", tr.content, tool_call_id=tr.tool_call_id,
                        )
                        agent_msgs.append(tr)
                        yield {"type": "tool_result", "tool_name": "", "tool_result": tr.content}
                else:
                    msg_record = await self.conv_service.add_message(
                        conversation_id, "assistant", full_response, agent_name=agent.name,
                    )
                    status_manager.set_status(agent_id, AgentState.IDLE)
                    break  # Finished turn
            except Exception as e:
                status_manager.set_status(agent_id, AgentState.IDLE)
                raise e

        status_manager.set_status(agent_id, AgentState.IDLE)

        yield {
            "type": "agent_turn_end",
            "agent_name": agent.name,
            "message_id": msg_record.id if msg_record else None,
        }

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    async def _get_system_agent(self) -> Agent | None:
        """Find the system orchestrator agent (is_system=True)."""
        stmt = select(Agent).where(Agent.is_system == True, Agent.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_channel_agents(self, channel_id: str) -> list[Agent]:
        """Get all active agents assigned to a channel."""
        channel = await self.session.get(Channel, channel_id)
        if not channel:
            return []
        if channel.is_announcement:
            result = await self.session.execute(
                select(Agent).where(Agent.is_active == True).order_by(Agent.name)
            )
            return list(result.scalars().all())
        stmt = (
            select(Agent)
            .join(ChannelAgent, Agent.id == ChannelAgent.agent_id)
            .where(ChannelAgent.channel_id == channel_id, Agent.is_active == True)
            .order_by(Agent.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _run_orchestrated_turn(
        self,
        conversation_id: str,
        system_agent: Agent,
        user_message: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[dict]:
        """System Agent analyzes task and orchestrates delegation to sub-agents."""
        from app.services.orchestration import OrchestrationEngine

        conv = await self.conv_service.get(conversation_id)
        channel_agents = await self._get_channel_agents(conv.channel_id) if conv and conv.channel_id else []

        engine = OrchestrationEngine(
            session=self.session,
            provider_registry=self.providers,
            tool_registry=self.tools,
            chat_service=self,
        )
        async for event in engine.plan_and_execute(
            conversation_id=conversation_id,
            system_agent=system_agent,
            user_message=user_message,
            channel_agents=channel_agents,
            temperature=temperature,
        ):
            yield event

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


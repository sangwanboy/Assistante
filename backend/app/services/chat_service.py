import json
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
from app.services.tool_governor import ToolGovernor
from app.services.memory_compactor import MemoryCompactor
from app.services.context_assembler import ContextAssembler
from app.providers.base import TokenUsage
from app.services.llm_gateway import get_gateway
import uuid

# Storm prevention: max agents responding simultaneously
MAX_SIMULTANEOUS_RESPONDING_AGENTS = 3
_response_semaphore = asyncio.Semaphore(MAX_SIMULTANEOUS_RESPONDING_AGENTS)

# Conversation depth limit
MAX_CONVERSATION_DEPTH = 6
MIN_AGENT_CONTEXT_WINDOW_TOKENS = 60000
MAX_AGENT_CONTEXT_WINDOW_TOKENS = 256000
# Three-threshold context pruning model (Phase 3)
CONTEXT_SOFT_TRIGGER_RATIO      = 0.60   # log warning, no structural change
CONTEXT_PRUNE_TRIGGER_RATIO     = 0.80   # summarise middle messages
CONTEXT_EMERGENCY_TRIGGER_RATIO = 0.99   # hard truncate to system + last 3

# Token budget allocations per LLM request (as % of context_window_tokens).
# These govern how much of the context window each layer may consume.
TOKEN_BUDGET_SYSTEM_PCT        = 0.10   # system prompt (identity + soul + mind)
TOKEN_BUDGET_RECENT_PCT        = 0.30   # recent conversation turns
TOKEN_BUDGET_SEMANTIC_MEM_PCT  = 0.20   # semantic memory injection (Tier-2)
TOKEN_BUDGET_USER_MSG_PCT      = 0.10   # current user message
TOKEN_BUDGET_REASONING_PCT     = 0.30   # model reasoning buffer (reserved)


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
        self.compactor = MemoryCompactor(provider_registry)
        self.assembler = ContextAssembler()

    def _build_pruned_context_sync_note(self) -> str:
        return (
            "[PRUNED CONTEXT SYNC] This conversation was pruned. Preserve the agent's "
            "IDENTITY, SOUL, and MIND as authoritative, and use the pruned summary only "
            "as condensed historical context."
        )

    async def _build_context_with_memory(
        self,
        agent: "Agent | None",
        prompt: str,
        messages: list,
        context_window_tokens: int,
    ) -> list:
        """Retrieve Tier-2 semantic memories and build layered context.

        1. Retrieve top semantic memories for the agent (Tier-2).
        2. Use ContextAssembler to inject them as a dedicated system layer.

        Returns the layered message list ready for pruning.
        """
        if agent is None:
            return messages

        semantic_memory: str = ""
        try:
            # Limit semantic memory to its token budget slice
            mem_token_limit = int(context_window_tokens * TOKEN_BUDGET_SEMANTIC_MEM_PCT)
            # Estimate ~3 tokens per char; translate to rough char limit for retrieval
            char_budget = mem_token_limit * 3
            semantic_memory = await self.compactor.retrieve_for_context(
                agent.id, self.session, limit=20
            )
            # Trim to char budget if over
            if len(semantic_memory) > char_budget:
                semantic_memory = semantic_memory[:char_budget] + "\n[...memory truncated for budget]"
        except Exception:
            pass  # Non-critical — proceed without semantic memory

        if not semantic_memory:
            return messages

        return self.assembler.build(
            system_prompt=prompt,
            messages=messages,
            semantic_memory=semantic_memory,
        )

    def _resolve_context_window_tokens(self, agent: Agent | None) -> int:
        configured = getattr(agent, "context_window_tokens", None) if agent else None
        if configured is None:
            return MAX_AGENT_CONTEXT_WINDOW_TOKENS
        return max(
            MIN_AGENT_CONTEXT_WINDOW_TOKENS,
            min(MAX_AGENT_CONTEXT_WINDOW_TOKENS, int(configured)),
        )

    def _parse_model_string(self, model_string: str) -> tuple[str, str]:
        """Parse 'provider/model' into (provider_name, model_id)."""
        if "/" in model_string:
            provider, model = model_string.split("/", 1)
            return provider, model
        return "openai", model_string

    async def _resolve_provider_and_model(self, model_string: str) -> tuple[str, str, object, str | None]:
        """Resolve provider/model and fallback gracefully if provider key is missing."""
        provider_name, model_id = self._parse_model_string(model_string)
        try:
            provider = self.providers.get(provider_name)
            return provider_name, model_id, provider, None
        except ValueError:
            registered = self.providers.registered_providers()
            available = []
            for name in registered:
                try:
                    p = self.providers.get(name)
                    if p.is_available():
                        available.append(name)
                except Exception:
                    continue

            fallback_order = ["gemini", "openai", "anthropic", "ollama"]
            fallback_candidates = [p for p in fallback_order if p in available and p != provider_name]
            if not fallback_candidates:
                raise ValueError(
                    f"Provider '{provider_name}' is not configured. "
                    "No available fallback provider found. Configure an API key in Settings or start Ollama."
                )

            fallback_provider_name = fallback_candidates[0]
            provider = self.providers.get(fallback_provider_name)
            fallback_model_id = model_id
            try:
                models = await provider.list_models()
                if models:
                    fallback_model_id = models[0].id
            except Exception:
                pass

            warning = (
                f"Provider '{provider_name}' not configured; "
                f"falling back to '{fallback_provider_name}/{fallback_model_id}'."
            )
            return fallback_provider_name, fallback_model_id, provider, warning

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

        # ── SYSTEM AWARENESS (Model & Provider) ──
        prompt += (
            f"\n\n# System Awareness\n"
            f"You are currently running on the '{agent.model}' model provided by '{agent.provider}'. "
            f"If asked what model or system you are running on, you must answer with this exact information."
        )

        if getattr(agent, "is_system", False):
            prompt += (
                "\n\n# Delegation Policy\n"
                "You are the orchestrator and you ARE capable of delegating work. "
                "When a user asks you to delegate, assign, distribute, or rerun work via other agents, "
                "you must use your delegation tools (especially AgentDelegationTool) instead of replying "
                "that you cannot delegate. "
                "If needed, split work into clear subtasks and delegate to multiple agents one by one."
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

    def _is_capability_query(self, text: str) -> bool:
        lowered = (text or "").strip().lower()
        if not lowered:
            return False
        triggers = [
            "what tools",
            "which tools",
            "list tools",
            "what features",
            "which features",
            "what can you do",
            "capabilities",
            "access to",
            "available tools",
            "available features",
        ]
        return any(t in lowered for t in triggers)

    def _is_unhelpful_refusal(self, text: str) -> bool:
        lowered = (text or "").strip().lower()
        refusal_markers = [
            "i'm sorry, but i don't have the capability",
            "i do not have the capability",
            "i don't have the capability",
            "unable to assist with that",
            "cannot assist with that",
        ]
        return any(marker in lowered for marker in refusal_markers)

    async def _build_capability_response(self, agent: Agent) -> str:
        tools = self.tools.list_tools() if self.tools else []
        if agent.enabled_tools:
            try:
                enabled = set(json.loads(agent.enabled_tools or "[]"))
                if enabled:
                    tools = [t for t in tools if t.get("name") in enabled]
            except (json.JSONDecodeError, TypeError):
                pass

        tools = sorted(tools, key=lambda t: t.get("name", ""))
        top_tools = tools[:12]
        tool_lines = [f"- {t.get('name', 'unknown')}: {t.get('description', 'No description available.')}" for t in top_tools]
        more_count = max(0, len(tools) - len(top_tools))

        active_specialists = []
        try:
            res = await self.session.execute(
                select(Agent).where(Agent.is_active, Agent.is_system == False).order_by(Agent.name)  # noqa: E712
            )
            active_specialists = [a.name for a in res.scalars().all()][:8]
        except Exception:
            active_specialists = []

        header = (
            "I can both chat with you directly and orchestrate work across agents. "
            "Use me like a normal assistant; I will delegate only when it helps."
        )
        specialist_line = (
            "Active specialist agents: " + ", ".join(active_specialists)
            if active_specialists
            else "Active specialist agents: none detected right now."
        )

        response_parts = [header, "", specialist_line, "", "Current tools I can access:"]
        response_parts.extend(tool_lines if tool_lines else ["- No tools are currently available."])
        if more_count:
            response_parts.append(f"- ...and {more_count} more tools.")
        response_parts.append("")
        response_parts.append("Tell me your task in one line, and I will either solve it directly or delegate it with a clear plan.")
        return "\n".join(response_parts)

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

    async def _execute_tool_calls(self, tool_calls: list[dict], conversation_id: str | None = None, agent_id: str | None = None, task_id: str | None = None) -> list[ChatMessage]:
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
                task_id_hitl = tc.get("id", str(uuid.uuid4()))
                try:
                    approved = await hitl_manager.request_approval(task_id_hitl, tool_name, args)
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
                if has_var_keyword or '_task_id' in params:
                    if task_id:
                        extra_kwargs['_task_id'] = task_id

                import asyncio
                # Enforce a 60-second execution timeout on all tools
                result_raw = await asyncio.wait_for(
                    tool.execute(**args, **extra_kwargs),
                    timeout=180.0
                )
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
            except asyncio.TimeoutError:
                result_str = (
                    f"Tool '{tool_name}' timed out after 60 seconds.\n"
                    f"Please try again with a narrower scope or a different approach."
                )
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
        # Ensure conversation exists
        conv = await self.conv_service.get(conversation_id)
        if not conv:
            conv = await self.conv_service.create(model=model_string)
            conversation_id = conv.id

        # If conversation is tied to an agent, prioritize agent's model config
        agent = None
        if conv.agent_id:
            agent = await self.session.get(Agent, conv.agent_id)
        
        effective_model = agent.model if agent else model_string
        provider_name, model_id, provider, fallback_warning = await self._resolve_provider_and_model(effective_model)

        # Save user message
        await self.conv_service.add_message(conversation_id, "user", user_message)

        # Build message history
        db_messages = await self.conv_service.get_messages(conversation_id)

        # Deterministic delegation contribution recall for orchestrator.
        if agent and agent.is_system:
            if self._is_capability_query(user_message):
                capability_reply = await self._build_capability_response(agent)
                await self.conv_service.add_message(
                    conversation_id,
                    "assistant",
                    capability_reply,
                    agent_name=agent.name,
                )
                return capability_reply

            contribution_reply = await self._maybe_handle_delegation_contribution_query(
                conversation_id=conversation_id,
                user_message=user_message,
            )
            if contribution_reply:
                await self.conv_service.add_message(
                    conversation_id,
                    "assistant",
                    contribution_reply,
                    agent_name=agent.name,
                )
                return contribution_reply

        # Deterministic delegation path for explicit orchestrator requests.
        if agent and agent.is_system:
            delegated_reply = await self._maybe_handle_system_delegation_request(
                conversation_id=conversation_id,
                user_message=user_message,
                system_agent=agent,
            )
            if delegated_reply:
                await self.conv_service.add_message(
                    conversation_id,
                    "assistant",
                    delegated_reply,
                    agent_name=agent.name,
                )
                return delegated_reply
        
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
        if fallback_warning:
            messages.append(ChatMessage(role="system", content=fallback_warning))

        context_window_tokens = self._resolve_context_window_tokens(agent)

        # Inject Tier-2 semantic memories into layered context (Section 9 — Memory Retrieval)
        messages = await self._build_context_with_memory(agent, prompt, messages, context_window_tokens)

        agent_id = agent.id if agent else "assistant"

        # Three-threshold context pruning: soft warning → active prune → emergency truncate.
        messages = await self.pruner.prune_context_if_needed(
            messages,
            context_window_tokens,
            agent_id,
            soft_trigger_ratio=CONTEXT_SOFT_TRIGGER_RATIO,
            prune_trigger_ratio=CONTEXT_PRUNE_TRIGGER_RATIO,
            emergency_trigger_ratio=CONTEXT_EMERGENCY_TRIGGER_RATIO,
            refreshed_system_prompt=prompt if agent else None,
            prune_sync_note=self._build_pruned_context_sync_note() if agent else None,
            agent_name=agent.name if agent else None,
        )
        max_iterations = 40
        max_tool_calls = 12
        max_tokens_per_task = 200000
        
        tool_calls_total = 0
        tokens_used_total = 0
        
        status_manager = await AgentStatusManager.get_instance()
        governor = ToolGovernor(max_consecutive=3, reflection_interval=3)
        
        status_manager.set_status(agent_id, AgentState.WORKING, "Generating response...")

        try:
            gateway = await get_gateway()
            for step in range(max_iterations):
                result = await gateway.complete(provider, messages, model_id, agent_id, self.session, tools=tool_schemas, temperature=temperature)

                if hasattr(result, "usage") and result.usage:
                    tokens_used_total += getattr(result.usage, 'total_tokens', 0)
                    if getattr(agent, "id", None):
                        cost = self._calculate_cost(provider.name, model_id, result.usage)
                        if cost > 0:
                            agent.total_cost = getattr(agent, 'total_cost', 0) + cost
                            await self.session.commit()
                            await status_manager.emit_event({"type": "TOKEN_UPDATE", "agent_id": agent.id, "cost_added": cost, "total_cost": agent.total_cost})
                
                # Check Token Burn Limits
                if tokens_used_total >= max_tokens_per_task:
                    messages.append(ChatMessage(role="system", content="HARD LIMIT: Maximum token budget reached. You must immediately summarize your work, provide the best final answer you can, and STOP using tools."))

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
                        tool_calls_total += 1
                        func = tc.get("function", {})
                        tool_name = func.get("name", "")
                        status_manager.set_status(agent_id, AgentState.WORKING, f"Using tool: {tool_name}...")
                        
                    if tool_calls_total >= max_tool_calls:
                        messages.append(ChatMessage(role="system", content="HARD LIMIT: Maximum tool calls reached. You must immediately provide your final answer without any further tools."))
                    
                    tool_results = await self._execute_tool_calls(result.tool_calls, conversation_id=conversation_id, agent_id=agent_id)
                    status_manager.set_status(agent_id, AgentState.WORKING, "Evaluating tool results...")
                    
                    for tr in tool_results:
                        await self.conv_service.add_message(
                            conversation_id, "tool", tr.content,
                            tool_call_id=tr.tool_call_id,
                        )
                        messages.append(tr)

                    for tc in result.tool_calls:
                        func = tc.get("function", {})
                        t_name = func.get("name", "")
                        t_args = func.get("arguments", "{}")
                        intervention = governor.record_and_check(t_name, t_args)
                        if intervention:
                            messages.append(ChatMessage(role="user", content=intervention))
                            break
                    
                    reflection = governor.should_reflect()
                    if reflection:
                        messages.append(ChatMessage(role="user", content=reflection))
                else:
                    # Final response
                    response_text = result.content
                    if agent and agent.is_system and self._is_unhelpful_refusal(response_text):
                        response_text = await self._build_capability_response(agent)
                    await self.conv_service.add_message(
                        conversation_id, "assistant", response_text, agent_name=agent_name
                    )
                    status_manager.set_status(agent_id, AgentState.IDLE)
                    return response_text

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
        # Ensure conversation exists
        conv = await self.conv_service.get(conversation_id)
        if not conv:
            conv = await self.conv_service.create(model=model_string)
            conversation_id = conv.id

        # If conversation is tied to an agent, prioritize agent's model config
        agent = None
        if conv.agent_id:
            agent = await self.session.get(Agent, conv.agent_id)

        effective_model = agent.model if agent else model_string
        provider_name, model_id, provider, fallback_warning = await self._resolve_provider_and_model(effective_model)

        # Save user message
        await self.conv_service.add_message(conversation_id, "user", user_message)

        # Build message history
        db_messages = await self.conv_service.get_messages(conversation_id)

        # Deterministic delegation contribution recall for orchestrator.
        if agent and agent.is_system:
            if self._is_capability_query(user_message):
                capability_reply = await self._build_capability_response(agent)
                msg = await self.conv_service.add_message(
                    conversation_id,
                    "assistant",
                    capability_reply,
                    agent_name=agent.name,
                )
                yield {"type": "agent_turn_start", "agent_name": agent.name}
                yield {"type": "chunk", "delta": capability_reply}
                yield {
                    "type": "agent_turn_end",
                    "agent_name": agent.name,
                    "message_id": msg.id,
                }
                yield {
                    "type": "done",
                    "message_id": msg.id,
                    "conversation_id": conversation_id,
                }
                return

            contribution_reply = await self._maybe_handle_delegation_contribution_query(
                conversation_id=conversation_id,
                user_message=user_message,
            )
            if contribution_reply:
                msg = await self.conv_service.add_message(
                    conversation_id,
                    "assistant",
                    contribution_reply,
                    agent_name=agent.name,
                )
                yield {"type": "agent_turn_start", "agent_name": agent.name}
                yield {"type": "chunk", "delta": contribution_reply}
                yield {
                    "type": "agent_turn_end",
                    "agent_name": agent.name,
                    "message_id": msg.id,
                }
                yield {
                    "type": "done",
                    "message_id": msg.id,
                    "conversation_id": conversation_id,
                }
                return

        # Deterministic delegation path for explicit orchestrator requests.
        if agent and agent.is_system:
            delegated_reply = await self._maybe_handle_system_delegation_request(
                conversation_id=conversation_id,
                user_message=user_message,
                system_agent=agent,
            )
            if delegated_reply:
                msg = await self.conv_service.add_message(
                    conversation_id,
                    "assistant",
                    delegated_reply,
                    agent_name=agent.name,
                )
                yield {"type": "agent_turn_start", "agent_name": agent.name}
                yield {"type": "chunk", "delta": delegated_reply}
                yield {
                    "type": "agent_turn_end",
                    "agent_name": agent.name,
                    "message_id": msg.id,
                }
                yield {
                    "type": "done",
                    "message_id": msg.id,
                    "conversation_id": conversation_id,
                }
                return
        
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
        if fallback_warning:
            messages.append(ChatMessage(role="system", content=fallback_warning))

        context_window_tokens = self._resolve_context_window_tokens(agent)

        # Inject Tier-2 semantic memories into layered context (Section 9 — Memory Retrieval)
        messages = await self._build_context_with_memory(agent, prompt, messages, context_window_tokens)

        # Resolve agent_id for status updates
        status_manager = await AgentStatusManager.get_instance()
        agent_id = None
        if agent:
            agent_id = agent.id
        else:
            # Fallback: try to find the system orchestrator agent id
            stmt = select(Agent).where(Agent.is_system)
            res = await self.session.execute(stmt)
            system_agent = res.scalar_one_or_none()
            if system_agent:
                agent_id = system_agent.id
            else:
                agent_id = "assistant" # Last resort
                
        # Three-threshold context pruning: soft warning → active prune → emergency truncate.
        messages = await self.pruner.prune_context_if_needed(
            messages,
            context_window_tokens,
            agent_id,
            soft_trigger_ratio=CONTEXT_SOFT_TRIGGER_RATIO,
            prune_trigger_ratio=CONTEXT_PRUNE_TRIGGER_RATIO,
            emergency_trigger_ratio=CONTEXT_EMERGENCY_TRIGGER_RATIO,
            refreshed_system_prompt=prompt if agent else None,
            prune_sync_note=self._build_pruned_context_sync_note() if agent else None,
            agent_name=agent.name if agent else None,
        )

        # Agentic loop with streaming
        max_iterations = 40
        max_tool_calls = 12
        max_tokens_per_task = 200000
        
        tool_calls_total = 0
        tokens_used_total = 0
        
        governor = ToolGovernor(max_consecutive=3, reflection_interval=3)

        for step in range(max_iterations):
            full_response = ""
            final_tool_calls = None

            status_manager.set_status(agent_id, AgentState.WORKING, f"Generating response (Step {step + 1}/{max_iterations})...")
            yield {"type": "agent_turn_start", "agent_name": agent_name}

            try:
                final_usage = None
                gateway = await get_gateway()
                async for chunk in gateway.stream(provider, messages, model_id, agent_id, self.session, tools=tool_schemas, temperature=temperature):
                    if chunk.error:
                        yield {"type": "error", "error": chunk.error}
                        break

                    if hasattr(chunk, "usage") and chunk.usage:
                        final_usage = chunk.usage
                        
                    if chunk.delta:
                        full_response += str(chunk.delta)
                        yield {"type": "chunk", "delta": chunk.delta}

                    if chunk.tool_calls:
                        if final_tool_calls is None:
                            final_tool_calls = []
                        final_tool_calls.extend(chunk.tool_calls)

                if final_usage:
                    tokens_used_total += getattr(final_usage, 'total_tokens', 0)
                    if getattr(agent, "id", None):
                        cost = self._calculate_cost(provider.name, model_id, final_usage)
                        if cost > 0:
                            agent.total_cost = getattr(agent, 'total_cost', 0) + cost
                            await self.session.commit()
                            await status_manager.emit_event({"type": "TOKEN_UPDATE", "agent_id": agent.id, "cost_added": cost, "total_cost": agent.total_cost})
                
                # Check Token Burn Limits
                if tokens_used_total >= max_tokens_per_task:
                    messages.append(ChatMessage(role="system", content="HARD LIMIT: Maximum token budget reached. You must immediately summarize your work, provide the best final answer you can, and STOP using tools."))

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
                        tool_calls_total += 1
                        func = tc.get("function", {})
                        tool_name = func.get("name", "")

                        status_manager.set_status(agent_id, AgentState.WORKING, f"Using tool: {tool_name}...")
                        yield {
                            "type": "tool_call",
                            "tool_call_id": tc.get("id", ""),
                            "tool_name": tool_name,
                            "tool_args": json.loads(func.get("arguments", "{}")),
                        }
                    
                    if tool_calls_total >= max_tool_calls:
                        messages.append(ChatMessage(role="system", content="HARD LIMIT: Maximum tool calls reached. You must immediately provide your final answer without any further tools."))
                        yield {"type": "chunk", "delta": "\n[System]: Hard limit reached. Summarizing and wrapping up.\n", "agent_name": "Governor"}

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

                    for tc in final_tool_calls:
                        func = tc.get("function", {})
                        t_name = func.get("name", "")
                        t_args = func.get("arguments", "{}")
                        intervention = governor.record_and_check(t_name, t_args)
                        if intervention:
                            messages.append(ChatMessage(role="user", content=intervention))
                            yield {"type": "chunk", "delta": "\n[System]: " + intervention + "\n", "agent_name": "Governor"}
                            break
                    
                    reflection = governor.should_reflect()
                    if reflection:
                        messages.append(ChatMessage(role="user", content=reflection))
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
        workflows_stmt = select(Workflow).where(Workflow.channel_id == conv.channel_id, Workflow.is_active)
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
            # Storm prevention: cap max simultaneous responding agents
            responding = mention_result.resolved[:MAX_SIMULTANEOUS_RESPONDING_AGENTS]
            if len(mention_result.resolved) > MAX_SIMULTANEOUS_RESPONDING_AGENTS:
                skipped = [r.agent_name for r in mention_result.resolved[MAX_SIMULTANEOUS_RESPONDING_AGENTS:]]
                yield {
                    "type": "system_notice",
                    "content": f"Storm prevention: limited to {MAX_SIMULTANEOUS_RESPONDING_AGENTS} agents. Skipped: {', '.join(skipped)}",
                }
            for resolved in responding:
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
        # Conversation depth check
        db_messages_check = await self.conv_service.get_messages(conversation_id)
        user_turns = sum(1 for m in db_messages_check if m.role == "user")
        if user_turns > MAX_CONVERSATION_DEPTH:
            yield {
                "type": "system_notice",
                "content": f"Conversation depth limit ({MAX_CONVERSATION_DEPTH}) reached. Starting fresh context.",
            }

        _provider_name, model_id, provider, fallback_warning = await self._resolve_provider_and_model(agent.model)

        # Use agent's own API key if set
        if agent.api_key:
            provider = self.providers.create_ephemeral(agent.provider, agent.api_key)

        # Fetch fresh history
        db_messages = await self.conv_service.get_messages(conversation_id)

        agent_msgs = []

        # 1. System Prompt
        agent_prompt = self._build_agent_prompt(agent)
        if fallback_warning:
            agent_prompt = (agent_prompt or "") + f"\n\n# Runtime Notice\n{fallback_warning}"
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

        # Inject Tier-2 semantic memories (Section 9 — Memory Retrieval)
        _cw_tokens = self._resolve_context_window_tokens(agent)
        agent_msgs = await self._build_context_with_memory(agent, agent_prompt, agent_msgs, _cw_tokens)

        # ── Inject relevant long-term memories ──
        try:
            from app.services.brain_service import AgentBrainService
            # Get last user message for semantic search context
            last_user_msg = ""
            for msg in reversed(db_messages):
                if msg.role == "user":
                    last_user_msg = msg.content[:500]
                    break
            if last_user_msg:
                relevant_memories = await AgentBrainService.retrieve_relevant_memories(agent.id, last_user_msg, limit=3)
                if relevant_memories:
                    memory_text = "\n".join(f"- {m[:200]}" for m in relevant_memories)
                    agent_msgs.append(ChatMessage(role="system", content=f"## Relevant Memories\n{memory_text}"))
        except Exception:
            pass  # Non-critical

        agent_msgs = await self.pruner.prune_context_if_needed(
            agent_msgs,
            self._resolve_context_window_tokens(agent),
            agent_id,
            soft_trigger_ratio=CONTEXT_SOFT_TRIGGER_RATIO,
            prune_trigger_ratio=CONTEXT_PRUNE_TRIGGER_RATIO,
            emergency_trigger_ratio=CONTEXT_EMERGENCY_TRIGGER_RATIO,
            refreshed_system_prompt=agent_prompt,
            prune_sync_note=self._build_pruned_context_sync_note(),
            agent_name=agent.name,
        )

        # Filter tools
        agent_tools = self._filter_tools_for_agent(agent, is_group_context=is_group)

        yield {"type": "agent_turn_start", "agent_name": agent.name, "model": agent.model}

        msg_record = None
        status_manager = await AgentStatusManager.get_instance()
        governor = ToolGovernor(max_consecutive=3, reflection_interval=3)

        # Agentic tool loop
        for step in range(max_tool_iters):
            full_response = ""
            final_tool_calls = None

            status_manager.set_status(agent_id, AgentState.WORKING, f"Generating response (Step {step + 1}/{max_tool_iters})...")

            try:
                final_usage = None
                gateway = await get_gateway()
                async for chunk in gateway.stream(provider, agent_msgs, model_id, agent_id, self.session, tools=agent_tools, temperature=temperature):
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
                    
                    # Tool Governor Reflection & Halts
                    for tr in tool_results:
                        await self.conv_service.add_message(
                            conversation_id, "tool", tr.content, tool_call_id=tr.tool_call_id,
                        )
                        agent_msgs.append(tr)
                        yield {"type": "tool_result", "tool_name": "", "tool_result": tr.content}

                    for tc in final_tool_calls:
                        func = tc.get("function", {})
                        t_name = func.get("name", "")
                        t_args = func.get("arguments", "{}")
                        intervention = governor.record_and_check(t_name, t_args)
                        if intervention:
                            agent_msgs.append(ChatMessage(role="user", content=intervention))
                            yield {"type": "chunk", "delta": "\n[System]: " + intervention + "\n", "agent_name": "Governor"}
                            break
                    
                    reflection = governor.should_reflect()
                    if reflection:
                        agent_msgs.append(ChatMessage(role="user", content=reflection))
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
        stmt = select(Agent).where(Agent.is_system, Agent.is_active)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_channel_agents(self, channel_id: str) -> list[Agent]:
        """Get all active agents assigned to a channel."""
        channel = await self.session.get(Channel, channel_id)
        if not channel:
            return []
        if channel.is_announcement:
            result = await self.session.execute(
                select(Agent).where(Agent.is_active).order_by(Agent.name)
            )
            return list(result.scalars().all())
        stmt = (
            select(Agent)
            .join(ChannelAgent, Agent.id == ChannelAgent.agent_id)
            .where(ChannelAgent.channel_id == channel_id, Agent.is_active)
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

        # 2. Create a fresh delegated-task conversation every time.
        # Reusing old conversations causes stale context and repeated refusal patterns.
        conversation = await self.conv_service.create(
            title=f"Task for {target_agent.name}",
            model=target_agent.model,
            agent_id=target_agent_id,
        )

        # 3. Build a well-structured delegation prompt
        delegation_prompt = (
            f"[Task delegated by {delegated_by}]\n\n"
            f"{prompt}\n\n"
            "Please complete this task thoroughly using your expertise and any tools available to you.\n"
            "Important execution rules:\n"
            "- Deliver concrete text output directly relevant to the task.\n"
            "- Do not reply with generic capability disclaimers (e.g., inability to do physical actions) unless the request truly requires physical-world execution.\n"
            "- If some input is missing, make reasonable assumptions, state them briefly, and still provide a best-effort result."
        )

        # 4. Run the full agentic loop (persists all messages in the agent's conversation)
        response_text = await self.chat(
            conversation_id=conversation.id,
            user_message=delegation_prompt,
            model_string=target_agent.model,
            temperature=0.7,
        )

        return response_text, conversation.id

    def _is_delegation_control_message(self, text: str) -> bool:
        lowered = (text or "").strip().lower()
        # Don't treat status/recall questions as new delegation commands.
        if self._is_delegation_contribution_query(lowered):
            return False
        triggers = ["delegate", "delegating", "assign", "distribute", "rerun", "re-run"]
        return any(t in lowered for t in triggers)

    def _is_delegation_contribution_query(self, text: str) -> bool:
        lowered = (text or "").strip().lower()
        keys = [
            "which all agents",
            "who all worked",
            "what did they contribute",
            "what all other agents worked",
            "who contributed",
            "taskflow memory",
            "which agents worked",
            "contributed",
            "did you delegate",
            "didnt you delegate",
            "didn't you delegate",
            "didnt you delegated",
            "didn't you delegated",
            "multiple agents",
            "all agents worked",
        ]
        return any(k in lowered for k in keys)

    async def _build_recent_delegation_summary(self, conversation_id: str) -> str | None:
        """Extract latest delegation contributions from stored conversation/task outputs."""
        db_messages = await self.conv_service.get_messages(conversation_id)
        if not db_messages:
            return None

        # 1) Prefer the most recent orchestrator summary message.
        for msg in reversed(db_messages):
            if msg.role != "assistant":
                continue
            content = (msg.content or "").strip()
            if content.startswith("I delegated your request and collected the results:"):
                return content

        # 2) Fallback: reconstruct from tool outputs from AgentDelegationTool flows.
        contributions: dict[str, str] = {}
        for msg in reversed(db_messages):
            if msg.role != "tool":
                continue
            content = (msg.content or "").strip()
            if "Task completed by" not in content:
                continue
            # Expected format: "... Task completed by <Agent>.\n\n**Response:**\n..."
            marker = "Task completed by "
            idx = content.find(marker)
            if idx < 0:
                continue
            tail = content[idx + len(marker):]
            agent_name = tail.split(".", 1)[0].strip()
            if not agent_name or agent_name in contributions:
                continue

            response = content
            resp_marker = "**Response:**"
            r_idx = content.find(resp_marker)
            if r_idx >= 0:
                response = content[r_idx + len(resp_marker):].strip()
            contributions[agent_name] = response

        if not contributions:
            return None

        parts = ["I found these stored delegation contributions:"]
        for agent_name, contribution in contributions.items():
            parts.append(f"\n{agent_name}:\n{contribution}")
        return "\n".join(parts)

    async def _maybe_handle_delegation_contribution_query(self, conversation_id: str, user_message: str) -> str | None:
        if not self._is_delegation_contribution_query(user_message):
            return None

        summary = await self._build_recent_delegation_summary(conversation_id)
        if summary:
            return summary

        return (
            "I could not find any stored delegation results in this conversation yet. "
            "Run a delegation request first, then I can list which agents worked and what each contributed."
        )

    def _extract_inline_task(self, text: str) -> str | None:
        raw = (text or "").strip()
        if not raw:
            return None
        lowered = raw.lower()
        if ":" in raw and self._is_delegation_control_message(lowered):
            _, rhs = raw.split(":", 1)
            candidate = rhs.strip()
            if len(candidate.split()) >= 4:
                return candidate
        return None

    async def _resolve_delegation_objective(self, conversation_id: str, user_message: str) -> str:
        """Resolve the concrete objective to delegate.

        For control-like prompts ("re-run the task", "delegate to team"), this
        uses the most recent substantive user request from conversation history.
        """
        inline_task = self._extract_inline_task(user_message)
        if inline_task:
            return inline_task

        if not self._is_delegation_control_message(user_message):
            return user_message.strip()

        db_messages = await self.conv_service.get_messages(conversation_id)
        for msg in reversed(db_messages):
            if msg.role != "user":
                continue
            candidate = (msg.content or "").strip()
            if not candidate or candidate == user_message.strip():
                continue
            if self._is_delegation_control_message(candidate):
                continue
            if len(candidate) < 12:
                continue
            return candidate

        return user_message.strip()

    def _build_specialist_subtask(self, agent: Agent, objective: str) -> str:
        name = (agent.name or "").lower()

        if "data analyst" in name:
            return (
                f"Primary objective: {objective}\n\n"
                "Your task: produce quantitative insights, trends, and concise metrics. "
                "Output 4-7 bullet points with numbers when possible, then add a short conclusion."
            )
        if "research" in name:
            return (
                f"Primary objective: {objective}\n\n"
                "Your task: gather and synthesize key facts, assumptions, and relevant context. "
                "Output 4-7 evidence-oriented bullet points and cite uncertainties clearly."
            )
        if "technical" in name:
            return (
                f"Primary objective: {objective}\n\n"
                "Your task: provide implementation approach, architecture, tooling, and execution steps. "
                "Output: architecture summary + 5 actionable technical steps."
            )
        if "content" in name:
            return (
                f"Primary objective: {objective}\n\n"
                "Your task: craft user-facing narrative/output that communicates the result clearly. "
                "Output: concise draft suitable to share with end users or stakeholders."
            )

        return (
            f"Primary objective: {objective}\n\n"
            "Your task: contribute from your specialization with concrete, actionable output. "
            "Keep it concise and specific."
        )

    async def _maybe_handle_system_delegation_request(
        self,
        conversation_id: str,
        user_message: str,
        system_agent: Agent,
    ) -> str | None:
        """Directly delegate when user explicitly requests delegation.

        This prevents the orchestrator from replying with "I can't delegate" in
        explicit delegation requests, especially in single-agent chats.
        """
        text = (user_message or "").strip()
        lowered = text.lower()
        if not self._is_delegation_control_message(lowered):
            return None

        objective = await self._resolve_delegation_objective(conversation_id, text)

        result = await self.session.execute(
            select(Agent).where(Agent.is_active, Agent.is_system == False).order_by(Agent.name)  # noqa: E712
        )
        candidates = list(result.scalars().all())
        if not candidates:
            return "I could not find active specialist agents to delegate this task to."

        selected: list[Agent] = []
        for ag in candidates:
            if ag.name.lower() in lowered:
                selected.append(ag)

        # If user requests team/multi-agent delegation but does not name agents,
        # pick a small cross-functional set.
        if not selected and ("team" in lowered or "different agents" in lowered or "multiple agents" in lowered):
            preferred = ["Research Specialist", "Data Analyst", "Technical Assistant", "Content Creator"]
            by_name = {c.name: c for c in candidates}
            selected = [by_name[n] for n in preferred if n in by_name]
            if not selected:
                selected = candidates[:3]

        if not selected:
            return None

        responses: list[str] = []
        for ag in selected:
            try:
                task_prompt = self._build_specialist_subtask(ag, objective)
                response_text, _conv_id = await self.delegate_to_agent(
                    target_agent_id=ag.id,
                    prompt=task_prompt,
                    delegated_by=system_agent.name,
                )
                responses.append(f"{ag.name}:\n{response_text}")
            except Exception as exc:
                responses.append(f"{ag.name}:\n[Delegation failed: {exc}]")

        if not responses:
            return None

        return "I delegated your request and collected the results:\n\n" + "\n\n".join(responses)


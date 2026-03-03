import json
from app.providers.base import ChatMessage
from app.services.agent_status import AgentStatusManager, AgentState
from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider

import tiktoken

class ContextPruner:
    """Service to compress older conversation history if token counts exceed limits."""
    
    def __init__(self, providers_manager):
        self.providers = providers_manager

    def estimate_tokens(self, messages: list[ChatMessage]) -> int:
        """Rough estimation of tokens using tiktoken (cl100k_base)."""
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback to character count / 4 if tiktoken fails
            return sum(len(m.content) for m in messages if m.content) // 4
            
        num_tokens = 0
        for message in messages:
            # Every message follows <im_start>{role/name}\n{content}<im_end>\n
            num_tokens += 4
            if message.content:
                num_tokens += len(encoding.encode(message.content))
            if message.tool_calls:
                num_tokens += len(encoding.encode(json.dumps(message.tool_calls)))
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens

    async def prune_context_if_needed(
        self, 
        messages: list[ChatMessage], 
        max_tokens: int,
        agent_id: str | None = None
    ) -> list[ChatMessage]:
        """
        If the token estimate of the messages exceeds max_tokens:
        Preserve the first message (system prompt) and the most recent 5 messages.
        Summarize the middle messages using a fast LLM.
        Replace those middle messages with the summary.
        """
        if len(messages) <= 6:
            return messages

        current_tokens = self.estimate_tokens(messages)
        if current_tokens <= max_tokens:
            return messages

        # We need to prune
        if agent_id:
            status_manager = await AgentStatusManager.get_instance()
            status_manager.set_status(agent_id, AgentState.WORKING, "Pruning context window...")

        # Find system message
        system_msgs = []
        middle_msgs = []
        recent_msgs = []
        
        # Keep the exact number of messages matching max 5 from end depending on structure
        keep_recent_count = 5
        
        idx = 0
        while idx < len(messages) and messages[idx].role == "system":
            system_msgs.append(messages[idx])
            idx += 1
            
        remaining = messages[idx:]
        if len(remaining) <= keep_recent_count:
            return messages
            
        middle_msgs = remaining[:-keep_recent_count]
        recent_msgs = remaining[-keep_recent_count:]
        
        # Summarize middle_msgs
        summary_prompt = "Please summarize the following conversation history concisely, preserving all key facts, entities, and tool outcomes. This summary will be used to inject context back into the AI assistant.\n\n"
        for m in middle_msgs:
            if m.content:
                summary_prompt += f"{m.role.upper()}: {m.content}\n"
            if m.tool_calls:
                summary_prompt += f"{m.role.upper()}: [Used tools: {json.dumps([tc.get('function', {}).get('name') for tc in m.tool_calls])}]\n"

        summary_msg = ChatMessage(role="user", content=summary_prompt)

        # Try to use a fast, cheap model for summarization. E.g. gpt-4o-mini or gemini-2.5-flash
        summary_text = ""
        provider = None
        model_id = None
        
        if "openai" in self.providers.providers:
            provider = self.providers.providers["openai"]
            model_id = "gpt-4o-mini"
        elif "gemini" in self.providers.providers:
            provider = self.providers.providers["gemini"]
            model_id = "gemini-2.5-flash"
        elif "anthropic" in self.providers.providers:
            provider = self.providers.providers["anthropic"]
            model_id = "claude-haiku-4-20250414"

        if provider and model_id:
            try:
                res = await provider.complete([summary_msg], model=model_id, temperature=0.3)
                summary_text = res.content
            except Exception as e:
                print(f"Context Pruning Error: {e}")
                summary_text = "Previous conversation omitted due to length."
        else:
            summary_text = "Previous conversation omitted due to length."

        # Reconstruct messages
        pruned_messages = system_msgs.copy()
        pruned_messages.append(ChatMessage(
            role="system",
            content=f"[CONTEXT PRUNED SUMMARY]:\n{summary_text}"
        ))
        pruned_messages.extend(recent_msgs)

        return pruned_messages

"""Multi-agent safe summarisation with summary drift protection.

Problems this module solves:

1. **Agent identity loss** — when a pruner summarises a multi-agent conversation,
   names and roles disappear from the summary, confusing the LLM on later turns.
   SummaryManager detects agent names and tells the summariser to preserve them.

2. **Summary drift** — if we summarise a message list that already contains a
   previous '[CONTEXT PRUNED SUMMARY]' block, we risk summarising a summary
   (quality degrades exponentially). SummaryManager splits the history into:
     - `frozen_summary`   the existing summary block — used verbatim as a base
     - `new_content`      messages written *after* the existing summary
   Then it asks the LLM to *extend* the frozen summary with the new content,
   rather than starting from scratch.

3. **Delegation history** — agent delegation chains are preserved in the summary
   as a structured block so the orchestrator can reconstruct the audit trail.
"""

import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.providers.base import ChatMessage

logger = logging.getLogger(__name__)

SUMMARY_MARKER = "[CONTEXT PRUNED SUMMARY]"
DELEGATION_MARKER = "[DELEGATION HISTORY]"


class SummaryManager:
    """Generates multi-agent aware, drift-protected conversation summaries."""

    def __init__(self, providers_manager):
        self.providers = providers_manager

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────

    async def summarize(
        self,
        messages: list["ChatMessage"],
        agent_name: str | None = None,
        delegation_history: list[str] | None = None,
    ) -> str:
        """Generate a context summary that is safe for multi-agent chains.

        Args:
            messages:           The messages to summarise (no system msgs please).
            agent_name:         Name of the *current* agent (preserved in output).
            delegation_history: List of agent names involved in the current chain.

        Returns:
            A plain-text summary string suitable for injection into a
            [CONTEXT PRUNED SUMMARY] system message.
        """
        if not messages:
            return "No prior conversation content."

        frozen_summary, new_messages = self._split_on_existing_summary(messages)
        agent_names = self._detect_agent_names(messages, agent_name, delegation_history)

        if frozen_summary and not new_messages:
            # Nothing new to add — return the existing summary verbatim.
            return frozen_summary

        prompt = self._build_prompt(
            new_messages,
            frozen_summary=frozen_summary,
            agent_names=agent_names,
            delegation_history=delegation_history,
        )

        summary_text = await self._call_llm(prompt)

        # Append delegation history block if present
        if delegation_history:
            chain_block = (
                f"\n\n{DELEGATION_MARKER}\n"
                + " → ".join(delegation_history)
            )
            summary_text = summary_text.rstrip() + chain_block

        return summary_text

    # ─────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────

    def _split_on_existing_summary(
        self, messages: list["ChatMessage"]
    ) -> tuple[str | None, list["ChatMessage"]]:
        """Split messages at the last existing SUMMARY_MARKER.

        Returns:
            (frozen_summary_text | None, new_messages_after_summary)
        """
        frozen_summary: str | None = None
        split_idx = 0

        for i, msg in enumerate(messages):
            if msg.content and SUMMARY_MARKER in msg.content:
                # Strip the marker header — keep the body
                body = msg.content.replace(f"{SUMMARY_MARKER}:\n", "").strip()
                frozen_summary = body
                split_idx = i + 1  # everything after this index is "new"

        return frozen_summary, messages[split_idx:]

    def _detect_agent_names(
        self,
        messages: list["ChatMessage"],
        current_agent: str | None,
        delegation_history: list[str] | None,
    ) -> list[str]:
        """Return a deduplicated list of agent names found in the conversation."""
        names: set[str] = set()

        if current_agent:
            names.add(current_agent)

        if delegation_history:
            names.update(delegation_history)

        # Detect "[AgentName]: ..." patterns in message content
        pattern = re.compile(r"^\[([A-Za-z0-9 _\-]+)\]:", re.MULTILINE)
        for msg in messages:
            if msg.content:
                for match in pattern.finditer(msg.content):
                    names.add(match.group(1).strip())

        return sorted(names)

    def _build_prompt(
        self,
        messages: list["ChatMessage"],
        frozen_summary: str | None,
        agent_names: list[str],
        delegation_history: list[str] | None,
    ) -> str:
        names_note = ""
        if agent_names:
            names_note = (
                f"\nIMPORTANT: The following agent names appear in this conversation: "
                f"{', '.join(agent_names)}. "
                "Preserve each agent's name in the summary so the chain of responsibility "
                "remains clear.\n"
            )

        deleg_note = ""
        if delegation_history and len(delegation_history) > 1:
            deleg_note = (
                f"\nThis is a multi-agent delegation chain: "
                f"{' → '.join(delegation_history)}. "
                "Summarise each agent's contribution separately.\n"
            )

        conversation_text = ""
        for msg in messages:
            content = msg.content or ""
            if msg.tool_calls:
                tools = [tc.get("function", {}).get("name", "?") for tc in msg.tool_calls]
                content += f" [tools: {', '.join(tools)}]"
            if content:
                conversation_text += f"{msg.role.upper()}: {content}\n"

        if frozen_summary:
            return (
                f"You are extending an existing conversation summary with new events.\n"
                f"{names_note}{deleg_note}\n"
                f"EXISTING SUMMARY:\n{frozen_summary}\n\n"
                f"NEW CONVERSATION EVENTS:\n{conversation_text}\n\n"
                "Write an updated summary that incorporates both. "
                "Do NOT repeat the existing summary verbatim — only carry forward "
                "relevant facts and add the new events. Be concise (max 300 words)."
            )
        else:
            return (
                f"Summarise this conversation for an AI context window.\n"
                f"{names_note}{deleg_note}\n"
                f"CONVERSATION:\n{conversation_text}\n\n"
                "Preserve key facts, decisions, tool outcomes, and agent contributions. "
                "Be concise (max 300 words). Plain text only."
            )

    async def _call_llm(self, prompt: str) -> str:
        """Call the cheapest available provider to generate the summary."""
        from app.providers.base import ChatMessage as CM

        provider_map = getattr(self.providers, "providers", {}) if self.providers else {}
        provider = model_id = None

        if "openai" in provider_map:
            provider, model_id = provider_map["openai"], "gpt-4o-mini"
        elif "gemini" in provider_map:
            provider, model_id = provider_map["gemini"], "gemini-2.5-flash"
        elif "anthropic" in provider_map:
            provider, model_id = provider_map["anthropic"], "claude-haiku-4-20250414"

        if provider is None:
            return "Previous conversation omitted due to length."

        try:
            resp = await provider.complete(
                [CM(role="user", content=prompt)],
                model=model_id,
                temperature=0.2,
            )
            return resp.content or "Previous conversation omitted due to length."
        except Exception as exc:
            logger.debug("SummaryManager LLM call failed: %s", exc)
            return "Previous conversation omitted due to length."

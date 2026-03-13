"""Context Pruner — three-threshold model with dynamic window and emergency path.

Threshold model (configurable, defaults match Phase-3 spec):

  soft      (60%)   Log a warning. No structural change. < 1 ms.
  active    (80%)   Summarise middle messages. Refresh system prompt.
  emergency (99%)   Hard truncate → keep system messages + last 3 turns.
                    Emit ERROR-level pruning event.

Dynamic recent window:
  Instead of a fixed 5-message keep count, the pruner calculates how many
  of the most-recent messages fit within RECENT_TOKEN_BUDGET (default 6 000).
  Floor: 3 messages.  Ceiling: 10 messages.

Multi-agent safe summaries:
  Delegates to SummaryManager so agent names and delegation history are
  preserved across summary boundaries (no identity loss).

Drift protection:
  SummaryManager detects existing [CONTEXT PRUNED SUMMARY] blocks and extends
  them rather than summarising a summary.

Observability:
  Every pruning decision emits a PruneEvent via pruning_events.emit().
"""

import json
import logging
import time
from typing import NamedTuple

import tiktoken

from app.providers.base import ChatMessage
from app.services.agent_status import AgentStatusManager, AgentState

logger = logging.getLogger(__name__)

# Default threshold ratios
SOFT_TRIGGER_RATIO      = 0.60   # warn only
ACTIVE_TRIGGER_RATIO    = 0.80   # summarise
EMERGENCY_TRIGGER_RATIO = 0.99   # hard truncate

# Dynamic recent window — token budget for the messages we always keep
RECENT_TOKEN_BUDGET = 6_000
RECENT_FLOOR        = 3    # always keep at least 3 recent messages
RECENT_CEILING      = 10   # never keep more than 10 for the "recent" window


class PruneDecision(NamedTuple):
    trigger: str          # "none" | "soft" | "active" | "emergency"
    current_tokens: int
    trigger_tokens: int   # whichever threshold was first crossed
    max_tokens: int


class ContextPruner:
    """Service to compress older conversation history if token counts exceed limits."""

    def __init__(self, providers_manager):
        self.providers = providers_manager

    # ─────────────────────────────────────────────────────────
    # Token estimation
    # ─────────────────────────────────────────────────────────

    def estimate_tokens(self, messages: list[ChatMessage]) -> int:
        """Rough token count using tiktoken (cl100k_base)."""
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            return sum(len(m.content) for m in messages if m.content) // 4

        num_tokens = 0
        for message in messages:
            num_tokens += 4  # per-message envelope
            if message.content:
                num_tokens += len(encoding.encode(message.content))
            if message.tool_calls:
                num_tokens += len(encoding.encode(json.dumps(message.tool_calls)))
        num_tokens += 2
        return num_tokens

    # ─────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────

    async def prune_context_if_needed(
        self,
        messages: list[ChatMessage],
        max_tokens: int,
        agent_id: str | None = None,
        # --- Three-threshold model ---
        soft_trigger_ratio: float = SOFT_TRIGGER_RATIO,
        prune_trigger_ratio: float = ACTIVE_TRIGGER_RATIO,
        emergency_trigger_ratio: float = EMERGENCY_TRIGGER_RATIO,
        # --- Refresh hooks ---
        refreshed_system_prompt: str | None = None,
        prune_sync_note: str | None = None,
        # --- Multi-agent context ---
        agent_name: str | None = None,
        delegation_history: list[str] | None = None,
    ) -> list[ChatMessage]:
        """Prune the context window according to the three-threshold model.

        Backward-compatible: callers that only pass `prune_trigger_ratio` still
        work correctly — they just won't have soft/emergency paths unless they
        explicitly override the other ratios.

        Performance contract:
          - Detection + assembly path: < 10 ms (synchronous).
          - Summary generation:  async, can exceed 10 ms (returned as part of
            the awaited result, but measured separately in PruneEvent.elapsed_ms).
        """
        if len(messages) <= 4:
            return messages

        t_start = time.monotonic()
        tokens_before = self.estimate_tokens(messages)
        decision = self._decide(tokens_before, max_tokens,
                                soft_trigger_ratio, prune_trigger_ratio,
                                emergency_trigger_ratio)

        if decision.trigger == "none":
            return messages

        # ── soft warning — update status, no structural change ──────────
        if decision.trigger == "soft":
            if agent_id:
                try:
                    sm = await AgentStatusManager.get_instance()
                    sm.set_status(
                        agent_id, AgentState.WORKING,
                        f"Context at {int(soft_trigger_ratio*100)}% capacity "
                        f"({tokens_before}/{max_tokens} tokens). Will prune soon.",
                    )
                except Exception:
                    pass
            from app.services.pruning_events import PruneEvent, emit as emit_event
            emit_event(PruneEvent(
                agent_id=agent_id or "?",
                trigger_type="soft",
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_before=len(messages),
                messages_after=len(messages),
                elapsed_ms=(time.monotonic() - t_start) * 1000,
            ))
            return messages

        # ── set status to WORKING ────────────────────────────────────────
        if agent_id:
            try:
                sm = await AgentStatusManager.get_instance()
                sm.set_status(
                    agent_id, AgentState.WORKING,
                    f"Pruning context ({decision.trigger}) "
                    f"{tokens_before}/{max_tokens} tokens…",
                )
            except Exception:
                pass

        # ── emergency hard truncate ──────────────────────────────────────
        if decision.trigger == "emergency":
            result = self._emergency_truncate(messages, refreshed_system_prompt, prune_sync_note)
            tokens_after = self.estimate_tokens(result)
            elapsed = (time.monotonic() - t_start) * 1000

            from app.services.pruning_events import PruneEvent, emit as emit_event
            emit_event(PruneEvent(
                agent_id=agent_id or "?",
                trigger_type="emergency",
                tokens_before=tokens_before,
                tokens_after=tokens_after,
                messages_before=len(messages),
                messages_after=len(result),
                emergency_triggered=True,
                elapsed_ms=elapsed,
            ))
            logger.error(
                "EMERGENCY PRUNE agent=%s tokens=%d->%d",
                agent_id, tokens_before, tokens_after,
            )
            return result

        # ── active prune — summarise middle messages ─────────────────────
        result, summary_tokens = await self._active_prune(
            messages,
            refreshed_system_prompt=refreshed_system_prompt,
            prune_sync_note=prune_sync_note,
            agent_name=agent_name,
            delegation_history=delegation_history,
        )
        tokens_after = self.estimate_tokens(result)
        elapsed = (time.monotonic() - t_start) * 1000

        from app.services.pruning_events import PruneEvent, emit as emit_event
        emit_event(PruneEvent(
            agent_id=agent_id or "?",
            trigger_type="active",
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            messages_before=len(messages),
            messages_after=len(result),
            summary_token_size=summary_tokens,
            elapsed_ms=elapsed,
        ))
        return result

    # ─────────────────────────────────────────────────────────
    # Threshold decision (< 1 ms, no I/O)
    # ─────────────────────────────────────────────────────────

    def _decide(
        self,
        current_tokens: int,
        max_tokens: int,
        soft_ratio: float,
        active_ratio: float,
        emergency_ratio: float,
    ) -> PruneDecision:
        emergency_t = int(max_tokens * emergency_ratio)
        active_t    = int(max_tokens * active_ratio)
        soft_t      = int(max_tokens * soft_ratio)

        if current_tokens >= emergency_t:
            return PruneDecision("emergency", current_tokens, emergency_t, max_tokens)
        if current_tokens >= active_t:
            return PruneDecision("active", current_tokens, active_t, max_tokens)
        if current_tokens >= soft_t:
            return PruneDecision("soft", current_tokens, soft_t, max_tokens)
        return PruneDecision("none", current_tokens, 0, max_tokens)

    # ─────────────────────────────────────────────────────────
    # Dynamic recent window
    # ─────────────────────────────────────────────────────────

    def _calculate_keep_recent(self, messages: list[ChatMessage]) -> int:
        """Return how many trailing messages fit within RECENT_TOKEN_BUDGET.

        Always between RECENT_FLOOR and RECENT_CEILING.
        """
        kept = 0
        budget_used = 0
        for msg in reversed(messages):
            msg_tokens = self.estimate_tokens([msg])
            if budget_used + msg_tokens > RECENT_TOKEN_BUDGET and kept >= RECENT_FLOOR:
                break
            budget_used += msg_tokens
            kept += 1
            if kept >= RECENT_CEILING:
                break
        return max(RECENT_FLOOR, kept)

    # ─────────────────────────────────────────────────────────
    # Active prune (summarise middle)
    # ─────────────────────────────────────────────────────────

    async def _active_prune(
        self,
        messages: list[ChatMessage],
        refreshed_system_prompt: str | None,
        prune_sync_note: str | None,
        agent_name: str | None,
        delegation_history: list[str] | None,
    ) -> tuple[list[ChatMessage], int]:
        """Summarise the middle messages and return the pruned list.

        Returns (pruned_messages, summary_token_count).
        """
        # Separate system messages from conversation turns
        system_msgs: list[ChatMessage] = []
        remaining: list[ChatMessage] = []
        idx = 0
        while idx < len(messages) and messages[idx].role == "system":
            system_msgs.append(messages[idx])
            idx += 1
        remaining = messages[idx:]

        # Refresh the first system message if a new prompt was supplied
        if refreshed_system_prompt:
            if system_msgs:
                system_msgs[0] = ChatMessage(role="system", content=refreshed_system_prompt)
            else:
                system_msgs.append(ChatMessage(role="system", content=refreshed_system_prompt))

        if prune_sync_note:
            system_msgs.append(ChatMessage(role="system", content=prune_sync_note))

        # Dynamic window: how many recent messages to keep
        keep_recent = self._calculate_keep_recent(remaining)

        if len(remaining) <= keep_recent:
            # Nothing to prune after accounting for the recent window
            return messages, 0

        middle_msgs = remaining[:-keep_recent]
        recent_msgs = remaining[-keep_recent:]

        # Summarise using SummaryManager (multi-agent safe, drift-protected)
        from app.services.summary_manager import SummaryManager
        mgr = SummaryManager(self.providers)
        summary_text = await mgr.summarize(
            middle_msgs,
            agent_name=agent_name,
            delegation_history=delegation_history,
        )

        summary_tokens = self.estimate_tokens(
            [ChatMessage(role="system", content=summary_text)]
        )

        pruned: list[ChatMessage] = system_msgs.copy()
        pruned.append(ChatMessage(
            role="system",
            content=f"[CONTEXT PRUNED SUMMARY]:\n{summary_text}",
        ))
        pruned.extend(recent_msgs)
        return pruned, summary_tokens

    # ─────────────────────────────────────────────────────────
    # Emergency hard truncate
    # ─────────────────────────────────────────────────────────

    def _emergency_truncate(
        self,
        messages: list[ChatMessage],
        refreshed_system_prompt: str | None,
        prune_sync_note: str | None,
    ) -> list[ChatMessage]:
        """Keep system messages + last 3 conversation turns. No LLM call."""
        system_msgs: list[ChatMessage] = []
        turns: list[ChatMessage] = []
        idx = 0
        while idx < len(messages) and messages[idx].role == "system":
            system_msgs.append(messages[idx])
            idx += 1
        turns = messages[idx:]

        if refreshed_system_prompt and system_msgs:
            system_msgs[0] = ChatMessage(role="system", content=refreshed_system_prompt)

        result = system_msgs.copy()
        if prune_sync_note:
            result.append(ChatMessage(role="system", content=prune_sync_note))

        result.append(ChatMessage(
            role="system",
            content="[EMERGENCY CONTEXT TRUNCATION]: Earlier conversation history was "
                    "dropped to fit the context window. Only the most recent messages are shown.",
        ))
        result.extend(turns[-3:])   # keep last 3 turns
        return result

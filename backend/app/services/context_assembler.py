"""Context Assembler — builds the layered context window.

Separates the LLM context into distinct semantic layers so each can be
selectively refreshed, token-budgeted, or replaced during pruning without
touching other layers:

  Layer 1  System Prompt          (authoritative, always preserved)
  Layer 2  Semantic Memory        (Tier-2 facts — injected when available)
  Layer 3  Task State             (live delegation / workflow state — injected when available)
  Layer 4  Conversation turns     (user / assistant / tool messages)
    └── [CONTEXT PRUNED SUMMARY]  (replaces the oldest turns after pruning)
    └── Recent messages           (dynamic window — last N messages that fit)

Usage in chat_service.py (drop-in enhancement):

    from app.services.context_assembler import ContextAssembler

    assembler = ContextAssembler()
    messages = assembler.build(
        system_prompt=prompt,
        messages=messages,
        task_state=current_task_state,  # optional
        semantic_memory=memory_block,   # optional, from MemoryCompactor.retrieve_for_context()
    )
    messages = await self.pruner.prune_context_if_needed(messages, ...)
"""

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.providers.base import ChatMessage

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class TaskState:
    """Snapshot of active task / delegation state for context injection."""
    task_id: str | None = None
    status: str | None = None             # QUEUED | RUNNING | WAITING_TOOL | WAITING_CHILD | COMPLETED | FAILED | TIMED_OUT | CANCELED | DLQ
    progress: int = 0                     # 0-100
    goal: str | None = None
    delegated_agents: list[str] | None = None   # names of sub-agents currently active
    workflow_state: str | None = None     # e.g. "step 2/5 — data extraction"
    chain_id: str | None = None

    @classmethod
    def from_task(cls, task) -> "TaskState":
        """Construct from a Task ORM object."""
        return cls(
            task_id=getattr(task, "id", None),
            status=getattr(task, "status", None),
            progress=getattr(task, "progress_percent", 0) or 0,
            goal=getattr(task, "goal", None),
        )


class ContextAssembler:
    """Assembles the layered context window for LLM calls.

    All methods are synchronous (no I/O) and execute in < 1 ms.
    They only manipulate in-memory ChatMessage lists.
    """

    # ─────────────────────────────────────────────────────────
    # Full build
    # ─────────────────────────────────────────────────────────

    def build(
        self,
        system_prompt: str,
        messages: list[ChatMessage],
        task_state: TaskState | dict | None = None,
        semantic_memory: str | None = None,
    ) -> list[ChatMessage]:
        """Return a fully-layered message list.

        Input `messages` should already have the system prompt as messages[0]
        (as produced by `_db_messages_to_chat`).  This method *replaces* that
        first system message with `system_prompt` and injects the optional
        layers after it.

        If the first message is not a system message, the system prompt is
        prepended.
        """
        # Separate the existing system messages from the turns
        sys_msgs: list[ChatMessage] = []
        turn_msgs: list[ChatMessage] = []
        for msg in messages:
            if msg.role == "system" and not turn_msgs:
                sys_msgs.append(msg)
            else:
                turn_msgs.append(msg)

        result: list[ChatMessage] = []

        # Layer 1 — canonical system prompt (replaces whatever was first)
        result.append(ChatMessage(role="system", content=system_prompt))

        # Carry over any *additional* system messages (e.g. skill instructions,
        # prune-sync notes) that were already in the list
        for extra in sys_msgs[1:]:
            result.append(extra)

        # Layer 2 — Semantic memory (Tier-2 knowledge injection)
        if semantic_memory and semantic_memory.strip():
            result.append(ChatMessage(role="system", content=semantic_memory.strip()))

        # Layer 3 — Task state injection
        if task_state is not None:
            task_block = self.format_task_state(task_state)
            if task_block:
                result.append(ChatMessage(role="system", content=task_block))

        # Layer 4 — Conversation turns (user / assistant / tool)
        result.extend(turn_msgs)

        return result

    # ─────────────────────────────────────────────────────────
    # Targeted injection helpers
    # ─────────────────────────────────────────────────────────

    def inject_task_state(
        self,
        messages: list[ChatMessage],
        task_state: TaskState | dict,
    ) -> list[ChatMessage]:
        """Insert a task-state system message right after the first system message."""
        block = self.format_task_state(task_state)
        if not block:
            return messages
        task_msg = ChatMessage(role="system", content=block)
        if messages and messages[0].role == "system":
            return [messages[0], task_msg] + messages[1:]
        return [task_msg] + messages

    def inject_semantic_memory(
        self,
        messages: list[ChatMessage],
        memory_block: str,
    ) -> list[ChatMessage]:
        """Insert a semantic memory system message right after the first system message."""
        if not memory_block or not memory_block.strip():
            return messages
        mem_msg = ChatMessage(role="system", content=memory_block.strip())
        if messages and messages[0].role == "system":
            return [messages[0], mem_msg] + messages[1:]
        return [mem_msg] + messages

    # ─────────────────────────────────────────────────────────
    # Formatting
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def format_task_state(task_state: TaskState | dict | None) -> str:
        """Return a concise task-state injection block (or empty string)."""
        if task_state is None:
            return ""

        # Accept either a TaskState dataclass or a plain dict
        if isinstance(task_state, dict):
            ts = TaskState(
                task_id=task_state.get("task_id"),
                status=task_state.get("status"),
                progress=task_state.get("progress", 0) or 0,
                goal=task_state.get("goal"),
                delegated_agents=task_state.get("delegated_agents"),
                workflow_state=task_state.get("workflow_state"),
                chain_id=task_state.get("chain_id"),
            )
        else:
            ts = task_state

        lines: list[str] = ["[TASK STATE]"]

        if ts.task_id:
            lines.append(f"task_id: {ts.task_id}")
        if ts.status:
            lines.append(f"status: {ts.status}")
        if ts.progress:
            lines.append(f"progress: {ts.progress}%")
        if ts.goal:
            lines.append(f"goal: {ts.goal[:200]}")
        if ts.delegated_agents:
            lines.append(f"delegated_agents: {', '.join(ts.delegated_agents)}")
        if ts.workflow_state:
            lines.append(f"workflow_state: {ts.workflow_state}")
        if ts.chain_id:
            lines.append(f"chain_id: {ts.chain_id}")

        if len(lines) == 1:
            return ""  # nothing useful
        return "\n".join(lines)

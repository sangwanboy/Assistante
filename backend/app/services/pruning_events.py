"""Structured event logging for context pruning operations.

Every pruning action — soft warning, active prune, or emergency truncation —
emits a PruneEvent that is logged to the dedicated 'pruning_events' logger.

Consumers can attach a handler to that logger to push events to:
  - structured JSON logs
  - Redis pub/sub (channel: orchestrator:prune_events)
  - a frontend WebSocket stream
  - a Prometheus counter (future)

Performance contract: emit() executes in < 1 ms (no I/O).
"""

import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Literal

logger = logging.getLogger("pruning_events")

PruneTriggerType = Literal["soft", "active", "emergency", "none"]

# Module-level counters for observability metrics (Section 14).
# Lightweight in-process aggregation — no I/O, resets on restart.
_counters: dict[str, int] = {
    "soft": 0,
    "active": 0,
    "emergency": 0,
    "total": 0,
}


def get_counters() -> dict[str, int]:
    """Return a snapshot of the current pruning event counters."""
    return dict(_counters)


@dataclass
class PruneEvent:
    """Immutable record of a single pruning decision."""
    agent_id: str
    trigger_type: PruneTriggerType         # soft | active | emergency | none
    tokens_before: int
    tokens_after: int
    messages_before: int
    messages_after: int
    summary_token_size: int = 0            # tokens in the generated summary block
    emergency_triggered: bool = False
    elapsed_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def reduction_pct(self) -> float:
        if self.tokens_before == 0:
            return 0.0
        return round((1 - self.tokens_after / self.tokens_before) * 100, 1)


def emit(event: PruneEvent) -> None:
    """Emit a structured pruning event to the dedicated logger.

    Log level:
      emergency → ERROR
      active    → INFO
      soft      → DEBUG
      none      → DEBUG (no-op path, rarely called)
    """
    # Increment in-process counters for /system/metrics
    if event.trigger_type in _counters:
        _counters[event.trigger_type] += 1
    _counters["total"] += 1

    payload = asdict(event)
    payload["reduction_pct"] = event.reduction_pct

    if event.emergency_triggered:
        logger.error(
            "PRUNE emergency agent=%s tokens=%d->%d msgs=%d->%d elapsed=%.1fms",
            event.agent_id,
            event.tokens_before,
            event.tokens_after,
            event.messages_before,
            event.messages_after,
            event.elapsed_ms,
            extra={"prune_event": payload},
        )
    elif event.trigger_type == "active":
        logger.info(
            "PRUNE active agent=%s tokens=%d->%d (-%s%%) msgs=%d->%d summary=%dtok elapsed=%.1fms",
            event.agent_id,
            event.tokens_before,
            event.tokens_after,
            event.reduction_pct,
            event.messages_before,
            event.messages_after,
            event.summary_token_size,
            event.elapsed_ms,
            extra={"prune_event": payload},
        )
    elif event.trigger_type == "soft":
        logger.debug(
            "PRUNE soft-warn agent=%s tokens=%d messages=%d",
            event.agent_id,
            event.tokens_before,
            event.messages_before,
            extra={"prune_event": payload},
        )

"""Communication channel monitor for the Master Heartbeat system.

Monitors channels, mentions, announcements, and message queue health
to ensure reliable agent communication.
"""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PendingMention:
    """Tracks an unacknowledged @mention."""
    target_agent_id: str
    channel_id: str | None
    conversation_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    resend_count: int = 0


@dataclass
class PendingAnnouncement:
    """Tracks a broadcast announcement awaiting acknowledgements."""
    announcement_id: str
    target_agent_ids: list[str] = field(default_factory=list)
    acknowledged_agent_ids: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CommunicationMonitor:
    """Monitors agent communication channels for health and responsiveness.
    
    Called by MasterHeartbeat every 5 seconds.
    
    Sub-monitors:
    1. Channel Monitor — detect unresponded pending mentions
    2. Mention Monitor — detect unacknowledged @mentions (5s timeout)
    3. Announcement Monitor — detect incomplete acknowledgements
    4. Message Queue Monitor — detect queue latency/stalls
    """

    MENTION_ACK_TIMEOUT = 5  # seconds before resending
    MENTION_ESCALATE_TIMEOUT = 15  # seconds before escalating to System Agent
    MENTION_MAX_RESENDS = 3
    ANNOUNCEMENT_ACK_TIMEOUT = 30  # seconds

    def __init__(self):
        self._pending_mentions: dict[str, PendingMention] = {}
        self._pending_announcements: dict[str, PendingAnnouncement] = {}
        self._queue_metrics = {
            "pending_messages": 0,
            "processing_rate": 0.0,
            "queue_latency_ms": 0,
        }
        self._messages_processed = 0
        self._last_queue_check = datetime.now(timezone.utc)

    # ── Mention Tracking ──

    def track_mention(self, mention_id: str, target_agent_id: str,
                      conversation_id: str, channel_id: str | None = None):
        """Register a new @mention that needs acknowledgement."""
        self._pending_mentions[mention_id] = PendingMention(
            target_agent_id=target_agent_id,
            channel_id=channel_id,
            conversation_id=conversation_id,
        )

    def acknowledge_mention(self, mention_id: str):
        """Mark a mention as acknowledged (agent responded)."""
        if mention_id in self._pending_mentions:
            self._pending_mentions[mention_id].acknowledged = True
            del self._pending_mentions[mention_id]

    def acknowledge_agent_activity(self, agent_id: str):
        """Mark all pending mentions for an agent as acknowledged."""
        keys_to_remove = []
        for key, mention in self._pending_mentions.items():
            if mention.target_agent_id == agent_id:
                mention.acknowledged = True
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._pending_mentions[key]

    # ── Announcement Tracking ──

    def track_announcement(self, announcement_id: str, target_agent_ids: list[str]):
        """Register a broadcast announcement."""
        self._pending_announcements[announcement_id] = PendingAnnouncement(
            announcement_id=announcement_id,
            target_agent_ids=target_agent_ids,
        )

    def acknowledge_announcement(self, announcement_id: str, agent_id: str):
        """Mark an agent's acknowledgement of an announcement."""
        if announcement_id in self._pending_announcements:
            ann = self._pending_announcements[announcement_id]
            if agent_id not in ann.acknowledged_agent_ids:
                ann.acknowledged_agent_ids.append(agent_id)
            # Remove if all acknowledged
            if set(ann.acknowledged_agent_ids) >= set(ann.target_agent_ids):
                del self._pending_announcements[announcement_id]

    # ── Queue Metrics ──

    def record_message_processed(self):
        """Called when a message is processed to track throughput."""
        self._messages_processed += 1

    def update_queue_depth(self, pending: int):
        """Update the current queue depth."""
        self._queue_metrics["pending_messages"] = pending

    # ── Monitor Check ──

    async def check_communication(self) -> dict:
        """Run all communication sub-monitors. Returns metrics dict."""
        now = datetime.now(timezone.utc)

        # ── Mention Monitor ──
        unacked_mentions = 0
        resent_mentions = 0
        escalated_mentions = 0
        mentions_to_remove = []

        for mention_id, mention in list(self._pending_mentions.items()):
            if mention.acknowledged:
                mentions_to_remove.append(mention_id)
                continue

            elapsed = (now - mention.timestamp).total_seconds()

            if elapsed > self.MENTION_ESCALATE_TIMEOUT:
                # Escalate to System Agent
                escalated_mentions += 1
                mentions_to_remove.append(mention_id)
                logger.warning(
                    "[CommMonitor] Mention to agent %s unacknowledged for %.0fs. Escalating.",
                    mention.target_agent_id, elapsed
                )
                # Wake the agent
                try:
                    from app.services.agent_status import AgentStatusManager, AgentState
                    status_mgr = await AgentStatusManager.get_instance()
                    current = status_mgr.get_status(mention.target_agent_id)
                    if current.get("state") in (AgentState.OFFLINE, AgentState.STALLED):
                        status_mgr.set_status(mention.target_agent_id, AgentState.INITIALIZING)
                except Exception:
                    pass

            elif elapsed > self.MENTION_ACK_TIMEOUT and mention.resend_count < self.MENTION_MAX_RESENDS:
                # Resend notification
                mention.resend_count += 1
                resent_mentions += 1
                unacked_mentions += 1
                logger.debug(
                    "[CommMonitor] Resending mention to agent %s (attempt %d)",
                    mention.target_agent_id, mention.resend_count
                )
            else:
                unacked_mentions += 1

        for mid in mentions_to_remove:
            self._pending_mentions.pop(mid, None)

        # ── Announcement Monitor ──
        incomplete_announcements = 0
        announcements_to_remove = []

        for ann_id, ann in list(self._pending_announcements.items()):
            elapsed = (now - ann.timestamp).total_seconds()
            ack_count = len(ann.acknowledged_agent_ids)
            target_count = len(ann.target_agent_ids)

            if ack_count < target_count:
                if elapsed > self.ANNOUNCEMENT_ACK_TIMEOUT:
                    incomplete_announcements += 1
                    logger.warning(
                        "[CommMonitor] Announcement %s incomplete: %d/%d acknowledged after %.0fs",
                        ann_id, ack_count, target_count, elapsed
                    )
                    # Retry missing acknowledgements, then escalate
                    missing_agents = set(ann.target_agent_ids) - set(ann.acknowledged_agent_ids)
                    if elapsed < self.ANNOUNCEMENT_ACK_TIMEOUT * 3:
                        # Retry: re-notify unacknowledged agents
                        logger.info(
                            "[CommMonitor] Retrying announcement %s for %d unacknowledged agents",
                            ann_id, len(missing_agents)
                        )
                    else:
                        # Escalate to System Agent after 3x timeout
                        logger.warning(
                            "[CommMonitor] Escalating announcement %s: %d agents never acknowledged",
                            ann_id, len(missing_agents)
                        )
                        announcements_to_remove.append(ann_id)

        for aid in announcements_to_remove:
            self._pending_announcements.pop(aid, None)

        # ── Queue Monitor ──
        elapsed_since_check = max((now - self._last_queue_check).total_seconds(), 1)
        processing_rate = self._messages_processed / elapsed_since_check
        self._queue_metrics["processing_rate"] = round(processing_rate, 2)
        self._messages_processed = 0
        self._last_queue_check = now

        queue_stalled = (
            self._queue_metrics["pending_messages"] > 10
            and processing_rate < 0.1
        )
        if queue_stalled:
            logger.warning(
                "[CommMonitor] Message queue appears stalled: %d pending, rate=%.2f/s",
                self._queue_metrics["pending_messages"], processing_rate
            )

        return {
            "pending_mentions": unacked_mentions,
            "resent_mentions": resent_mentions,
            "escalated_mentions": escalated_mentions,
            "incomplete_announcements": incomplete_announcements,
            "queue_pending": self._queue_metrics["pending_messages"],
            "queue_rate": processing_rate,
            "queue_stalled": queue_stalled,
        }

    def get_announcement_status(self, announcement_id: str) -> dict | None:
        """Get current status of a tracked announcement."""
        ann = self._pending_announcements.get(announcement_id)
        if not ann:
            return None
        return {
            "announcement_id": ann.announcement_id,
            "target_count": len(ann.target_agent_ids),
            "acknowledged_count": len(ann.acknowledged_agent_ids),
            "missing": list(set(ann.target_agent_ids) - set(ann.acknowledged_agent_ids)),
            "elapsed_seconds": (datetime.now(timezone.utc) - ann.timestamp).total_seconds(),
        }

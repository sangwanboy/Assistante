"""Slack Bot adapter using Slack Events API webhook (FastAPI endpoint) + Web API for sending."""
import logging
import httpx

from app.services.omnichannel.base import BaseChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"


class SlackAdapter(BaseChannelAdapter):
    """Slack adapter receives events via webhook POST /api/integrations/slack/events.
    The OmnichannelManager routes those payloads here via handle_webhook().
    """

    @property
    def platform(self) -> str:
        return "slack"

    async def start(self, on_message) -> None:
        self._on_message = on_message
        logger.info("Slack adapter ready (waiting for webhook events)")

    async def stop(self) -> None:
        logger.info("Slack adapter stopped")

    async def send(self, msg: OutgoingMessage) -> None:
        token = self.config.get("bot_token", "")
        payload = {"channel": msg.external_chat_id, "text": msg.text}
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{SLACK_API}/chat.postMessage",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )

    async def handle_webhook(self, payload: dict) -> None:
        """Called by the integrations API when Slack sends an event."""
        event = payload.get("event", {})
        if event.get("type") == "message" and not event.get("bot_id"):
            incoming = IncomingMessage(
                platform="slack",
                external_user_id=event.get("user", ""),
                external_chat_id=event.get("channel", ""),
                username=event.get("user", "slack_user"),
                text=event.get("text", ""),
                integration_id=self.integration_id,
                raw=payload,
            )
            await self._on_message(incoming)

"""OmnichannelManager: orchestrates all platform adapters and routes
incoming messages into Assitance conversations/agents.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Awaitable

from app.services.omnichannel.base import BaseChannelAdapter, IncomingMessage, OutgoingMessage
from app.services.omnichannel.telegram_adapter import TelegramAdapter
from app.services.omnichannel.discord_adapter import DiscordAdapter
from app.services.omnichannel.slack_adapter import SlackAdapter
from app.services.omnichannel.whatsapp_adapter import WhatsAppAdapter
from app.services.omnichannel.whatsapp_web_adapter import WhatsAppWebAdapter

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

ADAPTER_MAP: dict[str, type[BaseChannelAdapter]] = {
    "telegram": TelegramAdapter,
    "discord": DiscordAdapter,
    "slack": SlackAdapter,
    "whatsapp": WhatsAppAdapter,
    "whatsapp_web": WhatsAppWebAdapter,
}


class OmnichannelManager:
    """Singleton that holds live adapter instances and dispatches messages."""

    _instance: OmnichannelManager | None = None

    def __init__(self) -> None:
        self._adapters: dict[str, BaseChannelAdapter] = {}  # integration_id -> adapter
        # Callback set externally by main.py after chat infra is ready
        self._message_handler: Callable[[IncomingMessage], Awaitable[None]] | None = None

    @classmethod
    def get_instance(cls) -> "OmnichannelManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_message_handler(
        self, handler: Callable[[IncomingMessage], Awaitable[None]]
    ) -> None:
        self._message_handler = handler

    async def start_adapter(
        self, integration_id: str, platform: str, config: dict
    ) -> None:
        """Instantiate and start an adapter for an integration record."""
        cls = ADAPTER_MAP.get(platform)
        if cls is None:
            logger.warning("No adapter for platform '%s'", platform)
            return
        if integration_id in self._adapters:
            await self.stop_adapter(integration_id)
        adapter = cls(integration_id=integration_id, config=config)
        self._adapters[integration_id] = adapter
        await adapter.start(self._dispatch)
        logger.info("Started %s adapter for integration %s", platform, integration_id)

    async def stop_adapter(self, integration_id: str) -> None:
        adapter = self._adapters.pop(integration_id, None)
        if adapter:
            await adapter.stop()

    async def stop_all(self) -> None:
        for iid in list(self._adapters.keys()):
            await self.stop_adapter(iid)

    async def send(self, integration_id: str, chat_id: str, text: str) -> None:
        adapter = self._adapters.get(integration_id)
        if adapter is None:
            logger.warning("send called for unknown integration %s", integration_id)
            return
        msg = OutgoingMessage(
            platform=adapter.platform, external_chat_id=chat_id, text=text
        )
        await adapter.send(msg)

    async def handle_webhook(
        self, integration_id: str, payload: dict | None = None, form_data: dict | None = None
    ) -> None:
        """Route webhook payloads to the correct adapter (Slack, WhatsApp)."""
        adapter = self._adapters.get(integration_id)
        if adapter is None:
            logger.warning("Webhook for unknown integration %s", integration_id)
            return
        if hasattr(adapter, "handle_webhook"):
            if form_data is not None:
                await adapter.handle_webhook(form_data)  # type: ignore[arg-type]
            elif payload is not None:
                await adapter.handle_webhook(payload)  # type: ignore[arg-type]

    async def _dispatch(self, msg: IncomingMessage) -> None:
        """Route an IncomingMessage to the registered handler."""
        if self._message_handler is None:
            logger.warning("No message handler set; dropping message from %s", msg.platform)
            return
        try:
            await self._message_handler(msg)
        except Exception as exc:
            logger.error("Error handling omnichannel message: %s", exc, exc_info=True)

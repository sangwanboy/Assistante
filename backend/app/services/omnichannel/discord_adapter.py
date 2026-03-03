"""Discord Bot adapter using httpx + Gateway (simplified polling via REST for MVP)."""
import asyncio
import logging
import httpx

from app.services.omnichannel.base import BaseChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


class DiscordAdapter(BaseChannelAdapter):
    """Connects to Discord via REST polling on a specific channel (MVP).
    For production, replace with a proper Gateway WebSocket connection.
    """

    @property
    def platform(self) -> str:
        return "discord"

    def _headers(self) -> dict:
        return {"Authorization": f"Bot {self.config['bot_token']}"}

    async def start(self, on_message) -> None:
        self._running = True
        self._on_message = on_message
        self._last_message_id: str | None = None
        asyncio.create_task(self._poll_loop())
        logger.info("Discord adapter started (REST polling)")

    async def stop(self) -> None:
        self._running = False
        logger.info("Discord adapter stopped")

    async def send(self, msg: OutgoingMessage) -> None:
        url = f"{DISCORD_API}/channels/{msg.external_chat_id}/messages"
        payload: dict = {"content": msg.text}
        if msg.reply_to_message_id:
            payload["message_reference"] = {"message_id": msg.reply_to_message_id}
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload, headers=self._headers())

    async def _poll_loop(self) -> None:
        channel_id = self.config.get("channel_id")
        if not channel_id:
            logger.warning("Discord adapter: no channel_id configured, polling disabled")
            return
        while self._running:
            try:
                params: dict = {"limit": 10}
                if self._last_message_id:
                    params["after"] = self._last_message_id
                url = f"{DISCORD_API}/channels/{channel_id}/messages"
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(url, params=params, headers=self._headers())
                messages = resp.json()
                if isinstance(messages, list):
                    for m in reversed(messages):  # oldest first
                        if not m.get("author", {}).get("bot"):
                            self._last_message_id = m["id"]
                            author = m.get("author", {})
                            incoming = IncomingMessage(
                                platform="discord",
                                external_user_id=str(author.get("id", "")),
                                external_chat_id=channel_id,
                                username=author.get("username", "discord_user"),
                                text=m.get("content", ""),
                                integration_id=self.integration_id,
                                raw=m,
                            )
                            await self._on_message(incoming)
            except Exception as exc:
                logger.warning("Discord poll error: %s", exc)
            await asyncio.sleep(3)

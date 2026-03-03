"""Telegram Bot adapter using httpx long-polling (no external bot library required)."""
import asyncio
import logging
import httpx

from app.services.omnichannel.base import BaseChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class TelegramAdapter(BaseChannelAdapter):
    BASE = "https://api.telegram.org/bot{token}"

    @property
    def platform(self) -> str:
        return "telegram"

    def _url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.config['token']}/{method}"

    async def start(self, on_message) -> None:
        self._running = True
        self._on_message = on_message
        asyncio.create_task(self._poll_loop())
        logger.info("Telegram adapter started (long-polling)")

    async def stop(self) -> None:
        self._running = False
        logger.info("Telegram adapter stopped")

    async def send(self, msg: OutgoingMessage) -> None:
        payload = {"chat_id": msg.external_chat_id, "text": msg.text}
        if msg.reply_to_message_id:
            payload["reply_to_message_id"] = int(msg.reply_to_message_id)
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(self._url("sendMessage"), json=payload)

    async def _poll_loop(self) -> None:
        offset = 0
        async with httpx.AsyncClient(timeout=35) as client:
            while self._running:
                try:
                    resp = await client.get(
                        self._url("getUpdates"),
                        params={"timeout": 30, "offset": offset},
                    )
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        await self._handle_update(update)
                except Exception as exc:
                    logger.warning("Telegram poll error: %s", exc)
                    await asyncio.sleep(5)

    async def _handle_update(self, update: dict) -> None:
        msg = update.get("message") or update.get("channel_post")
        if not msg or "text" not in msg:
            return
        sender = msg.get("from", {})
        incoming = IncomingMessage(
            platform="telegram",
            external_user_id=str(sender.get("id", "unknown")),
            external_chat_id=str(msg["chat"]["id"]),
            username=sender.get("username") or sender.get("first_name", "telegram_user"),
            text=msg["text"],
            integration_id=self.integration_id,
            raw=update,
        )
        await self._on_message(incoming)

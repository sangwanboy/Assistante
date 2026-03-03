"""WhatsApp adapter stub using Twilio WhatsApp API (webhook-based)."""
import logging
import httpx

from app.services.omnichannel.base import BaseChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class WhatsAppAdapter(BaseChannelAdapter):
    """WhatsApp via Twilio.  Receives events via POST /api/integrations/whatsapp/events.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER in config.
    """

    @property
    def platform(self) -> str:
        return "whatsapp"

    async def start(self, on_message) -> None:
        self._on_message = on_message
        logger.info("WhatsApp adapter ready (waiting for Twilio webhook events)")

    async def stop(self) -> None:
        logger.info("WhatsApp adapter stopped")

    async def send(self, msg: OutgoingMessage) -> None:
        sid = self.config.get("account_sid", "")
        token = self.config.get("auth_token", "")
        from_number = self.config.get("from_number", "")
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                url,
                data={
                    "From": f"whatsapp:{from_number}",
                    "To": f"whatsapp:{msg.external_chat_id}",
                    "Body": msg.text,
                },
                auth=(sid, token),
            )

    async def handle_webhook(self, form_data: dict) -> None:
        """Called by the integrations API on Twilio form-encoded events."""
        text = form_data.get("Body", "")
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        if text:
            incoming = IncomingMessage(
                platform="whatsapp",
                external_user_id=from_number,
                external_chat_id=from_number,
                username=from_number,
                text=text,
                integration_id=self.integration_id,
                raw=form_data,
            )
            await self._on_message(incoming)

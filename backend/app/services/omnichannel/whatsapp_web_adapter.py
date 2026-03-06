"""WhatsApp Web adapter using the custom Node.js microservice."""
import logging
import httpx

from app.services.omnichannel.base import BaseChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

# The Node.js service is expected at this address
NODE_SERVICE_URL = "http://localhost:3001"

class WhatsAppWebAdapter(BaseChannelAdapter):
    """WhatsApp via whatsapp-web.js microservice.
    Receives events via POST /api/integrations/{id}/webhook/whatsapp_web.
    Config requires 'profile' name.
    """

    @property
    def platform(self) -> str:
        return "whatsapp_web"

    async def start(self, on_message) -> None:
        self._on_message = on_message
        profile = self.config.get("profile")
        if not profile:
            logger.error("WhatsAppWebAdapter: 'profile' not found in config")
            return

        # Tell Node service to connect this profile and associate it with this integrationId
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(
                    f"{NODE_SERVICE_URL}/api/whatsapp/connect",
                    json={
                        "profile": profile,
                        "integrationId": self.integration_id
                    }
                )
                logger.info("WhatsAppWebAdapter [%s] requested connection for profile %s", self.integration_id, profile)
            except Exception as exc:
                logger.error("WhatsAppWebAdapter [%s] failed to request connection: %s", self.integration_id, exc)

    async def stop(self) -> None:
        logger.info("WhatsAppWebAdapter [%s] stopped", self.integration_id)

    async def send(self, msg: OutgoingMessage) -> None:
        profile = self.config.get("profile")
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(
                    f"{NODE_SERVICE_URL}/api/whatsapp/send",
                    json={
                        "profile": profile,
                        "to": msg.external_chat_id,
                        "text": msg.text
                    }
                )
            except Exception as exc:
                logger.error("WhatsAppWebAdapter [%s] failed to send message: %s", self.integration_id, exc)

    async def handle_webhook(self, payload: dict) -> None:
        """Called by the integrations API on JSON events from Node service."""
        text = payload.get("text", "")
        from_id = payload.get("from", "")
        profile = payload.get("profile", "")
        
        if text and from_id:
            incoming = IncomingMessage(
                platform="whatsapp_web",
                external_user_id=from_id,
                external_chat_id=from_id,
                username=from_id, # Can use pushname if passed from Node
                text=text,
                integration_id=self.integration_id,
                raw=payload,
            )
            await self._on_message(incoming)

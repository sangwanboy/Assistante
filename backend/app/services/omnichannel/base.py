"""Base class for all omnichannel adapters."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class IncomingMessage:
    """Normalized inbound message from any external channel."""
    platform: str          # "telegram", "discord", "slack", "whatsapp"
    external_user_id: str  # Platform-specific user ID
    external_chat_id: str  # Platform-specific chat/channel ID
    username: str          # Display name of the sender
    text: str              # Message content
    integration_id: str    # DB ID of the ExternalIntegration record
    raw: dict              # Original payload for platform-specific use


@dataclass
class OutgoingMessage:
    """Normalized outbound reply to an external channel."""
    platform: str
    external_chat_id: str
    text: str
    reply_to_message_id: Optional[str] = None


class BaseChannelAdapter(ABC):
    """Abstract adapter each platform must implement."""

    def __init__(self, integration_id: str, config: dict):
        self.integration_id = integration_id
        self.config = config

    @property
    @abstractmethod
    def platform(self) -> str:
        ...

    @abstractmethod
    async def start(self, on_message) -> None:
        """Start listening for incoming messages.

        on_message: async callable(IncomingMessage) -> None
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stop the adapter."""
        ...

    @abstractmethod
    async def send(self, msg: OutgoingMessage) -> None:
        """Send a reply to the external platform."""
        ...

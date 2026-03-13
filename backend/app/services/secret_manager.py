"""Secret Protection Service (Section 22).

Uses Fernet symmetric encryption for API keys and credentials.
Agents never see raw API keys — only SecretManager handles them.
"""

import logging
import json
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


class SecretManager:
    """Manages encryption/decryption of sensitive credentials."""

    _instance = None
    _fernet: Fernet | None = None

    @classmethod
    def get_instance(cls) -> "SecretManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._vault_path = Path(__file__).resolve().parents[2] / "data" / "vault" / "secrets.json"
        self._key_path = Path(__file__).resolve().parents[2] / "data" / "vault" / "fernet.key"
        self._vault_path.parent.mkdir(parents=True, exist_ok=True)
        self._vault_data: dict[str, str] = {}

        key = self._get_or_create_encryption_key()
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
            logger.info("SecretManager initialized with configured key")
        except Exception:
            self._fernet = Fernet(Fernet.generate_key())
            logger.warning("SecretManager using auto-generated key (set ASSITANCE_SECRET_KEY for persistence)")

        self._load_vault()

    def _normalize_provider(self, provider: str) -> str:
        provider_l = (provider or "").strip().lower()
        if provider_l == "google":
            return "gemini"
        return provider_l

    def _get_or_create_encryption_key(self) -> str:
        """Resolve a stable Fernet key for vault encryption.

        Priority order:
        1) Explicit ASSITANCE_SECRET_KEY from settings
        2) Persisted local key file in backend/data/vault/fernet.key
        3) Newly generated key written to that file
        """
        if settings.secret_key:
            return settings.secret_key

        if self._key_path.exists():
            try:
                persisted = self._key_path.read_text(encoding="utf-8").strip()
                if persisted:
                    return persisted
            except Exception as exc:
                logger.warning("Failed reading persisted vault key: %s", exc)

        generated = Fernet.generate_key().decode()
        try:
            self._key_path.write_text(generated, encoding="utf-8")
            logger.warning(
                "ASSITANCE_SECRET_KEY not set; generated persistent local vault key at %s",
                self._key_path,
            )
        except Exception as exc:
            logger.warning("Failed writing persisted vault key: %s", exc)

        return generated

    def _load_vault(self):
        if not self._vault_path.exists():
            self._vault_data = {}
            return
        try:
            raw = self._vault_path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
            self._vault_data = data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning("Failed to load vault file: %s", exc)
            self._vault_data = {}

    def _save_vault(self):
        try:
            self._vault_path.write_text(json.dumps(self._vault_data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to save vault file: %s", exc)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string. Returns plaintext."""
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.warning("Failed to decrypt value in vault with current key")
            return ""

    def get_api_key(self, provider: str) -> str | None:
        """Get API key for a given provider.

        Safe wrapper that agents use instead of accessing credentials directly.
        """
        provider = self._normalize_provider(provider)

        key_map = {
            "openai": settings.openai_api_key,
            "anthropic": settings.anthropic_api_key,
            "gemini": settings.gemini_api_key,
        }
        raw_key = key_map.get(provider)
        if raw_key:
            return raw_key

        encrypted = self._vault_data.get(provider)
        if not encrypted:
            return None

        decrypted = self.decrypt(encrypted)
        if not decrypted:
            return None

        # Warm runtime settings cache for active process.
        if provider == "openai":
            settings.openai_api_key = decrypted
        elif provider == "anthropic":
            settings.anthropic_api_key = decrypted
        elif provider == "gemini":
            settings.gemini_api_key = decrypted

        return decrypted

    def set_api_key(self, provider: str, value: str | None):
        provider = self._normalize_provider(provider)
        clean_value = (value or "").strip()

        if clean_value:
            self._vault_data[provider] = self.encrypt(clean_value)
        else:
            self._vault_data.pop(provider, None)

        self._save_vault()

    def has_api_key(self, provider: str) -> bool:
        return bool(self.get_api_key(provider))

    def get_ollama_url(self) -> str:
        """Get Ollama base URL."""
        return settings.ollama_base_url


def get_secret_manager() -> SecretManager:
    return SecretManager.get_instance()

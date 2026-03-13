from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ASSITANCE_")

    # Server
    host: str = "127.0.0.1"
    port: int = 8322

    # Database — PostgreSQL by default, SQLite fallback for dev
    database_url: str = "postgresql+asyncpg://assitance:assitance@localhost:5432/assitance"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Provider API keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    
    # Gemini Customizable Rate Limits
    gemini_context_window: int = 1048576
    gemini_tpm: int | None = 4000000
    gemini_rpm: int | None = 1000
    gemini_rpd: int | None = None

    ollama_base_url: str = "http://localhost:11434"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Concurrency and Rate Limits
    max_concurrent_agents: int = 10
    max_requests_per_agent: int = 2
    global_request_limit: int = 50

    # Defaults
    default_model: str = "gemini/gemini-2.5-flash"
    default_temperature: float = 0.7
    default_system_prompt: str = "You are a helpful AI assistant."

    # Secret encryption key (auto-generated if not set)
    secret_key: str = ""

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def get_fernet_key(self) -> str:
        """Return a valid Fernet key, generating one if not configured."""
        if self.secret_key:
            return self.secret_key
        # Generate a default key — in production, set ASSITANCE_SECRET_KEY
        return Fernet.generate_key().decode()


settings = Settings()

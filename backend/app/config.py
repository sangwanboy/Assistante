from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ASSITANCE_")

    # Server
    host: str = "127.0.0.1"
    port: int = 8321

    # Database
    database_url: str = "sqlite+aiosqlite:///data/assitance.db"

    # Provider API keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # Defaults
    default_model: str = "gemini/gemini-2.5-flash"
    default_temperature: float = 0.7
    default_system_prompt: str = "You are a helpful AI assistant."


settings = Settings()

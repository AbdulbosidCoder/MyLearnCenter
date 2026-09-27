from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = ""
    # Telegram id of the single administrator. They get the admin role on first login.
    admin_tg_id: int = 0
    # Public HTTPS address of the Mini App (what the bot's button opens).
    webapp_url: str = "https://example.com"
    database_url: str = "sqlite+aiosqlite:///./mylearncenter.db"
    # How long a Telegram initData signature stays valid, in seconds.
    init_data_ttl: int = 24 * 60 * 60
    # Local development only: lets the API accept an "X-Dev-User" header instead of initData.
    dev_mode: bool = False
    seed_demo_content: bool = True
    # Largest file a teacher can upload for the AI agent, in megabytes.
    max_upload_mb: int = 50
    # Claude API for the AI agent that turns uploaded files into lessons.
    anthropic_api_key: str = ""
    ai_model: str = "claude-opus-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()

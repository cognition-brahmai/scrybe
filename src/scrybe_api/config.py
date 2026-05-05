from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SCRYBE API"
    debug: bool = False
    version: str = "0.1.0"

    data_dir: Path = Field(default=Path(".scrybe_data"), alias="SCRYBE_DATA_DIR")
    sqlite_path: Path = Field(
        default=Path(".scrybe_data") / "scrybe.db",
        alias="SCRYBE_SQLITE_PATH",
    )
    artifacts_dir: Path = Field(
        default=Path(".scrybe_data") / "artifacts",
        alias="SCRYBE_ARTIFACTS_DIR",
    )
    cache_dir: Path = Field(
        default=Path(".scrybe_data") / "cache",
        alias="SCRYBE_CACHE_DIR",
    )

    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="SCRYBE_OPENAI_MODEL")

    liteparse_cmd: str = Field(default="lit", alias="SCRYBE_LITEPARSE_CMD")
    liteparse_timeout_seconds: int = Field(
        default=120,
        alias="SCRYBE_LITEPARSE_TIMEOUT_SECONDS",
    )
    dynamic_threshold_chars: int = Field(
        default=500,
        alias="SCRYBE_DYNAMIC_THRESHOLD_CHARS",
    )
    request_timeout_seconds: int = Field(
        default=30,
        alias="SCRYBE_REQUEST_TIMEOUT_SECONDS",
    )
    cache_ttl_seconds: int = Field(default=3600, alias="SCRYBE_CACHE_TTL_SECONDS")
    max_sync_seconds: int = Field(default=20, alias="SCRYBE_MAX_SYNC_SECONDS")

    enable_auth: bool = Field(default=False, alias="SCRYBE_ENABLE_AUTH")
    api_key_header_name: str = Field(
        default="X-API-Key",
        alias="SCRYBE_API_KEY_HEADER_NAME",
    )
    api_key_secret: str | None = Field(default=None, alias="SCRYBE_API_KEY_SECRET")

    playwright_browser: str = Field(
        default="chromium",
        alias="SCRYBE_PLAYWRIGHT_BROWSER",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return settings


from __future__ import annotations

from datetime import time
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_hhmm(value: str) -> time:
    hh, mm = value.strip().split(":")
    return time(hour=int(hh), minute=int(mm))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_env: str = "development"
    log_level: str = "info"
    tz: str = "Asia/Jakarta"
    internal_api_token: str = ""
    dashboard_token: str = ""
    cors_allow_origins: str = "http://localhost:3000"

    approval_window_start: str = "01:00"
    approval_window_end: str = "10:00"
    collection_window_start: str = "10:00"
    collection_window_end: str = "22:00"

    database_url: str = ""

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_endpoint: str = ""
    r2_public_url: str = ""

    openai_api_key: str = ""
    llm_model_cheap: str = "gpt-4o-mini"
    llm_model_quality: str = "gpt-4o"
    llm_embedding_model: str = "text-embedding-3-small"
    llm_embedding_dim: int = 1536
    web_search_model: str = "gpt-4o-search-preview"
    tavily_api_key: str = ""
    supadata_api_key: str = ""

    telegram_bot_token: str = ""
    telegram_group_chat_id: str = ""
    telegram_webhook_secret: str = ""
    telegram_webhook_url: str = ""
    owner_telegram_id: int = 0

    google_drive_folder_id: str = ""
    google_service_account_json: str = ""

    crawl_user_agent: str = "CrawlerKonten/0.1"
    crawl_rate_limit_rps: float = 0.5
    crawl_timeout: int = 20
    crawl_max_retries: int = 3
    crawl_respect_robots: bool = True
    crawl_source_error_threshold: int = 5
    crawl_proxy_url: str = ""
    crawl_verify_ssl: bool = True

    sentry_dsn: str = ""
    youtube_api_key: str = ""

    @field_validator("cors_allow_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def approval_window(self) -> tuple[time, time]:
        return _parse_hhmm(self.approval_window_start), _parse_hhmm(self.approval_window_end)

    @property
    def collection_window(self) -> tuple[time, time]:
        return _parse_hhmm(self.collection_window_start), _parse_hhmm(self.collection_window_end)

    def in_window(self, window: tuple[time, time], now: time) -> bool:
        start, end = window
        if start <= end:
            return start <= now < end
        return now >= start or now < end


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    binance_market: Literal["spot", "futures"] = "spot"
    binance_base_url: str = ""
    binance_timeout_seconds: float = Field(default=10, gt=0)
    binance_max_attempts: int = Field(default=3, ge=1, le=5)
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = Field(default=60, ge=1)
    stale_ttl_seconds: int = Field(default=3600, ge=1)
    symbols_ttl_seconds: int = Field(default=3600, ge=1)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    telegram_enabled: bool = False
    telegram_timeout_seconds: float = Field(default=10, gt=0, le=60)
    telegram_timezone: Literal["Asia/Ho_Chi_Minh", "UTC"] = "Asia/Ho_Chi_Minh"
    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    openai_timeout_seconds: float = Field(default=60, gt=0)
    ai_enabled: bool = True
    telegram_ai_enabled: bool = True
    telegram_ai_language: Literal["en"] = "en"
    telegram_ai_timeout_seconds: float = Field(default=8, gt=0, le=60)
    ai_chat_requests_per_minute: int = Field(default=6, ge=1, le=60)
    telegram_test_enabled: bool = False
    telegram_test_key: SecretStr | None = Field(default=None, min_length=24, max_length=256)

    @field_validator("telegram_ai_language", mode="before")
    @classmethod
    def english_notifications(cls, value):
        # Accept existing .env files while migrating all outgoing responses to English.
        return "en" if value == "vi" else value

    @field_validator("telegram_test_key", mode="before")
    @classmethod
    def empty_test_key(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_ttls(self):
        if self.stale_ttl_seconds <= self.cache_ttl_seconds:
            raise ValueError("STALE_TTL_SECONDS must exceed CACHE_TTL_SECONDS")
        return self

    @property
    def base_url(self) -> str:
        return self.binance_base_url.rstrip("/") or (
            "https://api.binance.com"
            if self.binance_market == "spot"
            else "https://fapi.binance.com"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

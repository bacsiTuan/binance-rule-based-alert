from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import Interval


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)
    symbol: str = Field(default="BTCUSDT", pattern=r"^[a-zA-Z0-9]{2,30}$")
    interval: Interval = "1d"
    language: Literal["en", "vi"] = "en"

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value):
        return value.upper()

    @field_validator("message")
    @classmethod
    def meaningful_message(cls, value):
        if not value.strip():
            raise ValueError("Message must not be blank")
        return value.strip()


class ConfirmedTelegramRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    confirmed: Literal[True]

    @field_validator("confirmed", mode="before")
    @classmethod
    def explicit_confirmation(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation is required")
        return value


class TelegramTestRequest(ConfirmedTelegramRequest):
    symbol: str = Field(default="BTCUSDT", pattern=r"^[a-zA-Z0-9]{2,30}$")
    interval: Interval = "1d"
    language: Literal["en", "vi"] = "en"

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value):
        return value.upper()

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_defaults_and_secret():
    settings = Settings(_env_file=None, telegram_bot_token="sentinel-token")
    assert not settings.telegram_enabled
    assert settings.telegram_timeout_seconds == 10
    assert "sentinel-token" not in repr(settings)


@pytest.mark.parametrize("value", [0, -1, 61])
def test_invalid_timeout(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, telegram_timeout_seconds=value)


def test_alert_ai_timeout_allows_slower_models_but_remains_bounded():
    assert Settings(_env_file=None, telegram_ai_timeout_seconds=45).telegram_ai_timeout_seconds == 45
    with pytest.raises(ValidationError):
        Settings(_env_file=None, telegram_ai_timeout_seconds=61)


@pytest.mark.parametrize("language", ["en", "vi"])
def test_notifications_use_english_even_with_legacy_env_language(language):
    assert Settings(_env_file=None).telegram_ai_language == "en"
    assert Settings(_env_file=None, telegram_ai_language=language).telegram_ai_language == "en"

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

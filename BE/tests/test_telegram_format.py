from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.models import RuleCreate
from app.service.telegram_format import display_number, format_time, market_message, rule_message


def context():
    return {"symbol": "BTCUSDT", "market": "spot", "interval": "1d", "source": "cache",
            "stale": False, "last_close": "82200.06000000",
            "last_open_time": 1791936000000,  # 2026-10-14 00:00 UTC
            "last_close_time": 1792022399999,  # 2026-10-14 23:59:59.999 UTC
            "fetched_at": "2026-10-15T01:00:00+00:00"}


def test_vietnam_times_distinguish_closed_daily_candle_from_snapshot_and_send_time():
    text, bold = market_message(context(), "Quan sát và kịch bản có điều kiện.", language="vi",
                               zone="Asia/Ho_Chi_Minh", sent_at=datetime(2026, 10, 15, 1, 5, tzinfo=UTC))
    assert text.startswith("BTCUSDT · Nhận định thị trường\nSPOT · 1D")
    assert "Giá đóng: 82,200.06" in text
    assert "Mở nến: 14/10/2026 07:00:00" in text
    assert "Đóng nến: 15/10/2026 06:59:59" in text
    assert "Cập nhật dữ liệu: 15/10/2026 08:00:00" in text
    assert "Gửi lúc: 15/10/2026 08:05:00" in text
    assert "Múi giờ: UTC+07:00" in text and "Nguồn: Redis cache" in text
    assert "TEST" not in text and "MANUAL" not in text and "False" not in text
    assert bold == len(text.splitlines()[0])


def test_utc_display_does_not_apply_vietnam_offset_twice():
    text, _ = market_message(context(), "Conditional outlook", language="en", zone="UTC",
                             sent_at=datetime(2026, 10, 15, 1, 5, tzinfo=UTC))
    assert "Close: 14/10/2026 23:59:59" in text
    assert "Sent: 15/10/2026 01:05:00" in text
    assert "Timezone: UTC\n" in text
    assert "Closed candle (UTC):" not in text and "+00:00" not in text


def test_rule_and_market_messages_share_times_without_manual_labels():
    rule = RuleCreate(symbol="BTCUSDT", timeframe="1d", indicator={"type":"rsi", "length":14},
                      operator="gte", target=70, message="Momentum confirmation")
    rule = SimpleNamespace(id=7, **rule.model_dump())
    rule.indicator = SimpleNamespace(**rule.indicator)
    text, bold = rule_message(rule, "71.1234", "70", context()["last_open_time"],
                              context()["last_close_time"], market="spot", language="en",
                              zone="Asia/Ho_Chi_Minh", sent_at=datetime(2026, 10, 15, 1, 5, tzinfo=UTC),
                              analysis="Wait for confirmation.")
    assert text.startswith("Rule #7: Momentum confirmation\nBTCUSDT · SPOT · 1D")
    assert "Value: 71.12 >= 70" in text
    assert "Close: 15/10/2026 06:59:59" in text
    assert "[MANUAL]" not in text and "TEST" not in text
    assert text[bold:].startswith("\n")


def test_missing_and_invalid_times_are_not_fabricated_or_called_closed():
    data = context()
    data.update(last_open_time=None, last_close_time=None, last_close_at=None, stale=True)
    text, _ = market_message(data, "Insufficient data.", language="en", zone="UTC",
                             sent_at=datetime(2026, 10, 15, tzinfo=UTC))
    assert "Candle: Unavailable" in text and "Open: —" in text and "Close: —" in text
    assert "Fallback data" in text
    naive_time = datetime(2026, 10, 15)  # noqa: DTZ001 - deliberately exercise missing timezone
    for value in (None, "bad", True, naive_time, float("inf")):
        assert format_time(value) == "—"


@pytest.mark.parametrize("analysis", ["Detailed analysis " * 2000, "🚀" * 3000], ids=["long-text", "emoji"])
def test_long_titles_and_analysis_keep_metadata_and_telegram_size_limit(analysis):
    data = context()
    text, bold = market_message(data, analysis, language="vi", zone="UTC",
                               sent_at=datetime(2026, 10, 15, tzinfo=UTC))
    assert len(text) <= 4096 and text.endswith("…")
    assert len(text.encode("utf-16-le")) // 2 <= 4096
    assert "Đóng nến: 14/10/2026 23:59:59" in text
    assert "Phân tích AI\n" in text and bold == len(text.splitlines()[0])


@pytest.mark.parametrize("raw,expected", [("0.00000100", "0.000001"),
    ("100.000000", "100"), ("12345.678900", "12,345.6789"), (None, "—"), ("NaN", "—")])
def test_prices_are_readable_without_losing_small_values(raw, expected):
    assert display_number(raw) == expected


def test_timezone_configuration_is_explicit():
    assert Settings(_env_file=None).telegram_timezone == "Asia/Ho_Chi_Minh"
    with pytest.raises(ValueError):
        Settings(_env_file=None, telegram_timezone="typo")

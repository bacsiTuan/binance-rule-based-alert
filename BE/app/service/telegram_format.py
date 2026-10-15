"""Shared plain-text Telegram presentation; scheduling always remains in UTC."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from app.telegram_state import COMPARISONS


def timezone_label(zone):
    return "UTC" if zone == "UTC" else "UTC+07:00"


def format_time(value, zone="Asia/Ho_Chi_Minh"):
    """Show missing/invalid timestamps honestly instead of substituting the current time."""
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        elif type(value) in (int, float):
            value = datetime.fromtimestamp(value / 1000, UTC)
        if not isinstance(value, datetime) or value.tzinfo is None:
            return "—"
        target = UTC if zone == "UTC" else timezone(timedelta(hours=7))
        return value.astimezone(target).strftime("%d/%m/%Y %H:%M:%S")
    except (ValueError, OverflowError, OSError):
        return "—"


def display_number(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            return "—"
        if number and abs(number.adjusted()) > 30:
            return f"{number:.8E}"
        return format(number, ",f").rstrip("0").rstrip(".") if number % 1 else format(number, ",.0f")
    except InvalidOperation:
        return "—"


def text_units(text):
    return len(text.encode("utf-16-le")) // 2


def clip(text, budget):
    if text_units(text) <= budget:
        return text
    return text.encode("utf-16-le")[:max(0, budget - 1) * 2].decode("utf-16-le", errors="ignore").rstrip() + "…"


def compose(title, lines, analysis, language):
    title = title.strip().replace("\r", " ").replace("\n", " ")
    title = clip(title, 200)
    body = "\n".join(lines)
    if analysis and analysis.strip():
        label = "Phân tích AI" if language == "vi" else "AI analysis"
        prefix = f"{title}\n{body}\n\n{label}\n"
        return prefix + clip(analysis.strip(), 4096 - text_units(prefix)), len(title)
    return f"{title}\n{body}", len(title)


def time_lines(opened, closed, sent_at, zone, language, *, fetched_at=None):
    vi = language == "vi"
    lines = [
        ("Nến: Đã đóng" if vi else "Candle: CLOSED") if format_time(closed, zone) != "—"
        else ("Nến: Chưa có nến đóng" if vi else "Candle: Unavailable"),
        f"{'Mở nến' if vi else 'Open'}: {format_time(opened, zone)}",
        f"{'Đóng nến' if vi else 'Close'}: {format_time(closed, zone)}",
    ]
    if fetched_at is not None:
        lines.append(f"{'Cập nhật dữ liệu' if vi else 'Data updated'}: {format_time(fetched_at, zone)}")
    lines.extend([
        f"{'Gửi lúc' if vi else 'Sent'}: {format_time(sent_at, zone)}",
        f"{'Múi giờ' if vi else 'Timezone'}: {timezone_label(zone)}",
    ])
    return lines


def rule_message(rule, value, threshold, opened, closed, *, market, language,
                 zone, sent_at, analysis=None):
    title = f"Rule #{rule.id}" + (f": {rule.message}" if rule.message else "")
    vi = language == "vi"
    lines = [
        f"{rule.symbol} · {market.upper()} · {rule.timeframe.upper()}", "",
        f"{'Chỉ báo' if vi else 'Indicator'}: {rule.indicator.type.upper()}({rule.indicator.length})",
        f"{'Giá trị' if vi else 'Value'}: {Decimal(value):.2f} {COMPARISONS[rule.operator][1]} {threshold}",
        "", *time_lines(opened, closed, sent_at, zone, language),
    ]
    return compose(title, lines, analysis, language)


def market_message(context, analysis, *, language, zone, sent_at):
    vi = language == "vi"
    title = f"{context['symbol']} · " + ("Nhận định thị trường" if vi else "Market outlook")
    sources = {"binance": "Binance", "cache": "Redis cache", "redis": "Redis cache",
               "stale": "Dữ liệu dự phòng" if vi else "Fallback cache"}
    lines = [
        f"{context['market'].upper()} · {context['interval'].upper()}", "",
        f"{'Giá đóng' if vi else 'Close price'}: {display_number(context.get('last_close'))}", "",
        *time_lines(context.get("last_open_time"),
                    context.get("last_close_time", context.get("last_close_at")),
                    sent_at, zone, language, fetched_at=context.get("fetched_at")),
        f"{'Nguồn' if vi else 'Source'}: {sources.get(context.get('source'), '—')}",
    ]
    if context.get("stale"):
        lines.append("Dữ liệu dự phòng, chưa cập nhật mới."
                     if vi else "Fallback data; a newer snapshot is unavailable.")
    return compose(title, lines, analysis, language)

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.telegram_state import Delivery, MonitorMetadata, MonitorState


def delivery(**changes):
    data = {"event_id": "a" * 64, "candle_open_ms": 0, "candle_close_ms": 999,
                "value": "70.00000000000001", "threshold": "70", "reserved_at_ms": 1000}
    data.update(changes)
    return data


@pytest.mark.parametrize("changes", [
    {"value": "not-a-number"}, {"threshold": "Infinity"}, {"value": "NaN"},
    {"candle_open_ms": -1}, {"candle_close_ms": 0.5}, {"reserved_at_ms": True},
    {"completed_at_ms": -1}, {"candle_open_ms": 1001},
    {"delivery_status": "accepted"}, {"message_id": 2},
    {"delivery_status": "accepted", "message_id": True},
    {"delivery_status": "accepted", "message_id": -1},
    {"error_code": "https://api.telegram.org/botSECRET"},
])
def test_delivery_rejects_invalid_fields(changes):
    with pytest.raises(ValidationError):
        Delivery(**delivery(**changes))


def test_decimal_round_trip():
    event = Delivery(**delivery())
    state = MonitorState(generation=str(uuid4()), rule_id=1, updated_at_ms=1000,
                         last_event=event, last_value=event.value)
    restored = MonitorState.model_validate_json(state.model_dump_json())
    assert restored.last_value == "70.00000000000001"
    assert restored.last_event.delivery_status == "attempt_reserved"


@pytest.mark.parametrize("changes", [
    {"activated_at_ms": -1}, {"activated_at_ms": 1.2}, {"generation": "wrong"},
    {"schema_version": 2},
])
def test_metadata_validation(changes):
    with pytest.raises(ValidationError):
        MonitorMetadata(condition_fingerprint="x", **changes)

import json
import runpy
from pathlib import Path

import httpx
import pytest


@pytest.mark.parametrize("flag", [None, "0", "false"])
def test_credentials_do_not_enable_live_test(monkeypatch, flag):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "sentinel-not-a-real-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    if flag is None:
        monkeypatch.delenv("RUN_TELEGRAM_LIVE_TESTS", raising=False)
    else:
        monkeypatch.setenv("RUN_TELEGRAM_LIVE_TESTS", flag)
    with pytest.raises(pytest.skip.Exception, match="explicit opt-in"):
        runpy.run_path(str(Path(__file__).with_name("test_telegram_client_live.py")))


@pytest.mark.parametrize("outcome", ["accepted", "rejected", "timeout", "invalid_ack"])
async def test_opt_in_uses_fake_transport_for_gate_verification(monkeypatch, outcome):
    monkeypatch.setenv("RUN_TELEGRAM_LIVE_TESTS", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "sentinel-not-a-real-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    calls = []

    def respond(request):
        calls.append(request)
        if outcome == "timeout":
            raise httpx.ReadTimeout("sentinel-not-a-real-token", request=request)
        if outcome == "rejected":
            return httpx.Response(400, json={"ok": False})
        if outcome == "invalid_ack":
            return httpx.Response(200, json={"ok": True, "result": {}})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs),
    )
    module = runpy.run_path(str(Path(__file__).with_name("test_telegram_client_live.py")))
    if outcome == "accepted":
        await module["test_send_real_message"]()
    else:
        with pytest.raises(AssertionError) as error:
            await module["test_send_real_message"]()
        assert "sentinel-not-a-real-token" not in str(error.value)
        assert "123" not in str(error.value)
    assert len(calls) == 1
    assert "[KIỂM THỬ]" in json.loads(calls[0].content)["text"]

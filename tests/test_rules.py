import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import Indicator, RuleCreate, RuleUpdate
from app.rules import RuleStorage


@pytest.fixture
async def fake_redis():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()


@pytest.fixture
async def rule_storage(fake_redis):
    storage = RuleStorage(fake_redis)
    yield storage


async def test_rule_storage_init_seeds_and_crud(rule_storage):
    # Ban đầu chưa có rule, init_seeds sẽ tạo 2 rule mẫu
    await rule_storage.init_seeds()
    rules = await rule_storage.list_rules()
    assert len(rules) == 2
    assert rules[0].id == 1
    assert rules[0].symbol == "BTCUSDT"
    assert rules[1].id == 2
    assert rules[1].symbol == "ETHUSDT"

    # Tạo rule mới #3
    new_rule = await rule_storage.create_rule(
        RuleCreate(
            symbol="solusdt",
            timeframe="1h",
            indicator=Indicator(type="rsi", length=14),
            operator="cross_below",
            target=70,
            candle_mode="closed",
        )
    )
    assert new_rule.id == 3
    assert new_rule.symbol == "SOLUSDT"
    assert new_rule.enabled is True

    # Cập nhật rule #3 (tắt rule)
    updated = await rule_storage.update_rule(3, RuleUpdate(enabled=False))
    assert updated is not None
    assert updated.enabled is False

    # Lấy danh sách kiểm tra
    rules_after = await rule_storage.list_rules()
    assert len(rules_after) == 3

    # Xóa rule #1
    deleted = await rule_storage.delete_rule(1)
    assert deleted is True
    assert (await rule_storage.get_rule(1)) is None

    # Xóa rule không tồn tại
    assert (await rule_storage.delete_rule(999)) is False


def test_rules_http_endpoints():
    app = create_app(Settings(_env_file=None))
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    storage = RuleStorage(fake_redis)

    with TestClient(app) as http:
        app.state.rule_storage = storage

        # List ban đầu
        res = http.get("/rules")
        assert res.status_code == 200
        assert res.json() == []

        # Tạo rule
        payload = {
            "symbol": "BTCUSDT",
            "timeframe": "1d",
            "indicator": {"type": "rsi", "length": 14},
            "operator": "cross_above",
            "target": 30,
            "candle_mode": "closed",
        }
        create_res = http.post("/rules", json=payload)
        assert create_res.status_code == 201
        data = create_res.json()
        assert data["id"] == 1
        assert data["symbol"] == "BTCUSDT"
        assert data["enabled"] is True

        # Toggle rule
        patch_res = http.patch("/rules/1", json={"enabled": False})
        assert patch_res.status_code == 200
        assert patch_res.json()["enabled"] is False

        # Patch không tìm thấy
        assert http.patch("/rules/999", json={"enabled": True}).status_code == 404

        # Delete rule
        del_res = http.delete("/rules/1")
        assert del_res.status_code == 204

        # Delete không tìm thấy
        assert http.delete("/rules/999").status_code == 404

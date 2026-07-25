import pytest

from src.alert_manager import AlertManager
from src.config import config
from src.models import AlertLevel, StrategyType


@pytest.fixture
def telegram_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.telegram, "enabled", True)
    monkeypatch.setattr(config.telegram, "bot_token", "test-token")
    monkeypatch.setattr(config.telegram, "chat_id", "test-chat")
    monkeypatch.setattr(config.telegram, "delivery_timeout_seconds", 2.0)
    monkeypatch.setattr(config.alerts, "batch_window_seconds", 0.01)


def _patch_delivery(
    monkeypatch: pytest.MonkeyPatch,
    manager: AlertManager,
    result: bool,
) -> None:
    async def fake_send(message: str, chat_id: str) -> bool:
        assert message
        assert chat_id == "test-chat"
        return result

    monkeypatch.setattr(
        manager,
        "_send_telegram",
        fake_send,
    )


@pytest.mark.asyncio
async def test_json_alert_waits_for_confirmed_delivery(
    monkeypatch: pytest.MonkeyPatch,
    telegram_config: None,
) -> None:
    manager = AlertManager()
    _patch_delivery(monkeypatch, manager, True)

    delivered = await manager.send_json_alert(
        {
            "symbol": "BTCUSDT",
            "market": "spot",
            "change3mPct": 3.0,
            "direction": "UP",
            "volumeGroup": "HIGH",
            "quoteVolume24h": 1_000_000,
        },
        telegram_enabled=True,
    )

    assert delivered is True
    await manager.close()


@pytest.mark.asyncio
async def test_failed_delivery_does_not_start_cooldown(
    monkeypatch: pytest.MonkeyPatch,
    telegram_config: None,
) -> None:
    manager = AlertManager()
    _patch_delivery(monkeypatch, manager, False)

    delivered = await manager.send_alert(
        AlertLevel.P1,
        "BTCUSDT",
        StrategyType.CHANGE_3M,
        "test",
    )

    assert delivered is False
    assert manager.last_alert_time == {}
    await manager.close()


@pytest.mark.asyncio
async def test_explicit_log_only_mode_does_not_open_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config.telegram, "enabled", False)
    manager = AlertManager()

    processed = await manager.send_json_alert(
        {"symbol": "BTCUSDT"},
        telegram_enabled=False,
    )

    assert processed is True
    assert manager.client_session is None

import pytest

from src.change3m_calculator import Change3MCalculator


def _kline(close: object) -> list[object]:
    return [0, "0", "0", "0", close, "0"]


def test_calculates_three_minute_change() -> None:
    klines = [_kline("100"), _kline("101"), _kline("102"), _kline("110")]
    assert Change3MCalculator.calculate_change(klines) == pytest.approx(10.0)


@pytest.mark.parametrize(
    "klines",
    [
        [],
        [_kline("100")] * 3,
        [_kline("0"), _kline("1"), _kline("2"), _kline("3")],
        [_kline("bad"), _kline("1"), _kline("2"), _kline("3")],
    ],
)
def test_rejects_invalid_klines(klines: list[list[object]]) -> None:
    assert Change3MCalculator.calculate_change(klines) is None


def test_trigger_requires_positive_threshold() -> None:
    assert Change3MCalculator.check_trigger(-4.0, 4.0)
    with pytest.raises(ValueError):
        Change3MCalculator.check_trigger(1.0, 0)


def test_direction_includes_flat_state() -> None:
    assert Change3MCalculator.get_direction(1) == "UP"
    assert Change3MCalculator.get_direction(-1) == "DOWN"
    assert Change3MCalculator.get_direction(0) == "FLAT"

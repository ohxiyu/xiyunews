"""Synthetic timestamped replays; these are not historical backtests."""
# ruff: noqa: RUF001

import math

import pytest

from src.platform.signals import MoveWindow, move_gate, signal_title


def trade(window, second, price=100, trade_id=None, delay=0):
    stamp = second * 1000
    return window.update(
        dict(T=stamp, a=second if trade_id is None else trade_id, p=str(price)), stamp + delay
    )


def warm(window):
    for t in range(181):
        assert not trade(window, t)
    assert window.ready


@pytest.mark.parametrize("price,direction", [(102, 1), (98, -1)])
def test_three_minute_move_confirmed_for_three_seconds_both_directions(price, direction):
    w = MoveWindow(2.0)
    warm(w)
    for t in range(181, 184):
        assert not trade(w, t, price)
    [move] = trade(w, 184, price)
    assert move["direction"] == direction and move["price"] == price
    assert move["change"] == pytest.approx(2 * direction)
    assert (move["window_seconds"], move["crossed_at"], move["at"]) == (180, 181, 184)
    # The move stays confirmed while beyond the threshold; the store gate decides alerts.
    assert trade(w, 185, price)
    assert not trade(w, 186, 100)
    for t in range(187, 190):
        assert not trade(w, t, price)
    assert trade(w, 190, price)


def test_wick_and_idle_gap_do_not_confirm():
    w = MoveWindow(2.0)
    warm(w)
    assert not trade(w, 181, 104)
    assert not trade(w, 182, 100)
    assert not trade(w, 183, 104)
    # Aggregate IDs continuous but >2 seconds without an observation: restart confirmation.
    assert not trade(w, 190, 104, trade_id=184)
    assert not trade(w, 191, 104, trade_id=185)


def test_reference_is_last_trade_at_or_before_three_minutes_ago():
    w = MoveWindow(2.0)
    for t in range(181):
        trade(w, t, 100 if t < 60 else 101)
    for t in range(181, 185):
        moves = trade(w, t, 103)
    assert moves[0]["change"] == pytest.approx(3)
    for t in range(185, 240):
        moves = trade(w, t, 103)
    assert moves[0]["change"] == pytest.approx(3)  # Cutoff t=59: still the 100 at t=0.
    # From t=240 the 101 traded at t=60 is the reference: +1.98% is below 2%.
    assert not trade(w, 240, 103)


@pytest.mark.parametrize("mode", ["gap", "stale", "future"])
def test_invalid_stream_rewarms_without_alerts(mode):
    w = MoveWindow(2.0)
    warm(w)
    kw = {"trade_id": 182} if mode == "gap" else {"delay": 10001 if mode == "stale" else -2001}
    assert not trade(w, 181, 110, **kw)
    assert not w.ready
    assert not trade(w, 182, 110, trade_id=183)


def test_duplicate_out_of_order_nonfinite_and_unready():
    w = MoveWindow(2.0)
    for t in range(180):
        assert not trade(w, t, 100 + t / 10)
    assert not w.ready
    assert not trade(w, 178, 200)
    assert not trade(w, 180, math.nan)
    assert not trade(w, 180, -1)


def test_future_timestamp_does_not_poison_fresh_stream_watermark():
    w = MoveWindow(2.0)
    warm(w)
    assert not trade(w, 100000, 200, delay=-99000000)
    for t in range(181, 362):
        assert not trade(w, t)
    assert w.ready


def test_window_extremes():
    w = MoveWindow(2.0)
    warm(w)
    for t, price in [(181, 103), (182, 99), (183, 101)]:
        trade(w, t, price)
    assert (w.extreme(1), w.extreme(-1), w.price) == (103, 99, 101)


def test_gate_hourly_per_direction_with_further_ten_percent():
    up = dict(direction=1, at=5000.0, price=110.0)
    assert move_gate(None, up, 3600, 10) == "fresh"
    assert move_gate((1400.0, 200.0), up, 3600, 10) == "fresh"
    assert move_gate((1400.001, 200.0), up, 3600, 10) == ""
    assert move_gate((2000.0, 100.0), up, 3600, 10) == "continuation"
    assert move_gate((2000.0, 100.1), up, 3600, 10) == ""
    # Carried over from the previous policy without a price: only the hour can pass it.
    assert move_gate((2000.0, None), up, 3600, 10) == ""
    down = dict(direction=-1, at=5000.0, price=90.0)
    assert move_gate((2000.0, 100.0), down, 3600, 10) == "continuation"
    assert move_gate((2000.0, 99.0), down, 3600, 10) == ""


def test_titles():
    move = dict(direction=1, change=4.2, window_seconds=180)
    assert signal_title("ZECUSDT", move) == "ZEC 3 分钟内上涨 4.20%"
    assert signal_title("ZECUSDT", dict(move, extreme=True)) == (
        "ZEC 3 分钟内上涨 4.20%，创 24 小时新高"
    )
    down = dict(direction=-1, change=-12.5, window_seconds=180, further=10.44, extreme=True)
    assert signal_title("ZECUSDT", down) == (
        "ZEC 3 分钟内下跌 12.50%，较上次提醒再跌 10.4%，创 24 小时新低"
    )

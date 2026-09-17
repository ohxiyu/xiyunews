"""Synthetic timestamped replays; these are not historical ZEC backtests."""

import math

import pytest

from src.platform.signals import BurstWindow, TrendWindow, signal_title


def trade(window, second, price=100, trade_id=None, delay=0):
    stamp = second * 1000
    return window.update(
        dict(T=stamp, a=second if trade_id is None else trade_id, p=str(price)), stamp + delay
    )


def warm(window):
    for t in range(181):
        assert not trade(window, t)[0]
    assert window.ready


@pytest.mark.parametrize("price,direction", [(102, 1), (98, -1)])
def test_burst_confirmation_symmetric_and_recross(price, direction):
    w = BurstWindow({60: 1.5, 180: 2.5})
    warm(w)
    for t in range(181, 184):
        assert not trade(w, t, price)[0]
    hits, _ = trade(w, 184, price)
    assert len(hits) == 1 and hits[0]["direction"] == direction
    assert hits[0]["window_seconds"] == 60
    assert not trade(w, 185, price)[0]
    assert direction in trade(w, 186, 100)[1]
    for t in range(187, 191):
        hits, _ = trade(w, t, price)
    assert len(hits) == 1


def test_wick_and_missing_confirmation_do_not_trigger():
    w = BurstWindow({60: 1.5, 180: 2.5})
    warm(w)
    assert not trade(w, 181, 104)[0]
    assert not trade(w, 182, 100)[0]
    assert not trade(w, 183, 104)[0]
    # Aggregate IDs continuous but >2 seconds without an observation: restart confirmation.
    assert not trade(w, 190, 104, trade_id=184)[0]
    assert not trade(w, 191, 104, trade_id=185)[0]


def test_exact_rolling_reference_and_strongest_window():
    w = BurstWindow({60: 1.5, 180: 2.5})
    for t in range(181):
        trade(w, t, 100 if t < 60 else 102)
    for t in range(181, 185):
        hits, _ = trade(w, t, 105)
    assert len(hits) == 1
    assert hits[0]["window_seconds"] == 180
    assert hits[0]["change"] == pytest.approx(5)


@pytest.mark.parametrize("mode", ["gap", "stale", "future"])
def test_invalid_stream_rewarms_without_alerts(mode):
    w = BurstWindow({60: 1.5, 180: 2.5})
    warm(w)
    kw = {"trade_id": 182} if mode == "gap" else {"delay": 10001 if mode == "stale" else -2001}
    assert not trade(w, 181, 110, **kw)[0]
    assert not w.ready
    assert not trade(w, 182, 110, trade_id=183)[0]


def test_duplicate_out_of_order_nonfinite_and_unready():
    w = BurstWindow({60: 1.5, 180: 2.5})
    for t in range(180):
        assert not trade(w, t, 100 + t / 10)[0]
    assert not w.ready
    assert not trade(w, 178, 200)[0]
    assert not trade(w, 180, math.nan)[0]
    assert not trade(w, 180, -1)[0]


def row(i, price=100, high=None, low=None):
    return [i * 900000, price, high or price, low or price, price, 0, (i + 1) * 900000 - 1]


def candle(i, price, high=None, low=None, closed=True):
    r = row(i, price, high, low)
    return dict(t=r[0], T=r[6], h=r[2], l=r[3], c=r[4], x=closed)


def trend(prices=None):
    w = TrendWindow()
    w.seed([row(i, p) for i, p in enumerate(prices or [100] * 96)], 96 * 900000)
    return w


@pytest.mark.parametrize("price,direction", [(106, 1), (94, -1)])
def test_trend_closed_candle_and_breakout_excludes_current(price, direction):
    w = trend()
    k = candle(96, price, high=max(price, 100) + 1, low=min(price, 100) - 1, closed=False)
    now = 97 * 900000
    assert w.update(k, now) is None
    k["x"] = True
    hit = w.update(k, now)
    # close must be in outer 10% of range; use exact high/low for next run.
    assert hit is None
    w = trend()
    hit = w.update(candle(96, price), now)
    assert hit["direction"] == direction and hit["breakout"]
    assert w.update(candle(96, price), now) is None


def test_slow_day_rise_without_burst_still_triggers():
    # A smooth 10% day: ~0.02%/3m, well below burst thresholds.
    w = trend([100 * (1.10 ** (i / 96)) for i in range(96)])
    hit = w.update(candle(96, 110), 97 * 900000)
    assert hit["window_seconds"] == 86400 and hit["breakout"]
    assert hit["change_24h"] == pytest.approx(10)
    assert "持续走强" in signal_title("ZECUSDT", [hit])


def test_prior_wick_blocks_breakout_but_allows_trend():
    w = trend()
    w.bars[95 * 900000] = (106, 100, 100)
    hit = w.update(candle(96, 105.5), 97 * 900000)
    assert hit and not hit["breakout"]


@pytest.mark.parametrize("mode", ["missing", "stale", "future", "short"])
def test_trend_no_alert_on_incomplete_or_stale_history(mode):
    w = trend()
    if mode == "missing":
        w.bars.pop(10 * 900000)
    elif mode == "short":
        w.bars.clear()
    delay = 11000 if mode == "stale" else -1 if mode == "future" else 0
    assert w.update(candle(96, 110), 97 * 900000 + delay) is None


def test_seed_ignores_open_bars_and_never_overwrites_live_close():
    w = trend()
    w.seed([row(96, 500)], 96 * 900000 + 100)
    assert 96 * 900000 not in w.bars
    hit = w.update(candle(96, 110), 97 * 900000)
    assert hit
    w.seed([row(96, 500)], 97 * 900000)
    assert w.bars[96 * 900000][2] == 110


def test_future_timestamp_does_not_poison_fresh_stream_watermark():
    w = BurstWindow({60: 1.5, 180: 2.5})
    warm(w)
    assert not trade(w, 100000, 200, delay=-99000000)[0]
    for t in range(181, 362):
        assert not trade(w, t)[0]
    assert w.ready

import time

from src.platform.assets import Assets


def test_asset_name_match_stale_and_ambiguity():
    cache = Assets()
    cache.checked = time.time()
    cache.coins = [
        dict(symbol="OP", name="Optimism", quotes={"USD": {"market_cap": 123}}),
        dict(symbol="USDT", name="Tether", quotes={"USD": {"market_cap": 456}}),
    ]
    event = dict(kind="announcement", title="Optimism网络USDT置换", symbol="")
    assert {a["symbol"] for a in cache.match(event)} == {"OP", "USDT"}
    cache.checked = time.time() - 1801
    assert all(a["market_cap"] is None for a in cache.match(event))
    cache.checked = time.time()
    cache.matches.clear()
    cache.coins.append(dict(symbol="OP", name="Other", quotes={"USD": {"market_cap": 789}}))
    result = cache.match(dict(kind="market", title="OPUSDT", symbol="OPUSDT"))
    assert all(a["ambiguous"] and a["market_cap"] is None for a in result)
    assert cache.match(dict(kind="market", title="NEW", symbol="NEWUSDT"))[0]["market_cap"] is None


def test_single_letter_prose_not_a_coin():
    cache = Assets()
    cache.coins = [dict(symbol="X", name="X", quotes={})]
    assert cache.match(dict(kind="announcement", title="X-合约正式上线")) == []

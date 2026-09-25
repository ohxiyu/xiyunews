"""On-chain Binance flows: classification, threshold, receipts, checkpoints and routing."""
# ruff: noqa: RUF001

import asyncio

import pytest

from src.platform.delivery import Delivery, format_message
from src.platform.flows import CHAINS, TRANSFER, Flows, tron_from_hex, tron_to_hex
from src.platform.settings import Settings
from src.platform.store import Store

ETH = next(c for c in CHAINS if c.id == "ethereum")
TRON = next(c for c in CHAINS if c.id == "tron")
USDT = ETH.tokens[0].address


def topic(address):
    return "0x" + address[2:].rjust(64, "0")


def log(sender, receiver, amount, index=0, token=USDT, tx="0xaa"):
    return dict(
        address=token,
        topics=[TRANSFER, topic(sender), topic(receiver)],
        data=hex(amount),
        transactionHash=tx,
        logIndex=hex(index),
    )


def make(monkeypatch, responses, threshold=10_000_000):
    events, states, meta = [], [], {}

    async def emit(event, baseline):
        events.append(event)

    async def get(key):
        return meta.get(key)

    async def put(key, value):
        meta[key] = value

    flows = Flows(emit, lambda *a: states.append(a[1:]), get, put, threshold)

    async def batch(session, chain, calls):
        return [responses(method, params) for method, params in calls]

    async def price(session, symbol):
        return {"ETH": 4000.0}.get(symbol, 1.0)

    monkeypatch.setattr(flows, "batch", batch)
    monkeypatch.setattr(flows, "price", price)
    return flows, events, states, meta


@pytest.mark.asyncio
async def test_direction_threshold_internal_and_receipts(monkeypatch):
    binance = "0x28c6c06298d514db089934071355e5743bf21d60"
    other = "0x1111111111111111111111111111111111111111"
    cold = "0xf977814e90da44bfa03b6295a0616a897441acec"

    def responses(method, params):
        if method == "eth_getLogs":
            if params[0]["topics"][1] is None:  # incoming to Binance
                return [
                    log(other, binance, 12_000_000 * 10**6, 1),
                    log(other, binance, 9 * 10**12, 2),
                ]
            return [
                log(binance, cold, 50_000_000 * 10**6, 3),
                log(binance, other, 20_000_000 * 10**6, 4),
            ]
        if method == "eth_getBlockByNumber":
            txs = [
                dict(hash="0xok", value=hex(3000 * 10**18), to=binance, **{"from": other}),
                dict(hash="0xreverted", value=hex(3000 * 10**18), to=binance, **{"from": other}),
                dict(hash="0xsmall", value=hex(10**18), to=binance, **{"from": other}),
            ]
            return dict(transactions=txs if params[0] == "0x64" else [])
        if method == "eth_getTransactionReceipt":
            return {"status": "0x1" if params[0] == "0xok" else "0x0"}
        raise AssertionError(method)

    flows, events, _, _ = make(monkeypatch, responses)
    await flows.scan(None, ETH, 100, 101)
    got = [(e["category"], e["title"]) for e in events]
    # Internal (Binance hot -> cold), below-threshold, reverted and small transfers are dropped.
    assert got == [
        ("outflow", "币安大额流出 20,000,000 USDT（$20.00M）"),
        ("inflow", "币安大额流入 12,000,000 USDT（$12.00M）"),
        ("inflow", "币安大额流入 3,000 ETH（$12.00M）"),
    ]
    first = events[1]
    assert (
        first["source_id"] == "ethereum:0xaa:1" and first["url"] == "https://etherscan.io/tx/0xaa"
    )
    assert first["i18n"]["en"]["title"] == "Binance inflow 12,000,000 USDT ($12.00M)"
    assert "去向：币安热钱包（0x28c6…1d60）" in first["i18n"]["zh"]["summary"]


@pytest.mark.asyncio
async def test_tron_addresses_and_links_use_tron_format(monkeypatch):
    hot = next(iter(Flows(None, None, None, None, 1).book["tron"]))
    outsider = tron_to_hex("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")

    def responses(method, params):
        if params[0]["topics"][1] is None:
            return []
        return [log(hot, outsider, 15_000_000 * 10**6, token=TRON.tokens[0].address, tx="0xbeef")]

    flows, events, _, _ = make(monkeypatch, responses)
    await flows.scan(None, TRON, 1, 2)
    assert events[0]["url"] == "https://tronscan.org/#/transaction/beef"
    assert f"来源：币安热钱包（{tron_from_hex(hot)[:6]}" in events[0]["body"]
    assert "去向：TR7NHq…Lj6t" in events[0]["body"]


@pytest.mark.asyncio
async def test_checkpoint_starts_at_head_advances_and_is_retained_on_failure(monkeypatch):
    calls = {"logs": 0, "heads": 0}

    def responses(method, params):
        if method == "eth_blockNumber":
            calls["heads"] += 1
            return hex(1000 if calls["heads"] == 1 else 1010)
        if method == "eth_getLogs":
            calls["logs"] += 1
            if calls["logs"] > 2:
                raise ValueError("RPC HTTP 429")
            return []
        return dict(transactions=[])

    flows, _, states, meta = make(monkeypatch, responses)
    sleeps = []

    async def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(asyncio, "sleep", sleep)
    with pytest.raises(asyncio.CancelledError):
        await flows.run(ETH)
    # First start: lookback before the safe head (1000 - 2 confirmations), then one scan.
    assert meta["flow_checkpoint:ethereum"] == str(998)
    assert states[0][0] == "polling" and states[-1] == (
        "error",
        "Ethereum: RPC failed; checkpoint retained",
    )
    assert sleeps == [12, 30]


@pytest.mark.asyncio
async def test_flow_is_stored_bilingual_and_routed_to_its_topic(tmp_path, monkeypatch):
    def responses(method, params):
        if method == "eth_getLogs" and params[0]["topics"][1] is None:
            return [log("0x" + "2" * 40, "0x28c6c06298d514db089934071355e5743bf21d60", 11 * 10**12)]
        return [] if method == "eth_getLogs" else dict(transactions=[])

    flows, events, _, _ = make(monkeypatch, responses)
    await flows.scan(None, ETH, 1, 1)
    store = Store(str(tmp_path / "db"))
    assert await store.add(events[0], chat="-100", notify=True)
    row = (await store.listing(kind="flow"))[0]
    assert set(row["i18n"]) == {"zh", "en"} and row["i18n"]["zh"]["summary"].startswith(
        "链：Ethereum"
    )
    claimed = await store.claim(set(), chinese_announcements=True)
    text = format_message(claimed)
    assert text.startswith(
        "🔴 🇨🇳 <b>币安大额流入 11,000,000 USDT（$11.00M）</b>\n🔴 🇺🇸 Binance inflow"
    )
    assert "交易详情 / Tx ↗" in text
    settings = Settings(telegram=False)
    settings.topics = {"market": "7", "announcement": "8", "flow": "9"}
    method, args = await Delivery(settings, store).request(None, claimed)
    assert method == "sendMessage" and args["json"]["message_thread_id"] == 9
    await store.close()

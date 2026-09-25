"""Large Binance on-chain inflows and outflows (ported from ohxiyu/cex.top).

A transfer from an outside address to a listed Binance address is an inflow; the reverse
is an outflow; transfers between two listed addresses are internal and ignored. Each
chain keeps a block checkpoint that only advances after its range was fully scanned, so
failures never skip blocks. ERC-20 (and TRON TRC-20 via TronGrid's Ethereum-compatible
JSON-RPC) transfers are found with server-side log filters on the address book; native
ETH is read from full Ethereum blocks and only counted after a successful receipt.
"""
# ruff: noqa: RUF001

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp

from .announcements import Emit, Status

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
STABLES = {"USDT", "USDC", "FDUSD", "USDE", "USD1"}
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ROLES = {
    "hot_wallet": ("币安热钱包", "Binance hot wallet"),
    "cold_wallet": ("币安冷钱包", "Binance cold wallet"),
    "custodian": ("币安托管 Ceffu", "Binance custody (Ceffu)"),
    "deposit": ("币安充值地址", "Binance deposit address"),
}


def tron_to_hex(address: str) -> str:
    """Base58check TRON address -> 0x-prefixed 20-byte hex used in logs and topics."""
    number = 0
    for char in address:
        number = number * 58 + B58.index(char)
    raw = number.to_bytes(25, "big")
    payload, checksum = raw[:21], raw[21:]
    if (
        payload[0] != 0x41
        or hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != checksum
    ):
        raise ValueError("Invalid TRON address")
    return "0x" + payload[1:].hex()


def tron_from_hex(hex20: str) -> str:
    payload = b"\x41" + bytes.fromhex(hex20.removeprefix("0x")[-40:])
    raw = payload + hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    number = int.from_bytes(raw, "big")
    text = ""
    while number:
        number, rest = divmod(number, 58)
        text = B58[rest] + text
    return text


@dataclass(frozen=True)
class Token:
    address: str
    symbol: str
    decimals: int
    price: str


@dataclass(frozen=True)
class Chain:
    id: str
    name: str
    rpcs: tuple[str, ...]
    explorer: str
    confirmations: int
    max_range: int  # blocks per scan, also the catch-up step
    interval: float  # seconds between scans once caught up
    lookback: int  # first start: blocks before the safe head
    tokens: tuple[Token, ...]
    native: str = ""  # price symbol when native transfers are scanned from full blocks
    tron: bool = False


def _t(address: str, symbol: str, decimals: int, price: str = "") -> Token:
    return Token(address, symbol, decimals, price or symbol)


CHAINS = (
    Chain(
        "ethereum",
        "Ethereum",
        ("https://ethereum-rpc.publicnode.com", "https://eth.drpc.org"),
        "https://etherscan.io/tx/",
        2,
        20,
        12,
        5,
        (
            _t("0xdac17f958d2ee523a2206206994597c13d831ec7", "USDT", 6),
            _t("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "USDC", 6),
            _t("0xc5f0f7b66764f6ec8c8dff7ba683102295e16409", "FDUSD", 18),
            _t("0x4c9edd5852cd905f086c759e8383e09bff1e68b3", "USDE", 18),
            _t("0x8d0d000ee44948fc98c9b98a4fa4921476f08b0d", "USD1", 18),
            _t("0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", "WBTC", 8, "BTC"),
            _t("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "WETH", 18, "ETH"),
        ),
        native="ETH",
    ),
    Chain(
        "bsc",
        "BNB Chain",
        ("https://bsc-rpc.publicnode.com", "https://bsc.drpc.org"),
        "https://bscscan.com/tx/",
        5,
        1000,
        10,
        30,
        (
            _t("0x55d398326f99059ff775485246999027b3197955", "USDT", 18),
            _t("0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d", "USDC", 18),
            _t("0xc5f0f7b66764f6ec8c8dff7ba683102295e16409", "FDUSD", 18),
            _t("0x5d3a1ff2b6bab83b63cd9ad0787074081a52ef34", "USDE", 18),
            _t("0x8d0d000ee44948fc98c9b98a4fa4921476f08b0d", "USD1", 18),
            _t("0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c", "BTCB", 18, "BTC"),
            _t("0x2170ed0880ac9a755fd29b2688956bd959f933f8", "ETH", 18),
        ),
    ),
    Chain(
        "arbitrum",
        "Arbitrum",
        ("https://arb1.arbitrum.io/rpc", "https://arbitrum-one-rpc.publicnode.com"),
        "https://arbiscan.io/tx/",
        20,
        2000,
        10,
        100,
        (
            _t("0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9", "USDT", 6),
            _t("0xaf88d065e77c8cc2239327c5edb3a432268e5831", "USDC", 6),
            _t("0x93c9932e4afa59201f0b5e63f7d816516f1669fe", "FDUSD", 18),
            _t("0x82af49447d8a07e3bd95bd0d56f35241523fbab1", "WETH", 18, "ETH"),
        ),
    ),
    Chain(
        "base",
        "Base",
        ("https://base-rpc.publicnode.com", "https://mainnet.base.org"),
        "https://basescan.org/tx/",
        5,
        500,
        10,
        20,
        (
            _t("0xfde4c96c8593536e31f229ea8f37b2ada2699bb2", "USDT", 6),
            _t("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", "USDC", 6),
            _t("0x5d3a1ff2b6bab83b63cd9ad0787074081a52ef34", "USDE", 18),
            _t("0x4200000000000000000000000000000000000006", "WETH", 18, "ETH"),
        ),
    ),
    Chain(
        "tron",
        "TRON",
        ("https://api.trongrid.io/jsonrpc",),
        "https://tronscan.org/#/transaction/",
        20,
        100,
        15,
        20,
        (_t(tron_to_hex("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"), "USDT", 6),),
        tron=True,
    ),
)
NAMES = {c.id: c.name for c in CHAINS}


def load_book(path: Path | None = None) -> dict[str, dict[str, dict[str, str]]]:
    """chain -> normalized log address (EVM/TRON hex) -> {address, type, label}."""
    path = path or Path(__file__).resolve().parents[2] / "config/exchange_addresses.json"
    book: dict[str, dict[str, dict[str, str]]] = {}
    for row in json.loads(path.read_text())["addresses"]:
        chain = row["chain"]
        if chain == "tron":
            key = tron_to_hex(row["address"])
        elif chain in NAMES:
            key = row["address"].lower()
        else:
            continue  # Solana is not scanned yet; its rows stay in the book.
        book.setdefault(chain, {})[key] = row
    return book


def short(address: str) -> str:
    return f"{address[:6]}…{address[-4:]}"


def usd_text(value: float) -> str:
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    return f"${value / 1e6:.2f}M"


def amount_text(value: float) -> str:
    return f"{value:,.0f}" if value >= 1000 else f"{value:,.4f}".rstrip("0").rstrip(".")


def party(chain: Chain, key: str, row: dict[str, str] | None) -> tuple[str, str]:
    shown = short(tron_from_hex(key) if chain.tron else key)
    if not row:
        return shown, shown
    zh, en = ROLES.get(row["type"], ("币安地址", "Binance address"))
    return f"{zh}（{shown}）", f"{en} ({shown})"


def flow_event(
    chain: Chain,
    tx: str,
    position: str,
    symbol: str,
    amount: float,
    usd: float,
    source: tuple[str, dict[str, str] | None],
    target: tuple[str, dict[str, str] | None],
) -> dict[str, Any]:
    inflow = target[1] is not None
    url = chain.explorer + (tx.removeprefix("0x") if chain.tron else tx)
    sender, receiver = party(chain, *source), party(chain, *target)
    head = f"{amount_text(amount)} {symbol}"
    zh_title = f"币安大额{'流入' if inflow else '流出'} {head}（{usd_text(usd)}）"
    en_title = f"Binance {'inflow' if inflow else 'outflow'} {head} ({usd_text(usd)})"
    zh = f"链：{chain.name}\n来源：{sender[0]}\n去向：{receiver[0]}"
    en = f"Chain: {chain.name}\nFrom: {sender[1]}\nTo: {receiver[1]}"
    return dict(
        kind="flow",
        source="binance",
        source_id=f"{chain.id}:{tx.lower()}:{position}",
        title=zh_title,
        body=zh,
        url=url,
        published=None,
        category="inflow" if inflow else "outflow",
        symbol=symbol,
        i18n={
            "zh": dict(title=zh_title, summary=zh, points="", url=url),
            "en": dict(title=en_title, summary=en, points="", url=url),
        },
    )


class Flows:
    def __init__(
        self,
        emit: Emit,
        status: Status,
        meta: Callable[[str], Awaitable[str | None]],
        set_meta: Callable[[str, str], Awaitable[None]],
        threshold: float,
    ) -> None:
        self.emit, self.status, self.meta, self.set_meta = emit, status, meta, set_meta
        self.threshold = threshold
        self.book = load_book()
        self.prices: dict[str, tuple[float, float]] = {}

    def tasks(self) -> list[tuple[str, Any]]:
        return [(f"flow-{c.id}", self.run(c)) for c in CHAINS if self.book.get(c.id)]

    async def rpc(
        self, session: aiohttp.ClientSession, chain: Chain, method: str, params: list[Any]
    ) -> Any:
        return (await self.batch(session, chain, [(method, params)]))[0]

    async def batch(
        self, session: aiohttp.ClientSession, chain: Chain, calls: list[tuple[str, list[Any]]]
    ) -> list[Any]:
        """JSON-RPC batch with endpoint fallback; any error keeps the checkpoint."""
        body = [
            {"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)
        ]
        failure: Exception = ValueError("No RPC endpoint")
        for url in chain.rpcs:
            try:
                async with session.post(url, json=body if len(body) > 1 else body[0]) as r:
                    if r.status != 200:
                        raise ValueError(f"RPC HTTP {r.status}")
                    data = await r.json(content_type=None)
                rows = data if isinstance(data, list) else [data]
                if len(rows) != len(calls):
                    raise ValueError("Incomplete RPC batch")
                results = []
                for row in sorted(rows, key=lambda x: x["id"]):
                    if "error" in row or "result" not in row:
                        raise ValueError("RPC error")
                    results.append(row["result"])
                return results
            except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                failure = exc
        raise failure

    async def price(self, session: aiohttp.ClientSession, symbol: str) -> float:
        if symbol in STABLES:
            return 1.0
        cached = self.prices.get(symbol)
        if cached and time.time() - cached[1] < 60:
            return cached[0]
        async with session.get(
            "https://api.binance.com/api/v3/ticker/price", params={"symbol": f"{symbol}USDT"}
        ) as r:
            if r.status != 200:
                raise ValueError("Price unavailable")
            value = float((await r.json())["price"])
        if value <= 0:
            raise ValueError("Invalid price")
        self.prices[symbol] = (value, time.time())
        return value

    async def run(self, chain: Chain) -> None:
        name, key = f"flow_{chain.id}", f"flow_checkpoint:{chain.id}"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            while True:
                delay = chain.interval
                try:
                    head = int(await self.rpc(session, chain, "eth_blockNumber", []), 16)
                    safe = head - chain.confirmations
                    saved = await self.meta(key)
                    if saved is None:
                        # First start follows the chain head; persisted before any scan.
                        saved = str(safe - chain.lookback)
                        await self.set_meta(key, saved)
                    start = int(saved) + 1
                    behind = safe - int(saved)
                    if start <= safe:
                        end = min(safe, start + chain.max_range - 1)
                        await self.scan(session, chain, start, end)
                        await self.set_meta(key, str(end))
                        behind = safe - end
                        if behind > 0:
                            delay = 1  # Catch up without skipping, one range at a time.
                    self.status(
                        name,
                        "polling",
                        f"{chain.name}: {len(self.book[chain.id])} Binance addresses; "
                        f"{behind} blocks behind",
                    )
                except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError):
                    self.status(name, "error", f"{chain.name}: RPC failed; checkpoint retained")
                    delay = max(chain.interval, 30)
                await asyncio.sleep(delay)

    async def scan(
        self, session: aiohttp.ClientSession, chain: Chain, start: int, end: int
    ) -> None:
        book = self.book[chain.id]
        topics = ["0x" + key[2:].rjust(64, "0") for key in book]
        tokens = {t.address: t for t in chain.tokens}
        base = {"fromBlock": hex(start), "toBlock": hex(end), "address": list(tokens)}
        outgoing, incoming = await self.batch(
            session,
            chain,
            [
                ("eth_getLogs", [dict(base, topics=[TRANSFER, topics])]),
                ("eth_getLogs", [dict(base, topics=[TRANSFER, None, topics])]),
            ],
        )
        seen = set()
        for log in [*outgoing, *incoming]:
            ident = (log["transactionHash"], log["logIndex"])
            token = tokens.get(log["address"].lower())
            if ident in seen or not token or len(log["topics"]) < 3 or log.get("removed"):
                continue
            seen.add(ident)
            sender = "0x" + log["topics"][1][-40:].lower()
            receiver = "0x" + log["topics"][2][-40:].lower()
            amount = int(log["data"], 16) / 10**token.decimals
            await self.consider(
                session,
                chain,
                log["transactionHash"],
                str(int(log["logIndex"], 16)),
                token.symbol,
                token.price,
                amount,
                sender,
                receiver,
                native=False,
            )
        if chain.native:
            # Three full blocks per batch: free fallback endpoints reject larger batches.
            for first in range(start, end + 1, 3):
                blocks = await self.batch(
                    session,
                    chain,
                    [
                        ("eth_getBlockByNumber", [hex(n), True])
                        for n in range(first, min(end, first + 2) + 1)
                    ],
                )
                for block in blocks:
                    if not block:
                        raise ValueError("Missing block")
                    for tx in block["transactions"]:
                        value = int(tx["value"], 16)
                        if not tx.get("to") or not value:
                            continue
                        await self.consider(
                            session,
                            chain,
                            tx["hash"],
                            "native",
                            chain.native,
                            chain.native,
                            value / 1e18,
                            tx["from"].lower(),
                            tx["to"].lower(),
                            native=True,
                        )

    async def consider(
        self,
        session: aiohttp.ClientSession,
        chain: Chain,
        tx: str,
        position: str,
        symbol: str,
        price_symbol: str,
        amount: float,
        sender: str,
        receiver: str,
        *,
        native: bool,
    ) -> None:
        book = self.book[chain.id]
        known_sender, known_receiver = book.get(sender), book.get(receiver)
        if bool(known_sender) == bool(known_receiver):
            return  # Unrelated to Binance, or an internal Binance transfer.
        usd = amount * await self.price(session, price_symbol)
        if usd < self.threshold:
            return
        if native:
            receipt = await self.rpc(session, chain, "eth_getTransactionReceipt", [tx])
            if not receipt:
                raise ValueError("Receipt unavailable")
            if receipt["status"] != "0x1":
                return  # Reverted: no value moved.
        if chain.tron:
            tx = tx.removeprefix("0x")
        event = flow_event(
            chain,
            tx,
            position,
            symbol,
            amount,
            usd,
            (sender, known_sender),
            (receiver, known_receiver),
        )
        await self.emit(event, False)

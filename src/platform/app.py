"""FomoBTC service: bounded ingestion, durable events, read-only API and source health."""

import asyncio
import contextlib
import fcntl
import logging
import os
import signal
import time
from pathlib import Path
from typing import Any

from aiohttp import web

from .announcements import Announcements
from .delivery import Delivery
from .market import Market
from .settings import Settings, load_settings
from .store import Store

logger = logging.getLogger("fomobtc")
VERSION = "2.1.0"


class Platform:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = Store(settings.database)
        self.queue: asyncio.Queue[tuple[dict[str, Any], bool, asyncio.Future[None]]] = (
            asyncio.Queue(maxsize=1000)
        )
        self.sources: dict[str, dict[str, Any]] = {}
        self.stats: dict[str, Any] = {}
        self.started = time.time()
        self.subscribers: set[asyncio.Queue[str]] = set()
        self.market = Market(self.emit, self.status, self.stats)
        self.collectors = Announcements(settings, self.store, self.emit, self.status)
        self.delivery = Delivery(settings, self.store)

    def status(self, source: str, state: str, detail: str) -> None:
        old = self.sources.get(source, {})
        self.sources[source] = dict(
            state=state,
            detail=detail,
            checked=time.time(),
            last_success=time.time()
            if state in {"live", "polling", "degraded"}
            else old.get("last_success"),
        )
        if state != old.get("state"):
            logger.info("source=%s state=%s detail=%s", source, state, detail)

    async def emit(self, event: dict[str, Any], baseline: bool) -> None:
        # Backpressure rather than silently dropping detected signals.
        done = asyncio.get_running_loop().create_future()
        await self.queue.put((event, baseline, done))
        await asyncio.shield(done)

    async def ingest(self) -> None:
        while True:
            event, baseline, done = await self.queue.get()
            try:
                chat = (
                    self.settings.announcement_chat or self.settings.chat
                    if event["kind"] == "announcement"
                    else self.settings.chat
                )
                if event["kind"] == "market" and "signal" in event:
                    reason = await self.store.market_update(
                        event, chat=chat, notify=self.settings.telegram
                    )
                    reasons = self.stats.setdefault("notification_decisions", {})
                    reasons[reason] = reasons.get(reason, 0) + 1
                    added = True
                else:
                    added = await self.store.add(
                        event,
                        chat=chat,
                        notify=self.settings.telegram and event["category"] != "promotion",
                        baseline=baseline,
                    )
                if added:
                    for queue in list(self.subscribers):
                        if queue.full():
                            queue.get_nowait()
                        queue.put_nowait("refresh")
                if not done.done():
                    done.set_result(None)
            except Exception as exc:
                if not done.done():
                    done.set_exception(exc)
                raise
            finally:
                self.queue.task_done()

    async def state(self) -> dict[str, Any]:
        samples = sorted(self.market.latencies)
        return dict(
            name="FomoBTC",
            version=VERSION,
            source_commit=self.settings.revision,
            uptime_seconds=int(time.time() - self.started),
            sources={
                name: dict(s, state="stale")
                if ("_stream_" in name or name.endswith("_universe") or name == "okx")
                and s["state"] in {"live", "polling", "degraded"}
                and time.time() - s["checked"]
                > (self.market.refresh * 2 if name.endswith("_universe") else 90)
                else s
                for name, s in self.sources.items()
                if s["state"] != "retired"
            },
            events=await self.store.counts(),
            ingestion_queue=self.queue.qsize(),
            market_messages=self.stats.get("market_messages", 0),
            decision_p99_ms=samples[min(len(samples) - 1, int(len(samples) * 0.99))]
            if samples
            else None,
            decision_sample_count=len(samples),
            telegram_enabled=self.settings.telegram,
            monitoring={**self.market.metrics(), **await self.store.monitoring()},
            enabled_markets=[
                m for m in ("spot", "futures") if self.settings.market and getattr(self.settings, m)
            ],
        )

    def api(self) -> web.Application:
        @web.middleware
        async def headers(request: web.Request, handler: Any) -> web.StreamResponse:
            if request.method == "OPTIONS":
                response: web.StreamResponse = web.Response(status=204)
            else:
                try:
                    response = await handler(request)
                except (ValueError, TypeError):
                    response = web.json_response({"error": "invalid query"}, status=400)
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            if request.headers.get("Origin") == self.settings.origin and self.settings.origin:
                response.headers["Access-Control-Allow-Origin"] = self.settings.origin
                response.headers["Vary"] = "Origin"
                response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            return response

        app = web.Application(middlewares=[headers], client_max_size=1024)

        async def health(request: web.Request) -> web.Response:
            return web.json_response(await self.state())

        async def ready(request: web.Request) -> web.Response:
            state = await self.state()
            failed = {
                name: s
                for name, s in state["sources"].items()
                if s["state"] in {"error", "blocked", "warming", "degraded", "stale"}
            }
            enabled = self.settings.market or self.settings.announcements
            ok = bool(self.sources) and not failed if enabled else True
            return web.json_response(dict(ready=ok, **state), status=200 if ok else 503)

        async def listing(request: web.Request) -> web.Response:
            return web.json_response(
                {
                    "events": await self.store.listing(
                        kind=request.query.get("kind", ""),
                        source=request.query.get("source", ""),
                        query=request.query.get("q", "")[:200],
                        before=float(request.query.get("before", "0")),
                        limit=max(1, min(100, int(request.query.get("limit", "50")))),
                        activity=request.query.get("activity") == "true",
                    ),
                }
            )

        async def stream(request: web.Request) -> web.StreamResponse:
            if len(self.subscribers) >= 100:
                raise web.HTTPServiceUnavailable(text="Live connection limit reached")
            response = web.StreamResponse(
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-store",
                    "X-Accel-Buffering": "no",
                }
            )
            if request.headers.get("Origin") == self.settings.origin and self.settings.origin:
                response.headers["Access-Control-Allow-Origin"] = self.settings.origin
                response.headers["Vary"] = "Origin"
            await response.prepare(request)
            queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
            self.subscribers.add(queue)
            try:
                await response.write(b"event: refresh\ndata: {}\n\n")
                while True:
                    try:
                        await asyncio.wait_for(queue.get(), timeout=15)
                        await response.write(b"event: refresh\ndata: {}\n\n")
                    except TimeoutError:
                        await response.write(b": heartbeat\n\n")
            except (ConnectionError, asyncio.CancelledError):
                pass
            finally:
                self.subscribers.discard(queue)
            return response

        app.router.add_get("/api/health", health)
        app.router.add_get("/api/ready", ready)
        app.router.add_get("/api/events", listing)
        app.router.add_get("/api/stream", stream)
        app.router.add_route("OPTIONS", "/api/{path:.*}", health)
        return app

    async def run(self) -> None:
        jobs = [asyncio.create_task(self.ingest(), name="ingestion")]
        if self.settings.telegram:
            jobs.append(asyncio.create_task(self.delivery.run(), name="delivery"))
        if self.settings.market:
            jobs.append(asyncio.create_task(self.market.flush_loop(), name="market-summaries"))
            for market in ("spot", "futures"):
                if not getattr(self.settings, market):
                    continue
                self.status(market + "_universe", "warming", "Starting")
                jobs.append(asyncio.create_task(self.market.run(market), name=market))
        if self.settings.announcements:
            for source in ("okx", "binance_announcements", "hyperliquid"):
                self.status(source, "warming", "Starting")
            jobs.extend(
                asyncio.create_task(task, name=name)
                for name, task in (
                    ("okx", self.collectors.okx()),
                    ("binance-announcements", self.collectors.binance()),
                    ("hyperliquid", self.collectors.hyperliquid()),
                )
            )
        runner = web.AppRunner(self.api(), shutdown_timeout=2)
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        try:
            await runner.setup()
            await web.TCPSite(runner, self.settings.host, self.settings.port).start()
            waiter = asyncio.create_task(stop.wait())
            done, _ = await asyncio.wait([*jobs, waiter], return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if task is not waiter:
                    task.result()
                    raise RuntimeError("A critical service stopped")
            waiter.cancel()
            await asyncio.gather(waiter, return_exceptions=True)
        finally:
            for task in jobs:
                task.cancel()
            await asyncio.gather(*jobs, return_exceptions=True)
            await runner.cleanup()
            await self.store.close()


def main() -> None:
    settings = load_settings()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    # Only one process may own this database, including during a service rename.
    Path(settings.database).parent.mkdir(parents=True, exist_ok=True)
    with open(settings.database + ".lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another FomoBTC instance owns this database") from None
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(Platform(settings).run())

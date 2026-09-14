"""Serialized SQLite transactions off the event loop; persistent delivery outbox."""

import asyncio
import hashlib
import json
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


class Store:
    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = asyncio.Lock()
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
            PRAGMA busy_timeout=5000;
            CREATE TABLE IF NOT EXISTS events (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, source TEXT NOT NULL,
              source_id TEXT NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL,
              body TEXT NOT NULL, category TEXT NOT NULL, symbol TEXT NOT NULL,
              published REAL, detected REAL NOT NULL, updated INTEGER NOT NULL,
              status TEXT NOT NULL, chat TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
              due REAL NOT NULL, sent REAL, error TEXT NOT NULL DEFAULT '',
              cooldown_key TEXT NOT NULL DEFAULT '', expires REAL NOT NULL,
              telegram_id INTEGER, dispatch_ms REAL
            );
            CREATE INDEX IF NOT EXISTS event_due ON events(status,due);
            CREATE INDEX IF NOT EXISTS event_detected ON events(detected DESC);
            CREATE INDEX IF NOT EXISTS event_cooldown ON events(cooldown_key,status);
            CREATE TABLE IF NOT EXISTS announcement_content (
              event_id TEXT PRIMARY KEY, body TEXT NOT NULL, brief TEXT NOT NULL,
              state TEXT NOT NULL, checked REAL NOT NULL, retry_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS seen (
              source TEXT, source_id TEXT, digest TEXT NOT NULL,
              PRIMARY KEY(source,source_id)
            );
            CREATE TABLE IF NOT EXISTS cooldown (key TEXT PRIMARY KEY, until REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS market_episodes (
              id TEXT PRIMARY KEY, source TEXT NOT NULL, symbol TEXT NOT NULL,
              direction INTEGER NOT NULL, last_hit REAL NOT NULL, data TEXT NOT NULL,
              notice_id TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS episode_symbol
              ON market_episodes(source,symbol,last_hit DESC);
            CREATE TABLE IF NOT EXISTS market_notice_attempt (
              key TEXT PRIMARY KEY, at REAL NOT NULL
            );
        """)
        # A crashed in-flight HTTP call may already have been accepted. Keep this explicit.
        self.db.execute(
            "UPDATE events SET status='unknown',error='interrupted delivery' WHERE status='sending'"
        )
        self.db.commit()

    async def run(self, operation: Callable[[], T]) -> T:
        async with self.lock:
            task = asyncio.create_task(asyncio.to_thread(operation))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                await task
                raise

    async def close(self) -> None:
        await self.run(self.db.close)

    async def meta(self, key: str) -> str | None:
        def get() -> str | None:
            row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return str(row[0]) if row else None

        return await self.run(get)

    async def set_meta(self, key: str, value: str) -> None:
        def put() -> None:
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value))

        await self.run(put)

    async def add(
        self,
        event: dict[str, Any],
        *,
        chat: str,
        notify: bool,
        baseline: bool = False,
        cooldown_key: str = "",
    ) -> bool:
        def write() -> bool:
            now = time.time()
            source, sid = str(event["source"]), str(event["source_id"])
            content = [event.get(k, "") for k in ("title", "body", "url", "category")]
            digest = hashlib.sha256(json.dumps(content, ensure_ascii=False).encode()).hexdigest()
            old = self.db.execute(
                "SELECT digest FROM seen WHERE source=? AND source_id=?", (source, sid)
            ).fetchone()
            if old and old[0] == digest:
                return False
            if cooldown_key:
                cool = self.db.execute(
                    "SELECT until FROM cooldown WHERE key=?", (cooldown_key,)
                ).fetchone()
                pending = self.db.execute(
                    "SELECT 1 FROM events WHERE cooldown_key=? AND status IN "
                    "('pending','sending','unknown') AND expires>?",
                    (cooldown_key, now),
                ).fetchone()
                if (cool and cool[0] > now) or pending:
                    return False
            eid = hashlib.sha256(f"{source}:{sid}:{digest}".encode()).hexdigest()[:32]
            status = "baseline" if baseline else ("pending" if notify else "archived")
            with self.db:
                # Events are immutable revisions. Revisiting a previous revision is deduplicated.
                cursor = self.db.execute(
                    """INSERT OR IGNORE INTO events
                    (id,kind,source,source_id,title,url,body,category,symbol,published,
                     detected,updated,status,chat,due,cooldown_key,expires)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        eid,
                        event["kind"],
                        source,
                        sid,
                        event["title"],
                        event.get("url", ""),
                        event.get("body", ""),
                        event.get("category", "other"),
                        event.get("symbol", ""),
                        event.get("published"),
                        now,
                        int(bool(old)),
                        status,
                        chat,
                        now,
                        cooldown_key,
                        now + (120 if event["kind"] == "market" else 3600),
                    ),
                )
                self.db.execute("INSERT OR REPLACE INTO seen VALUES (?,?,?)", (source, sid, digest))
                if cursor.rowcount > 0 and cooldown_key and not notify:
                    self.db.execute(
                        "INSERT OR REPLACE INTO cooldown VALUES (?,?)", (cooldown_key, now + 7200)
                    )
                return cursor.rowcount > 0

        return await self.run(write)

    async def market_update(self, event: dict[str, Any], *, chat: str, notify: bool) -> str:
        """One summary per directional episode; immutable, separately throttled notices."""

        def write() -> str:
            now = time.time()
            batch = event["signal"]
            source, symbol = event["source"], event["symbol"]
            direction = 1 if batch["change"] > 0 else -1
            base = f"{source.removeprefix('binance_')}_{symbol}_3m"
            with self.db:
                previous = self.db.execute(
                    "SELECT * FROM market_episodes WHERE source=? AND symbol=? "
                    "ORDER BY last_hit DESC LIMIT 1",
                    (source, symbol),
                ).fetchone()
                continuing = (
                    previous
                    and previous["direction"] == direction
                    and batch["first_hit"] - previous["last_hit"] <= 60
                )
                data = (
                    json.loads(previous["data"])
                    if continuing
                    else dict(started=batch["first_hit"], hits=0, peak_change=batch["peak_change"])
                )
                data.update(
                    {
                        k: batch[k]
                        for k in ("change", "price", "threshold", "volume", "group", "last_hit")
                    }
                )
                data["hits"] += batch["hits"]
                if abs(batch["peak_change"]) > abs(data["peak_change"]):
                    data["peak_change"] = batch["peak_change"]
                data["direction"] = direction
                eid = (
                    previous["id"]
                    if continuing
                    else hashlib.sha256(
                        f"episode:{source}:{symbol}:{batch['first_hit']}:{direction}".encode()
                    ).hexdigest()[:32]
                )
                if not continuing:
                    self.db.execute(
                        "INSERT INTO events (id,kind,source,source_id,title,url,body,category,"
                        "symbol,published,detected,updated,status,chat,due,cooldown_key,expires) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            eid,
                            "market",
                            source,
                            eid,
                            event["title"],
                            "",
                            event["body"],
                            "price",
                            symbol,
                            batch["first_hit"],
                            now,
                            0,
                            "archived",
                            "",
                            now,
                            "",
                            now,
                        ),
                    )
                else:
                    self.db.execute(
                        "UPDATE events SET title=?,body=?,updated=1 WHERE id=?",
                        (event["title"], event["body"], eid),
                    )
                self.db.execute(
                    "INSERT INTO market_episodes(id,source,symbol,direction,last_hit,data) "
                    "VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                    "last_hit=excluded.last_hit,data=excluded.data",
                    (eid, source, symbol, direction, batch["last_hit"], json.dumps(data)),
                )
                if not notify:
                    return "disabled"
                # Severity levels are threshold multiples 1x/2x/3x, capped at three.
                level = min(3, max(1, int(abs(batch["peak_change"]) / batch["threshold"])))
                key = f"{base}:{direction}:{level}"
                # Preserve legacy successful cooldowns across the additive migration.
                keys = [base, *(f"{base}:{direction}:{n}" for n in range(level, 4))]
                placeholders = ",".join("?" for _ in keys)
                cool = self.db.execute(
                    f"SELECT 1 FROM cooldown WHERE key IN ({placeholders}) AND until>?",
                    (*keys, now),
                ).fetchone()
                if cool:
                    return "cooldown"
                pending = self.db.execute(
                    f"SELECT 1 FROM events WHERE cooldown_key IN ({placeholders}) "
                    "AND (status='unknown' OR (status IN ('pending','sending') AND expires>?))",
                    (*keys, now),
                ).fetchone()
                if pending:
                    return "pending_or_unknown"
                attempt = self.db.execute(
                    "SELECT at FROM market_notice_attempt WHERE key=?", (base,)
                ).fetchone()
                if attempt and now - attempt[0] < 60:
                    return "rate_limited"
                nid = hashlib.sha256(f"notice:{eid}:{now}:{key}".encode()).hexdigest()[:32]
                title = f"{symbol} {batch['peak_change']:+.2f}% · L{level}"
                body = (
                    f"方向 {'上涨' if direction > 0 else '下跌'};阈值 {batch['threshold']}%;"
                    f"本次采样峰值;最新价格 {batch['price']}。" + event["body"]
                )
                self.db.execute(
                    "INSERT INTO events(id,kind,source,source_id,title,url,body,category,"
                    "symbol,published,detected,updated,status,chat,due,cooldown_key,expires) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        nid,
                        "market",
                        source,
                        nid,
                        title,
                        "",
                        body,
                        "price_notice",
                        symbol,
                        batch["last_hit"],
                        now,
                        0,
                        "pending",
                        chat,
                        now,
                        key,
                        now + 120,
                    ),
                )
                self.db.execute("UPDATE market_episodes SET notice_id=? WHERE id=?", (nid, eid))
                self.db.execute(
                    "INSERT OR REPLACE INTO market_notice_attempt VALUES (?,?)", (base, now)
                )
                return "queued"

        return await self.run(write)

    async def claim(self, unavailable: set[str]) -> dict[str, Any] | None:
        def take() -> dict[str, Any] | None:
            now = time.time()
            with self.db:
                self.db.execute(
                    "UPDATE events SET status='expired' WHERE status='pending' AND expires<?",
                    (now,),
                )
                # Scan only due work, highest priority first, without blocking another chat.
                rows = self.db.execute(
                    "SELECT * FROM events WHERE status='pending' AND due<=? "
                    "ORDER BY CASE category WHEN 'security' THEN 0 "
                    "WHEN 'delisting' THEN 1 ELSE 2 END, detected LIMIT 100",
                    (now,),
                ).fetchall()
                for row in rows:
                    if row["chat"] not in unavailable:
                        self.db.execute(
                            "UPDATE events SET status='sending',attempts=attempts+1 WHERE id=?",
                            (row["id"],),
                        )
                        result = dict(row)
                        result["attempts"] += 1
                        return result
                return None

        return await self.run(take)

    async def finish(
        self,
        event: dict[str, Any],
        status: str,
        *,
        delay: float = 0,
        error: str = "",
        message_id: int | None = None,
        duration: float | None = None,
    ) -> None:
        def save() -> None:
            now = time.time()
            with self.db:
                self.db.execute(
                    "UPDATE events SET status=?,due=?,sent=?,error=?,telegram_id=?,"
                    "dispatch_ms=? WHERE id=?",
                    (
                        status,
                        now + delay,
                        now if status == "sent" else None,
                        error,
                        message_id,
                        duration,
                        event["id"],
                    ),
                )
                if status == "sent" and event["cooldown_key"]:
                    self.db.execute(
                        "INSERT OR REPLACE INTO cooldown VALUES (?,?)",
                        (event["cooldown_key"], now + 7200),
                    )

        await self.run(save)

    async def content_pending(self, now: float) -> list[dict[str, Any]]:
        return await self.run(
            lambda: [
                dict(r)
                for r in self.db.execute(
                    "SELECT e.* FROM events e LEFT JOIN announcement_content c ON c.event_id=e.id "
                    "WHERE e.kind='announcement' AND (c.event_id IS NULL OR "
                    "(c.state!='ready' AND c.retry_at<?)) ORDER BY e.detected DESC LIMIT 100",
                    (now,),
                ).fetchall()
            ]
        )

    async def save_content(self, eid: str, body: str, brief: str, state: str) -> None:
        def write() -> None:
            with self.db:
                self.db.execute(
                    "INSERT OR REPLACE INTO announcement_content VALUES (?,?,?,?,?,?)",
                    (eid, body, brief, state, time.time(), time.time() + 3600),
                )

        await self.run(write)

    async def listing(
        self,
        *,
        kind: str = "",
        source: str = "",
        query: str = "",
        before: float = 0,
        limit: int = 100,
        activity: bool = False,
    ) -> list[dict[str, Any]]:
        def read() -> list[dict[str, Any]]:
            order = (
                "coalesce((SELECT last_hit FROM market_episodes WHERE id=events.id),detected)"
                if activity
                else "detected"
            )
            rows = self.db.execute(
                "SELECT * FROM events WHERE category!='price_notice' AND (?='' OR kind=?) "
                "AND (?='' OR source=?) AND (?='' OR instr(lower(title),lower(?))>0) "
                f"AND (?=0 OR detected<?) ORDER BY {order} DESC LIMIT ?",
                (kind, kind, source, source, query, query, before, before, limit),
            ).fetchall()
            private = {"chat", "cooldown_key"}
            result = []
            for row in rows:
                item = {k: v for k, v in dict(row).items() if k not in private}
                episode = self.db.execute(
                    "SELECT data,notice_id FROM market_episodes WHERE id=?", (row["id"],)
                ).fetchone()
                if episode:
                    item["signal"] = json.loads(episode["data"])
                    notice = self.db.execute(
                        "SELECT status FROM events WHERE id=?", (episode["notice_id"],)
                    ).fetchone()
                    item["notification_status"] = notice[0] if notice else "not_queued"
                if item["kind"] == "announcement":
                    content = self.db.execute(
                        "SELECT * FROM announcement_content WHERE event_id=?", (item["id"],)
                    ).fetchone()
                    item["content_state"] = content["state"] if content else "pending"
                    item["brief"] = content["brief"] if content else ""
                    item["brief_method"] = "extractive_v1"
                    item["content_checked"] = content["checked"] if content else None
                    if content and content["body"]:
                        item["body"] = content["body"]
                result.append(item)
            return result

        return await self.run(read)

    async def counts(self) -> dict[str, int]:
        return await self.run(
            lambda: dict(
                self.db.execute(
                    "SELECT status,count(*) FROM events WHERE category!='price_notice' "
                    "GROUP BY status"
                ).fetchall()
            )
        )

    async def monitoring(self) -> dict[str, Any]:
        def read() -> dict[str, Any]:
            last = self.db.execute(
                "SELECT max(t) FROM (SELECT max(last_hit) AS t FROM market_episodes "
                "UNION ALL SELECT max(detected) FROM events WHERE kind='market' "
                "AND category!='price_notice')"
            ).fetchone()[0]
            notices = dict(
                self.db.execute(
                    "SELECT status,count(*) FROM events WHERE category='price_notice' "
                    "GROUP BY status"
                ).fetchall()
            )
            return dict(last_signal=last, notification_counts=notices)

        return await self.run(read)

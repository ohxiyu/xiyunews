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
            CREATE TABLE IF NOT EXISTS seen (
              source TEXT, source_id TEXT, digest TEXT NOT NULL,
              PRIMARY KEY(source,source_id)
            );
            CREATE TABLE IF NOT EXISTS cooldown (key TEXT PRIMARY KEY, until REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
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

    async def listing(
        self,
        *,
        kind: str = "",
        source: str = "",
        query: str = "",
        before: float = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        def read() -> list[dict[str, Any]]:
            rows = self.db.execute(
                "SELECT * FROM events WHERE (?='' OR kind=?) "
                "AND (?='' OR source=?) AND (?='' OR instr(lower(title),lower(?))>0) "
                "AND (?=0 OR detected<?) ORDER BY detected DESC LIMIT ?",
                (kind, kind, source, source, query, query, before, before, limit),
            ).fetchall()
            private = {"chat", "cooldown_key"}
            return [{k: v for k, v in dict(r).items() if k not in private} for r in rows]

        return await self.run(read)

    async def counts(self) -> dict[str, int]:
        return await self.run(
            lambda: dict(
                self.db.execute("SELECT status,count(*) FROM events GROUP BY status").fetchall()
            )
        )

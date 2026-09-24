"""Serialized SQLite transactions off the event loop; persistent delivery outbox."""

import asyncio
import hashlib
import json
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import yaml

from .signals import signal_title
from .text import summarize

T = TypeVar("T")
# Sources no longer collected; their past rows stay stored but are not listed.
RETIRED_SOURCES = ("htx", "kucoin")
CATEGORIES = ("listing", "delisting", "security", "maintenance", "promotion", "other", "price", "")


class Store:
    def __init__(self, path: str) -> None:
        self.policy = yaml.safe_load(
            (Path(__file__).resolve().parents[2] / "config/thresholds.yaml").read_text()
        )["market_alerts"]
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
            CREATE INDEX IF NOT EXISTS event_symbol_time ON events(symbol,detected DESC);
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
            CREATE TABLE IF NOT EXISTS alert_policy_state (
              key TEXT PRIMARY KEY, at REAL NOT NULL, armed INTEGER NOT NULL,
              breakout INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS announcement_alias (
              catalog INTEGER NOT NULL, published REAL NOT NULL, event_id TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS alias_time ON announcement_alias(catalog,published);
            CREATE TABLE IF NOT EXISTS announcement_i18n (
              event_id TEXT NOT NULL, lang TEXT NOT NULL, title TEXT NOT NULL,
              summary TEXT NOT NULL, points TEXT NOT NULL, url TEXT NOT NULL,
              method TEXT NOT NULL, PRIMARY KEY(event_id, lang)
            );
            CREATE TABLE IF NOT EXISTS market_notice_attempt (
              key TEXT PRIMARY KEY, at REAL NOT NULL
            );
        """)
        # Telegram language actually sent, and whether a later Chinese edit was applied.
        columns = {r[1] for r in self.db.execute("PRAGMA table_info(events)")}
        for name in ("sent_lang", "edit_state"):
            if name not in columns:
                self.db.execute(f"ALTER TABLE events ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
        columns = {r[1] for r in self.db.execute("PRAGMA table_info(announcement_content)")}
        for name in ("title", "language", "url"):
            if name not in columns:
                self.db.execute(
                    f"ALTER TABLE announcement_content ADD COLUMN {name} TEXT NOT NULL DEFAULT ''"
                )
        # A crashed in-flight HTTP call may already have been accepted. Keep this explicit.
        self.db.execute(
            "UPDATE events SET status='unknown',error='interrupted delivery' WHERE status='sending'"
        )
        # One-time conservative carryover from the previous policy; no historical replay.
        if not self.db.execute("SELECT 1 FROM meta WHERE key='alert_policy_v2'").fetchone():
            now = time.time()
            for row in self.db.execute(
                "SELECT e.source,e.symbol,e.detected,m.direction FROM events e "
                "JOIN market_episodes m ON m.id=e.id WHERE e.detected>? ORDER BY e.detected",
                (now - self.policy["burst"]["cooldown_seconds"],),
            ).fetchall():
                key = f"{row['source']}:{row['symbol']}:burst:{row['direction']}"
                self.db.execute(
                    "INSERT OR REPLACE INTO alert_policy_state VALUES (?,?,0,0)",
                    (key, row["detected"]),
                )
            self.db.execute(
                "UPDATE events SET status='expired',error='policy replaced' "
                "WHERE category='price_notice' AND status='pending'"
            )
            self.db.execute("INSERT INTO meta VALUES ('alert_policy_v2','1')")
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
            content = [event.get(k, "") for k in ("title", "body", "url")]
            digest = hashlib.sha256(json.dumps(content, ensure_ascii=False).encode()).hexdigest()
            old = self.db.execute(
                "SELECT digest FROM seen WHERE source=? AND source_id=?", (source, sid)
            ).fetchone()
            # Rows seen before 2.2 also hashed the derived category, whose rules may have
            # changed since; a category change alone is not a content revision.
            legacy = {
                hashlib.sha256(
                    json.dumps([*content, name], ensure_ascii=False).encode()
                ).hexdigest()
                for name in CATEGORIES
            }
            if old and (old[0] == digest or old[0] in legacy):
                if event.get("i18n"):
                    # An official translation can be listed after the original was stored.
                    latest = self.db.execute(
                        "SELECT id FROM events WHERE source=? AND source_id=? "
                        "ORDER BY detected DESC LIMIT 1",
                        (source, sid),
                    ).fetchone()
                    if latest:
                        with self.db:
                            self._save_i18n(latest[0], event["i18n"], "official", replace=False)
                return False
            alias = event.get("alias")
            if alias and not old:
                # The stream (English, instant) and website (Chinese, link) copies of one
                # Binance article share catalog and publish time; notify only once.
                twin = self.db.execute(
                    "SELECT event_id FROM announcement_alias WHERE catalog=? "
                    "AND abs(published-?)<=5 ORDER BY abs(published-?) LIMIT 1",
                    (alias[0], alias[1], alias[1]),
                ).fetchone()
                if twin:
                    with self.db:
                        if sid.startswith("cms:"):
                            # Upgrade the stream event to the website article; content is
                            # re-fetched in Chinese. A sent notification is never repeated.
                            moved = self.db.execute(
                                "UPDATE events SET source_id=?,url=? WHERE id=? "
                                "AND source_id NOT LIKE 'cms:%'",
                                (sid, event.get("url", ""), twin[0]),
                            )
                            if moved.rowcount:
                                self.db.execute(
                                    "DELETE FROM announcement_content WHERE event_id=?",
                                    (twin[0],),
                                )
                        self.db.execute(
                            "INSERT OR REPLACE INTO seen VALUES (?,?,?)", (source, sid, digest)
                        )
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
                if cursor.rowcount > 0 and event.get("i18n"):
                    self._save_i18n(eid, event["i18n"], "official")
                if cursor.rowcount > 0 and alias:
                    self.db.execute(
                        "INSERT INTO announcement_alias VALUES (?,?,?)", (alias[0], alias[1], eid)
                    )
                if cursor.rowcount > 0 and cooldown_key and not notify:
                    self.db.execute(
                        "INSERT OR REPLACE INTO cooldown VALUES (?,?)", (cooldown_key, now + 7200)
                    )
                return cursor.rowcount > 0

        return await self.run(write)

    def _save_i18n(
        self, eid: str, versions: dict[str, dict[str, str]], method: str, replace: bool = True
    ) -> None:
        verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
        for lang, v in versions.items():
            summary, points = summarize(v["title"], v.get("body", ""), lang)
            self.db.execute(
                f"{verb} INTO announcement_i18n VALUES (?,?,?,?,?,?,?)",
                (eid, lang, v["title"][:500], summary, points, v.get("url", ""), method),
            )

    async def save_i18n(self, eid: str, versions: dict[str, dict[str, str]], method: str) -> None:
        def write() -> None:
            with self.db:
                self._save_i18n(eid, versions, method)

        await self.run(write)

    def _i18n(self, eid: str) -> dict[str, dict[str, str]]:
        return {
            r["lang"]: {k: r[k] for k in ("title", "summary", "points", "url", "method")}
            for r in self.db.execute("SELECT * FROM announcement_i18n WHERE event_id=?", (eid,))
        }

    async def pending_edits(self, since: float) -> list[dict[str, Any]]:
        """Sent announcements whose Chinese version arrived after a non-Chinese push."""

        def read() -> list[dict[str, Any]]:
            rows = self.db.execute(
                "SELECT e.* FROM events e JOIN announcement_i18n i ON i.event_id=e.id "
                "AND i.lang='zh' WHERE e.kind='announcement' AND e.status='sent' "
                "AND e.telegram_id IS NOT NULL AND e.sent_lang NOT IN ('', 'zh') "
                "AND e.edit_state='' AND e.sent>? ORDER BY e.sent LIMIT 5",
                (since,),
            ).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["i18n"] = self._i18n(row["id"])["zh"]
                item["lang"] = "zh"
                result.append(item)
            return result

        return await self.run(read)

    async def mark_edit(self, eid: str, state: str) -> None:
        def write() -> None:
            with self.db:
                self.db.execute("UPDATE events SET edit_state=? WHERE id=?", (state, eid))

        await self.run(write)

    async def market_rearm(self, source: str, symbol: str, direction: int) -> None:
        def write() -> None:
            with self.db:
                self.db.execute(
                    "UPDATE alert_policy_state SET armed=1 WHERE key=?",
                    (f"{source}:{symbol}:burst:{direction}",),
                )

        await self.run(write)

    async def market_update(
        self,
        event: dict[str, Any],
        *,
        chat: str,
        notify: bool,
    ) -> str:
        """Atomic policy gates and a shared immutable web/delivery event."""

        def write() -> str:
            now = time.time()
            batch = event["signal"]
            if batch.get("policy_version") != 2 or event["source"] != "binance_spot":
                return "unsupported_policy"
            symbol = event["symbol"].upper()
            accepted = []
            with self.db:
                for c in batch["components"]:
                    if (
                        c["type"] not in ("burst", "trend")
                        or c["direction"] not in (-1, 1)
                        or c["direction"] * c["change"] + 1e-9 < c["threshold"]
                        or now - c["at"] > 10
                        or c["at"] > now + 2
                    ):
                        continue
                    key = f"{event['source']}:{symbol}:{c['type']}:{c['direction']}"
                    old = self.db.execute(
                        "SELECT * FROM alert_policy_state WHERE key=?", (key,)
                    ).fetchone()
                    episode = c["at"]
                    breakout = int(c.get("breakout", False))
                    if old:
                        if c["type"] == "burst":
                            if (
                                not old["armed"]
                                or c["crossed_at"]
                                < old["at"] + self.policy["burst"]["cooldown_seconds"]
                            ):
                                continue
                        elif c["at"] < old["at"] + self.policy["trend"]["cooldown_seconds"]:
                            if not breakout or old["breakout"] or c["at"] <= old["at"]:
                                continue
                            episode = old["at"]  # Extra breakout doesn't restart the 6h episode.
                    self.db.execute(
                        "INSERT OR REPLACE INTO alert_policy_state VALUES (?,?,0,?)",
                        (key, episode, breakout),
                    )
                    accepted.append(c)
                if not accepted:
                    return "policy_limited"
                title = signal_title(symbol, accepted)
                data = dict(batch, components=accepted)
                data["direction"] = accepted[0]["direction"]
                data["started"] = min(c["at"] for c in accepted)
                data["last_hit"] = max(c["at"] for c in accepted)
                eid = hashlib.sha256(
                    f"v2:{event['source']}:{symbol}:{json.dumps(accepted, sort_keys=True)}".encode()
                ).hexdigest()[:32]
                nid = eid + "n" if notify else ""
                hold = self.policy["digest"]["hold_seconds"]
                for record, category, status, target, due, expires in [
                    (eid, "price", "archived", "", now, now),
                    *(
                        [(nid, "price_notice", "pending", chat, now + hold, now + 120)]
                        if notify
                        else []
                    ),
                ]:
                    self.db.execute(
                        "INSERT INTO events(id,kind,source,source_id,title,url,body,category,"
                        "symbol,published,detected,updated,status,chat,due,cooldown_key,expires) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            record,
                            "market",
                            event["source"],
                            record,
                            title,
                            "",
                            "",
                            category,
                            symbol,
                            data["started"],
                            now,
                            0,
                            status,
                            target,
                            due,
                            "",
                            expires,
                        ),
                    )
                self.db.execute(
                    "INSERT INTO market_episodes VALUES (?,?,?,?,?,?,?)",
                    (
                        eid,
                        event["source"],
                        symbol,
                        data["direction"],
                        data["last_hit"],
                        json.dumps(data),
                        nid,
                    ),
                )
                return "queued" if notify else "disabled"

        return await self.run(write)

    async def claim(
        self, unavailable: set[str], *, chinese_announcements: bool = False
    ) -> dict[str, Any] | None:
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
                    "AND (?=0 OR kind!='announcement' OR EXISTS("
                    "SELECT 1 FROM announcement_content c "
                    "WHERE c.event_id=events.id AND c.state='ready' "
                    "AND c.language IN ('zh','en','ko'))) "
                    "ORDER BY CASE category WHEN 'security' THEN 0 "
                    "WHEN 'delisting' THEN 1 ELSE 2 END, detected LIMIT 100",
                    (now, int(chinese_announcements)),
                ).fetchall()
                for row in rows:
                    if row["chat"] not in unavailable:
                        self.db.execute(
                            "UPDATE events SET status='sending',attempts=attempts+1 WHERE id=?",
                            (row["id"],),
                        )
                        result = dict(row)
                        if chinese_announcements and result["kind"] == "announcement":
                            content = self.db.execute(
                                "SELECT * FROM announcement_content WHERE event_id=?", (row["id"],)
                            ).fetchone()
                            result["title"] = content["title"] or result["title"]
                            result["body"] = content["brief"]
                            result["url"] = content["url"] or result["url"]
                        result["attempts"] += 1
                        if result["kind"] == "announcement":
                            versions = self._i18n(row["id"])
                            preferred: list[str] = [x for x in ("zh", "en") if x in versions]
                            lang = (preferred or list(versions) or [""])[0]
                            result["i18n"] = versions.get(lang)
                            result["lang"] = lang
                        if result["category"] == "price_notice":
                            result["members"] = self._claim_digest(result, now)
                        return result
                return None

        return await self.run(take)

    def _claim_digest(self, leader: dict[str, Any], now: float) -> list[dict[str, Any]]:
        """Claim every due market notice for the same chat into one Telegram message."""
        rows = self.db.execute(
            "SELECT id,title,symbol,detected FROM events WHERE status='pending' AND due<=? "
            "AND category='price_notice' AND chat=? AND id!=? ORDER BY detected LIMIT ?",
            (now, leader["chat"], leader["id"], self.policy["digest"]["max_items"] - 1),
        ).fetchall()
        members = [{k: leader[k] for k in ("id", "title", "symbol", "detected")}]
        members += [dict(r) for r in rows]
        for member in members[1:]:
            self.db.execute(
                "UPDATE events SET status='sending',attempts=attempts+1 WHERE id=?",
                (member["id"],),
            )
        for member in members:
            episode = self.db.execute(
                "SELECT direction FROM market_episodes WHERE notice_id=?", (member["id"],)
            ).fetchone()
            member["direction"] = episode[0] if episode else 0
        return members

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
                # A digest shares one Telegram message and one outcome across its notices.
                for eid in [m["id"] for m in event.get("members") or [event]]:
                    self.db.execute(
                        "UPDATE events SET status=?,due=?,sent=?,error=?,telegram_id=?,sent_lang=?,"
                        "dispatch_ms=? WHERE id=?",
                        (
                            status,
                            now + delay,
                            now if status == "sent" else None,
                            error,
                            message_id,
                            event.get("lang", "") if status == "sent" else "",
                            duration,
                            eid,
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
                    "WHERE e.kind='announcement' AND e.status!='baseline' "
                    "AND coalesce(e.published,e.detected)>=? AND (c.event_id IS NULL OR "
                    "(c.state!='ready' AND c.retry_at<?) OR NOT EXISTS("
                    "SELECT 1 FROM announcement_i18n i WHERE i.event_id=e.id)) "
                    "ORDER BY e.detected DESC LIMIT 100",
                    (now - 86400, now),
                ).fetchall()
            ]
        )

    async def save_content(
        self,
        eid: str,
        body: str,
        brief: str,
        state: str,
        *,
        title: str = "",
        language: str = "",
        url: str = "",
    ) -> None:
        def write() -> None:
            with self.db:
                self.db.execute(
                    "INSERT OR REPLACE INTO announcement_content VALUES (?,?,?,?,?,?,?,?,?)",
                    (eid, body, brief, state, time.time(), time.time() + 60, title, language, url),
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
            order = "detected"
            rows = self.db.execute(
                # Market-list baselines are the pairs that already existed, not news.
                "SELECT * FROM events WHERE category!='price_notice' AND (?='' OR kind=?) "
                "AND NOT (status='baseline' AND source_id LIKE 'market:%') "
                f"AND source NOT IN ({','.join('?' * len(RETIRED_SOURCES))}) "
                "AND (?=0 OR source!='binance_futures') "
                "AND (?='' OR source=?) AND (?='' OR instr(lower(title),lower(?))>0) "
                f"AND (?=0 OR detected<?) ORDER BY {order} DESC LIMIT ?",
                (
                    kind,
                    kind,
                    *RETIRED_SOURCES,
                    int(activity),
                    source,
                    source,
                    query,
                    query,
                    before,
                    before,
                    limit,
                ),
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
                        "SELECT status,sent FROM events WHERE id=?", (episode["notice_id"],)
                    ).fetchone()
                    item["notification_status"] = notice[0] if notice else "not_queued"
                    item["notification_sent"] = notice[1] if notice else None
                if item["kind"] == "announcement":
                    content = self.db.execute(
                        "SELECT * FROM announcement_content WHERE event_id=?", (item["id"],)
                    ).fetchone()
                    item["content_state"] = content["state"] if content else "pending"
                    item["brief"] = content["brief"] if content else ""
                    item["brief_method"] = "extractive_v1"
                    item["i18n"] = self._i18n(item["id"])
                    item["content_language"] = content["language"] if content else ""
                    if content and content["language"] == "zh":
                        item["original_title"] = item["title"]
                        item["title"] = content["title"] or item["title"]
                        item["url"] = content["url"] or item["url"]
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

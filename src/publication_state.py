"""Independent server publication state. Git files remain audit/export snapshots."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from contextlib import contextmanager

PRODUCERS = {"xiyu.news Feed Collection", "xiyu.news Daily Edition",
    "xiyu.news X Distribution", "xiyunews Cloudflare"}
DOCUMENTS = {"data/staging-items.json": "staging",
    "data/qualified-cache.json": "qualified",
    "docs/_data/events.json": "events", "docs/_data/event-legacy-urls.json": "event_urls",
    "docs/_data/bmtnews_state.json": "daily"}
_stores = {}


class StateConflict(ValueError):
    """Two independent writers changed the same state; preserve both, stop."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def signature(text):
    return hashlib.sha256(text.encode()).hexdigest()


class PublicationState:
    def __init__(self, directory: Path):
        if directory.is_symlink():
            raise ValueError("state directory symlink")
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.stat().st_uid != os.getuid():
            raise ValueError("state directory belongs to another account")
        self.path = directory / "publication.sqlite3"
        if self.path.is_symlink():
            raise ValueError("state database symlink")
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS publication_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS publication_documents (name TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL, source_digest TEXT NOT NULL, dirty INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS ai_cache (kind TEXT NOT NULL, key TEXT NOT NULL, record TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(kind,key))")
            db.execute("CREATE TABLE IF NOT EXISTS publication_runs (id TEXT PRIMARY KEY, kind TEXT NOT NULL, edition TEXT NOT NULL, report TEXT NOT NULL, recorded_at REAL NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS publication_editions (date TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL)")
            # Preserve the current selection when upgrading, even before the
            # next day replaces the single current-document pointer.
            current = db.execute("SELECT payload FROM publication_documents WHERE name='daily'").fetchone()
            if current:
                self._remember_edition(db, json.loads(current[0]))
            db.execute("INSERT OR IGNORE INTO publication_meta VALUES ('schema','1')")
            if db.execute("SELECT value FROM publication_meta WHERE key='schema'").fetchone()[0] != "1":
                raise ValueError("unsupported publication schema")
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        try:
            connection.execute("PRAGMA busy_timeout=30000")
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                yield connection
        finally:
            connection.close()

    def load_document(self, name, incoming, *, primary=False, reconcile=None):
        text = canonical(incoming) if incoming is not None else None
        digest = signature(text) if text is not None else ""
        with self.connect() as db:
            row = db.execute("SELECT payload,digest,source_digest,dirty FROM publication_documents WHERE name=?", (name,)).fetchone()
            if row is None:
                if text is None:
                    return None
                db.execute("INSERT INTO publication_documents VALUES(?,?,?,?,0)", (name,text,digest,digest))
                return incoming
            payload, current, source, dirty = row
            if primary or text is None or digest == source:
                return json.loads(payload)
            if digest == current:
                # A producer can reread its own export before Git push. Equality
                # proves content, never durability; only an explicit ACK does.
                return json.loads(payload)
            if dirty:
                if reconcile is not None:
                    # Only a domain-specific, conservative receipt reconciliation
                    # may establish a new audit base. Never discard local state.
                    resolved = canonical(reconcile(json.loads(payload), incoming))
                    resolved_digest = signature(resolved)
                    result = db.execute(
                        "UPDATE publication_documents SET payload=?,digest=?,source_digest=?,dirty=? "
                        "WHERE name=? AND digest=? AND source_digest=? AND dirty=1",
                        (resolved, resolved_digest, digest, int(resolved_digest != digest),
                         name, current, source),
                    )
                    if result.rowcount != 1:
                        raise StateConflict("publication state changed during reconciliation: " + name)
                    return json.loads(resolved)
                raise StateConflict("unpublished local state conflicts with a changed audit snapshot: " + name)
            db.execute("UPDATE publication_documents SET payload=?,digest=?,source_digest=?,dirty=0 WHERE name=?", (text,digest,digest,name))
            return incoming

    def save_document(self, name, value):
        text = canonical(value)
        digest = signature(text)
        with self.connect() as db:
            if name == "daily":
                previous = db.execute("SELECT payload FROM publication_documents WHERE name='daily'").fetchone()
                if previous:
                    self._remember_edition(db, json.loads(previous[0]))
                self._remember_edition(db, value)
            db.execute("INSERT INTO publication_documents VALUES(?,?,?,?,1) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload,digest=excluded.digest,dirty=1", (name,text,digest,""))

    @staticmethod
    def _remember_edition(db, value):
        from datetime import date
        if not value.get("items"):
            return
        # Queue gates use this storage module before dependency installation.
        # Producers already validate DailyFeedState; recovery consumers validate
        # it again. Capture its original JSON here without importing Pydantic.
        day = value.get("date")
        if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
            raise ValueError("edition date must be canonical ISO date")
        if not isinstance(value["items"], list) or any(not isinstance(item, dict) for item in value["items"]):
            raise ValueError("edition items must be JSON records")
        text = canonical(value)
        db.execute("INSERT INTO publication_editions VALUES(?,?,?) ON CONFLICT(date) DO UPDATE SET payload=excluded.payload,digest=excluded.digest",
                   (day, text, signature(text)))
        # Tiny selected-public-text snapshots; keep all generated editions.
        # Pending publication is never discarded by a rolling date cutoff.

    def remember_edition(self, value):
        with self.connect() as db:
            self._remember_edition(db, value)

    def saved_editions(self):
        with self.connect() as db:
            result = []
            for payload, digest in db.execute("SELECT payload,digest FROM publication_editions ORDER BY date"):
                if signature(payload) != digest:
                    raise StateConflict("saved edition checksum mismatch")
                result.append(json.loads(payload))
            return result

    def acknowledge_document(self, name, value):
        """Advance the audit base only after the exact Git checkpoint succeeds."""
        self.acknowledge_documents({name: value})

    def acknowledge_documents(self, values):
        """Confirm an entire exported snapshot atomically, preserving newer work."""
        with self.connect() as db:
            for name, value in values.items():
                text = canonical(value)
                digest = signature(text)
                result = db.execute(
                    "UPDATE publication_documents SET source_digest=?,dirty=0 "
                    "WHERE name=? AND digest=? AND payload=?",
                    (digest, name, digest, text),
                )
                if result.rowcount != 1:
                    raise StateConflict("publication state changed before checkpoint acknowledgement: " + name)

    def load_cache(self, fallback):
        with self.connect() as db:
            if db.execute("SELECT value FROM publication_meta WHERE key='cache_initialized'").fetchone() is None:
                self._save_cache(db, fallback)
                db.execute("INSERT INTO publication_meta VALUES('cache_initialized','1')")
            result = {"version": 1, "entries": {}, "prefilter_batches": {}, "relation_pairs": {}}
            for kind,key,record in db.execute("SELECT kind,key,record FROM ai_cache"):
                if kind not in result or not isinstance(result[kind], dict):
                    raise ValueError("unknown cache namespace")
                result[kind][key] = json.loads(record)
            return result

    def _save_cache(self, db, payload):
        if not isinstance(payload, dict) or payload.get("version") != 1:
            payload = {"version": 1}
        previous = {(kind,key): digest for kind,key,digest in db.execute("SELECT kind,key,digest FROM ai_cache")}
        retained = set()
        for kind in ("entries", "prefilter_batches", "relation_pairs"):
            rows = payload.get(kind, {})
            if not isinstance(rows, dict):
                raise ValueError("invalid cache snapshot namespace")
            for key,record in rows.items():
                if not isinstance(key, str) or not isinstance(record, dict):
                    continue
                text = canonical(record)
                digest = signature(text)
                retained.add((kind,key))
                if previous.get((kind,key)) != digest:
                    db.execute("INSERT INTO ai_cache VALUES(?,?,?,?) ON CONFLICT(kind,key) DO UPDATE SET record=excluded.record,digest=excluded.digest", (kind,key,text,digest))
        db.executemany("DELETE FROM ai_cache WHERE kind=? AND key=?", previous.keys() - retained)

    def save_cache(self, payload):
        with self.connect() as db:
            self._save_cache(db, payload)
            db.execute("INSERT OR REPLACE INTO publication_meta VALUES('cache_initialized','1')")

    def save_report(self, report):
        invocation = os.environ.get("GITHUB_RUN_ID", "local") + ":" + os.environ.get("GITHUB_RUN_ATTEMPT", "1") + ":" + report.get("kind", "unknown")
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO publication_runs VALUES(?,?,?,?,?)", (invocation,report.get("kind","unknown"),report.get("date","unknown"),canonical(report),time.time()))
            db.execute("DELETE FROM publication_runs WHERE id NOT IN (SELECT id FROM publication_runs ORDER BY recorded_at DESC LIMIT 200)")

    def latest_edition_metrics(self, edition):
        with self.connect() as db:
            rows = db.execute("SELECT report FROM publication_runs WHERE kind='daily_publish' AND edition=? ORDER BY recorded_at DESC", (edition,))
            for (raw,) in rows:
                metrics = json.loads(raw).get("metrics", {})
                if metrics.get("edition_candidates"):
                    return metrics
        return {}

    def bootstrap(self, cache, documents):
        # Validate/canonicalize ALL supplied data before a single transaction.
        prepared = {name: canonical(value) for name,value in documents.items()}
        canonical(cache)
        for kind in ("entries", "prefilter_batches", "relation_pairs"):
            rows = cache.get(kind, {})
            if not isinstance(rows, dict) or any(not isinstance(key,str) or not isinstance(value,dict) for key,value in rows.items()):
                raise ValueError("legacy cache namespace is not preservable")
        inserted = []
        cache_imported = False
        with self.connect() as db:
            if db.execute("SELECT value FROM publication_meta WHERE key='cache_initialized'").fetchone() is None:
                self._save_cache(db, cache)
                db.execute("INSERT INTO publication_meta VALUES('cache_initialized','1')")
                cache_imported = True
            for name,text in prepared.items():
                if db.execute("SELECT 1 FROM publication_documents WHERE name=?", (name,)).fetchone() is None:
                    digest = signature(text)
                    db.execute("INSERT INTO publication_documents VALUES(?,?,?,?,0)", (name,text,digest,digest))
                    inserted.append(name)
            counts = {kind: count for kind,count in db.execute("SELECT kind,COUNT(*) FROM ai_cache GROUP BY kind")}
            if cache_imported:
                restored = {kind:{} for kind in ("entries", "prefilter_batches", "relation_pairs")}
                for kind,key,record in db.execute("SELECT kind,key,record FROM ai_cache"):
                    restored[kind][key] = json.loads(record)
                if canonical(restored) != canonical({kind:cache.get(kind,{}) for kind in restored}):
                    raise ValueError("legacy scores or relations changed during import")
        # Existing primary state is never overwritten by repeated bootstrap.
        return {"inserted_documents": inserted, "cache_rows": counts, "cache_imported": cache_imported}

    def verify(self):
        with self.connect() as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("publication database integrity failed")
            for payload,digest in db.execute("SELECT payload,digest FROM publication_documents"):
                if signature(payload) != digest or canonical(json.loads(payload)) != payload:
                    raise ValueError("publication document integrity failed")
            for record,digest in db.execute("SELECT record,digest FROM ai_cache"):
                if signature(record) != digest or canonical(json.loads(record)) != record:
                    raise ValueError("publication cache integrity failed")
            for payload,digest in db.execute("SELECT payload,digest FROM publication_editions"):
                if signature(payload) != digest or canonical(json.loads(payload)) != payload:
                    raise ValueError("saved edition integrity failed")
            return {"verified": True, "documents": db.execute("SELECT COUNT(*) FROM publication_documents").fetchone()[0],
                "cache_rows": db.execute("SELECT COUNT(*) FROM ai_cache").fetchone()[0],
                "runs": db.execute("SELECT COUNT(*) FROM publication_runs").fetchone()[0]}


def active_store():
    remote = os.environ.get("XIYUNEWS_STATE_BACKEND") == "cloudflare"
    directory = os.environ.get("XIYUNEWS_STATE_DIR")
    if not directory and not remote:
        return None
    if os.environ.get("GITHUB_ACTIONS") == "true" and (os.environ.get("GITHUB_REPOSITORY") != "ohxiyu/xiyunews" or os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_WORKFLOW") not in PRODUCERS):
        return None  # Tests/PRs/preview builds never touch business caches.
    if remote:
        from .edge_state import location, EdgePublicationState
        path = location()
    else:
        path = Path(directory)
    if not path.is_absolute():
        raise ValueError("publication state requires an absolute directory")
    key = ("cloudflare:" if remote else "") + str(path)
    if key not in _stores:
        _stores[key] = EdgePublicationState(path) if remote else PublicationState(path)
    return _stores[key]


def document_key(path):
    try:
        return DOCUMENTS.get(Path(path).resolve().relative_to(Path.cwd().resolve()).as_posix())
    except ValueError:
        return None


def read_document(path, *, name=None, primary=False, reconcile=None):
    path = Path(path)
    key = name or document_key(path)
    store = active_store() if key else None
    incoming = json.loads(path.read_text()) if path.exists() else None
    return store.load_document(key, incoming, primary=primary, reconcile=reconcile) if store else incoming


def acknowledge_document(path, value, *, name=None):
    key = name or document_key(path)
    store = active_store() if key else None
    if store:
        store.acknowledge_document(key, value)


def write_document(path, value, *, name=None):
    from ._file_utils import _atomic_write_text
    path = Path(path)
    key = name or document_key(path)
    store = active_store() if key else None
    if store:
        store.save_document(key, value)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def acknowledge_published_snapshot(*, reader_only=False):
    """Read back the real remote commit after the publication action succeeded.

    Local exports, retained refs, and action exit status alone cannot certify
    which bytes reached Git. No business writes occur if any comparison fails.
    """
    import subprocess
    store = active_store()
    if store is None:
        return {"acknowledged": [], "reason": "no production state backend"}
    subprocess.run(["git", "fetch", "--depth=1", "origin",
                    "+gh-pages:refs/remotes/origin/gh-pages"], check=True)
    sha = subprocess.check_output(["git", "rev-parse", "origin/gh-pages"], text=True).strip()
    values = {}
    for relative, name in DOCUMENTS.items():
        if reader_only and name in {"events", "event_urls"}:
            continue
        if not relative.startswith("docs/") or not Path(relative).is_file():
            continue
        local = json.loads(Path(relative).read_text())
        remote = json.loads(subprocess.check_output(
            ["git", "show", sha + ":" + relative.removeprefix("docs/")], text=True))
        if canonical(local) != canonical(remote):
            raise StateConflict("published bytes differ from exported document: " + name)
        with store.connect() as db:
            exists = db.execute("SELECT 1 FROM publication_documents WHERE name=?", (name,)).fetchone()
        if exists:
            values[name] = remote
    store.acknowledge_documents(values)
    return {"acknowledged": sorted(values), "artifact_commit": sha}


def restore_published_documents():
    """Materialize durable state over the restored Git mirrors before rendering.

    After a failed publication, renderers may already see newer SQLite state.
    The next producer must export that catalog too, not just its HTML/API.
    Reconcile every input before changing any workspace file; never ACK here.
    """
    from ._file_utils import _atomic_write_text
    if active_store() is None:
        return {"restored": []}
    values = {}
    for relative in DOCUMENTS:
        if relative.startswith("docs/") and Path(relative).is_file():
            values[relative] = read_document(relative)
    for relative, value in values.items():
        _atomic_write_text(Path(relative), json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return {"restored": sorted(values)}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--acknowledge-published", action="store_true")
    parser.add_argument("--reader-only", action="store_true")
    parser.add_argument("--restore-published", action="store_true")
    args = parser.parse_args()
    if args.restore_published:
        print(json.dumps(restore_published_documents()))
        return
    if args.acknowledge_published:
        print(json.dumps(acknowledge_published_snapshot(reader_only=args.reader_only)))
        return
    store = active_store()
    if store is None:
        raise ValueError("trusted production SQLite environment required")
    if args.bootstrap:
        root = args.bootstrap
        names = {"staging-items.json":"staging",
            "bmtnews_state.json":"daily", "x-queue.json":"x_queue"}
        documents = {name: json.loads((root / filename).read_text()) for filename,name in names.items() if (root / filename).exists()}
        from .edition import StagingState
        from .daily_feed import DailyFeedState
        from .x_queue import validate as validate_x
        if "staging" in documents:
            StagingState.model_validate(documents["staging"])
        if "daily" in documents:
            DailyFeedState.model_validate(documents["daily"])
        if "x_queue" in documents:
            validate_x(documents["x_queue"])
        cache = json.loads((root / "analysis-cache.json").read_text())
        if not isinstance(cache, dict) or cache.get("version") != 1 or not isinstance(cache.get("entries"), dict):
            raise ValueError("invalid legacy cache; do not mark migration complete")
        result = store.bootstrap(cache, documents)
        # Prove new imports exactly equal their canonical inputs, not merely counts.
        with store.connect() as db:
            for name in result["inserted_documents"]:
                digest = db.execute("SELECT digest FROM publication_documents WHERE name=?", (name,)).fetchone()[0]
                if digest != signature(canonical(documents[name])):
                    raise ValueError("migrated document mismatch")
        print(json.dumps({"migration": result, **store.verify()}))
    elif args.verify:
        print(json.dumps(store.verify()))
    else:
        parser.error("use --bootstrap snapshot-directory or --verify")


if __name__ == "__main__":
    main()

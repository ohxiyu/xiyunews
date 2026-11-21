"""Independent server publication state. Git files remain audit/export snapshots."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from contextlib import contextmanager

PRODUCERS = {"xiyu.news Feed Collection", "xiyu.news Daily Edition", "Deploy Docs",
    "xiyu.news Weekly Review", "Editorial Rebuild", "Apply Event Archive Migration",
    "xiyu.news X Distribution", "xiyu.news Binance Square Distribution", "xiyunews State Maintenance"}
DOCUMENTS = {"data/staging-items.json": "staging",
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

    def load_document(self, name, incoming, *, primary=False):
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
                # A successful/unknown-response Git checkpoint has caught up.
                db.execute("UPDATE publication_documents SET source_digest=?,dirty=0 WHERE name=?", (digest,name))
                return json.loads(payload)
            if dirty:
                raise StateConflict("unpublished local state conflicts with a changed audit snapshot: " + name)
            db.execute("UPDATE publication_documents SET payload=?,digest=?,source_digest=?,dirty=0 WHERE name=?", (text,digest,digest,name))
            return incoming

    def save_document(self, name, value):
        text = canonical(value)
        digest = signature(text)
        with self.connect() as db:
            db.execute("INSERT INTO publication_documents VALUES(?,?,?,?,1) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload,digest=excluded.digest,dirty=1", (name,text,digest,""))

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
            return {"verified": True, "documents": db.execute("SELECT COUNT(*) FROM publication_documents").fetchone()[0],
                "cache_rows": db.execute("SELECT COUNT(*) FROM ai_cache").fetchone()[0],
                "runs": db.execute("SELECT COUNT(*) FROM publication_runs").fetchone()[0]}


def active_store():
    directory = os.environ.get("XIYUNEWS_STATE_DIR")
    if not directory:
        return None
    if os.environ.get("GITHUB_ACTIONS") == "true" and (os.environ.get("GITHUB_REPOSITORY") != "ohxiyu/xiyunews" or os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_WORKFLOW") not in PRODUCERS):
        return None  # Tests/PRs/preview builds never touch business caches.
    path = Path(directory)
    if not path.is_absolute():
        raise ValueError("publication state requires an absolute directory")
    key = str(path)
    if key not in _stores:
        _stores[key] = PublicationState(path)
    return _stores[key]


def document_key(path):
    try:
        return DOCUMENTS.get(Path(path).resolve().relative_to(Path.cwd().resolve()).as_posix())
    except ValueError:
        return None


def read_document(path, *, name=None, primary=False):
    path = Path(path)
    key = name or document_key(path)
    store = active_store() if key else None
    incoming = json.loads(path.read_text()) if path.exists() else None
    return store.load_document(key, incoming, primary=primary) if store else incoming


def write_document(path, value, *, name=None):
    from ._file_utils import _atomic_write_text
    path = Path(path)
    key = name or document_key(path)
    store = active_store() if key else None
    if store:
        store.save_document(key, value)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    store = active_store()
    if store is None:
        raise ValueError("trusted production SQLite environment required")
    if args.bootstrap:
        root = args.bootstrap
        names = {"staging-items.json":"staging", "events.json":"events", "event-legacy-urls.json":"event_urls",
            "bmtnews_state.json":"daily", "x-queue.json":"x_queue", "square-queue.json":"square_queue"}
        documents = {name: json.loads((root / filename).read_text()) for filename,name in names.items() if (root / filename).exists()}
        from .edition import StagingState
        from .daily_feed import DailyFeedState
        from .events import TrackedEvent
        from .event_pipeline import known_story_assignments
        from .x_queue import validate as validate_x
        from .square_plan import validate as validate_square
        if "staging" in documents:
            StagingState.model_validate(documents["staging"])
        if "daily" in documents:
            DailyFeedState.model_validate(documents["daily"])
        if "events" in documents:
            known_story_assignments([TrackedEvent.model_validate(row) for row in documents["events"]["events"]])
        if "x_queue" in documents:
            validate_x(documents["x_queue"])
        if "square_queue" in documents:
            validate_square(documents["square_queue"])
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

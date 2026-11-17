"""Fenced live SQLite state for ephemeral Actions jobs; no backup/cache backend.

The existing SQL domain transactions remain unchanged. A transaction's changed
64 KiB blocks reach the private Durable Object atomically BEFORE local commit or
external delivery. Transport ambiguity stops the job, never permits a send.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .publication_state import PublicationState, StateConflict
from ._file_utils import _atomic_write_text

ORIGIN = "https://xiyu.news/internal/publication-state"
BLOCK = 65536
MAX_SIZE = 128 * 1024 * 1024


class Transport:
    def __init__(self):
        self.token = ""
        self.expires = 0

    def identity(self):
        if self.expires <= time.time():
            # Only GitHub's per-job, short-lived OIDC identity. Never new secrets.
            url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
            if not url.startswith("https://"):
                raise StateConflict("OIDC identity unavailable")
            request = Request(url + ("&" if "?" in url else "?") + urlencode({"audience":ORIGIN}),
                headers={"Authorization":"Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]})
            with urlopen(request, timeout=30) as response:
                self.token = json.load(response)["value"]
            self.expires = time.time() + 180
        return self.token

    def call(self, action, body):
        raw = json.dumps(body, separators=(",", ":")).encode()
        if len(raw) > 2 * 1024 * 1024:
            raise StateConflict("state request too large")
        request = Request(ORIGIN + "/" + action, data=raw, method="POST", headers={
            "Authorization":"Bearer " + self.identity(), "Content-Type":"application/json",
            "Accept-Encoding":"gzip"})
        try:
            with urlopen(request, timeout=90) as response:
                data = response.read(3 * 1024 * 1024)
                if response.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return json.loads(data)
        except HTTPError as error:
            # Never print identity tokens, requests, response bodies or private SQL.
            raise StateConflict("private state request rejected: " + str(error.code)) from None
        except Exception:
            raise StateConflict("private state transport unconfirmed; stop before delivery") from None


def location():
    root = Path(os.environ["RUNNER_TEMP"]) / "xiyunews-publication"
    if not root.is_absolute() or root.is_symlink():
        raise StateConflict("invalid temporary state directory")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def save_meta(root, meta):
    _atomic_write_text(root / "lease.json", json.dumps(meta))
    (root / "lease.json").chmod(0o600)


def blocks(raw):
    if not raw.startswith(b"SQLite format 3\0") or len(raw) > MAX_SIZE:
        raise StateConflict("invalid or oversized SQLite state")
    chunks = [gzip.compress(raw[n:n+BLOCK], mtime=0) for n in range(0,len(raw),BLOCK)]
    return chunks, [hashlib.sha256(chunk).hexdigest() for chunk in chunks]


def inventory(db):
    """Only counts and hashes in logs; no source text or private receipts."""
    result = {}
    for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        if not table.replace("_", "").isalnum():
            raise StateConflict("unexpected state table")
        rows = sorted(json.dumps(row,ensure_ascii=False,separators=(",",":")) for row in db.execute('SELECT * FROM "'+table+'"'))
        result[table] = {"rows":len(rows),"sha256":hashlib.sha256("\n".join(rows).encode()).hexdigest()}
    return result


def commit(transport, meta, raw):
    chunks, hashes = blocks(raw)
    changed = [{"n":n,"hash":hashes[n],"data":base64.b64encode(chunk).decode()}
               for n,chunk in enumerate(chunks) if n >= len(meta["hashes"]) or hashes[n] != meta["hashes"][n]]
    if not changed and len(raw) == meta["size"]:
        return meta
    base = {"owner":meta["owner"], "version":meta["version"]}
    for start in range(0,len(changed),8):
        transport.call("upload",{**base,"pages":changed[start:start+8]})
    result = transport.call("commit",{**base,"size":len(raw),"hashes":hashes})
    if result.get("version") != meta["version"]+1 or result.get("hashes") != hashes or result.get("size") != len(raw):
        raise StateConflict("remote state commit unconfirmed")
    return {**result,"owner":meta["owner"]}


def acquire(root, transport, *, migration=False, wait=600):
    owner = os.environ["GITHUB_RUN_ID"] + ":" + os.environ["GITHUB_RUN_ATTEMPT"] + ":" + secrets.token_hex(16)
    deadline = time.monotonic() + wait
    while True:
        try:
            meta = {**transport.call("acquire",{"owner":owner}),"owner":owner}
            break
        except StateConflict as error:
            if "423" not in str(error) or time.monotonic() >= deadline:
                raise
            time.sleep(10)
    save_meta(root,meta)
    if migration:
        return meta
    if not meta.get("ready"):
        raise StateConflict("private state has not been initialized")
    raw = bytearray()
    for start in range(0,len(meta["hashes"]),8):
        value = transport.call("download",{"owner":owner,"version":meta["version"],"start":start})
        pages = value["pages"]
        if len(pages) != min(8,len(meta["hashes"])-start):
            raise StateConflict("incomplete private state")
        for expected,page in enumerate(pages,start):
            encoded = base64.b64decode(page["data"], validate=True)
            if page["n"] != expected or hashlib.sha256(encoded).hexdigest() != meta["hashes"][expected]:
                raise StateConflict("private state checksum mismatch")
            chunk = gzip.decompress(encoded)
            if len(chunk) > BLOCK:
                raise StateConflict("oversized state page")
            raw.extend(chunk)
    if len(raw) != meta["size"] or not raw.startswith(b"SQLite format 3\0"):
        raise StateConflict("invalid private state snapshot")
    path = root / "publication.sqlite3"
    if path.exists():
        raise StateConflict("temporary state already exists; do not replace live work")
    with path.open("xb") as handle:
        os.chmod(path,0o600)
        handle.write(raw)
    with sqlite3.connect(path) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise StateConflict("private SQLite integrity failed")
    return meta


class Connection(sqlite3.Connection):
    def execute(self, sql, parameters=()):
        # Page transport uses a self-contained DELETE-journal image. WAL is only
        # for the old server backend, and must never create unexported sidecars.
        if sql.strip().upper() == "PRAGMA JOURNAL_MODE=WAL":
            sql = "PRAGMA journal_mode=DELETE"
        return super().execute(sql,parameters)


class EdgePublicationState(PublicationState):
    def __init__(self, root, transport=None):
        self.transport = transport or Transport()
        self.root = root
        super().__init__(root)

    @contextmanager
    def connect(self):
        # Different Python steps share one fenced job lease and metadata file.
        # A local flock also prevents accidental same-job concurrent writers.
        with (self.root / "state.lock").open("a") as guard:
            fcntl.flock(guard,fcntl.LOCK_EX)
            meta = json.loads((self.root / "lease.json").read_text())
            if meta["until"] <= time.time()*1000:
                raise StateConflict("private state lease expired")
            db = sqlite3.connect(self.root / "publication.sqlite3", factory=Connection, timeout=30)
            try:
                db.execute("PRAGMA synchronous=FULL")
                before = db.serialize()
                with db:
                    yield db
                    # serialize includes this transaction's uncommitted writes.
                    # The remote commit is the durability boundary, before send.
                    raw = db.serialize()
                    updated = commit(self.transport,meta,raw) if raw != before else meta
                if updated is not meta:
                    save_meta(self.root,updated)
            finally:
                db.close()


def migrate(root, transport, source):
    meta = acquire(root,transport,migration=True,wait=0)
    if meta["ready"]:
        raise StateConflict("state already initialized; migration never overwrites it")
    # Read-only direct transfer of live state, not a retained backup file.
    with sqlite3.connect("file:"+str(source)+"?mode=ro",uri=True) as source_db:
        source_db.execute("PRAGMA query_only=ON")
        if source_db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise StateConflict("source integrity failed")
        memory = sqlite3.connect(":memory:")
        try:
            source_db.backup(memory)
            raw = bytearray(memory.serialize())
            # SQLite's online backup retains WAL flags even in memory. All pages
            # are in this image; normalize only the journal format header flags.
            raw[18:20] = b"\x01\x01"
            summary = inventory(memory)
        finally:
            memory.close()
    save_meta(root,commit(transport,meta,bytes(raw)))
    print(json.dumps({"migrated":True,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"tables":summary}))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["acquire","release","migrate","verify"])
    parser.add_argument("--source",type=Path)
    args=parser.parse_args()
    root,transport=location(),Transport()
    if args.action == "acquire":
        meta=acquire(root,transport)
        path = root/"publication.sqlite3"
        print(json.dumps({"ready":meta["ready"],"version":meta["version"],"bytes":meta["size"],"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}))
    elif args.action == "migrate":
        if not args.source or not args.source.is_absolute():
            raise ValueError("absolute migration source required")
        migrate(root,transport,args.source)
    elif args.action == "release":
        if (root/"lease.json").exists():
            meta=json.loads((root/"lease.json").read_text())
            transport.call("release",{"owner":meta["owner"]})
            print('{"released":true}')
    else:
        store=EdgePublicationState(root,transport)
        with store.connect() as db:
            summary=inventory(db)
        print(json.dumps({**store.verify(),"tables":summary}))


if __name__ == "__main__":
    main()

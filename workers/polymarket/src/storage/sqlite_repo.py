"""SQLite report storage."""
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class SQLiteReportRepository:
    def __init__(self, db_path: str = "db/reports.db"):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    items_count INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_platform_updated
                ON reports(platform, updated_at DESC)
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    async def save_report(self, platform: str, payload: dict[str, Any]) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._save_report_sync, platform, payload)

    def _save_report_sync(self, platform: str, payload: dict[str, Any]) -> str:
        conn = self._get_conn()
        try:
            updated_at = payload.get("updated_at", datetime.now(timezone.utc).isoformat())
            items_count = len(payload.get("items", []))
            payload_json = json.dumps(payload, ensure_ascii=False)
            cursor = conn.execute(
                """
                INSERT INTO reports (platform, updated_at, items_count, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (platform, updated_at, items_count, payload_json),
            )
            conn.commit()
            return str(cursor.lastrowid)
        finally:
            conn.close()

    async def get_latest_report(self, platform: str) -> dict[str, Any] | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_latest_report_sync, platform)

    def _get_latest_report_sync(self, platform: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                """
                SELECT payload_json
                FROM reports
                WHERE platform = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (platform,),
            ).fetchone()
            return json.loads(row["payload_json"]) if row else None
        finally:
            conn.close()

    async def get_history(self, platform: str, days: int = 7) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_history_sync, platform, days)

    def _get_history_sync(self, platform: str, days: int) -> list[dict[str, Any]]:
        conn = self._get_conn()
        try:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            rows = conn.execute(
                """
                SELECT id, platform, updated_at, items_count
                FROM reports
                WHERE platform = ? AND updated_at >= ?
                ORDER BY updated_at DESC
                """,
                (platform, cutoff_date),
            ).fetchall()
            return [
                {
                    "storage_key": str(row["id"]),
                    "platform": row["platform"],
                    "updated_at": row["updated_at"],
                    "items_count": row["items_count"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    async def get_report_by_id(self, report_id: str) -> dict[str, Any] | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_report_by_id_sync, report_id)

    def _get_report_by_id_sync(self, report_id: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                """
                SELECT payload_json
                FROM reports
                WHERE id = ?
                """,
                (report_id,),
            ).fetchone()
            return json.loads(row["payload_json"]) if row else None
        finally:
            conn.close()

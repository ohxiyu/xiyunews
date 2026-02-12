"""
SQLite implementation of report repository
"""
import sqlite3
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from pathlib import Path
from .base import ReportRepository


class SQLiteReportRepository(ReportRepository):
    """SQLite-based report storage"""

    def __init__(self, db_path: str = "db/reports.db"):
        """
        Initialize repository

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and table exist"""
        # Create directory if needed
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create table
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
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    async def save_report(self, platform: str, payload: Dict) -> str:
        """
        Save a report

        Args:
            platform: Platform name (polymarket/opinion)
            payload: Report data dictionary

        Returns:
            Report ID as string
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._save_report_sync, platform, payload)

    def _save_report_sync(self, platform: str, payload: Dict) -> str:
        """Synchronous save (for thread pool)"""
        conn = self._get_conn()
        try:
            updated_at = payload.get('updated_at', datetime.now(timezone.utc).isoformat())
            items_count = len(payload.get('items', []))
            payload_json = json.dumps(payload, ensure_ascii=False)

            cursor = conn.execute(
                """
                INSERT INTO reports (platform, updated_at, items_count, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (platform, updated_at, items_count, payload_json)
            )
            conn.commit()
            return str(cursor.lastrowid)
        finally:
            conn.close()

    async def get_latest_report(self, platform: str) -> Optional[Dict]:
        """Get the latest report for a platform"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_latest_report_sync, platform)

    def _get_latest_report_sync(self, platform: str) -> Optional[Dict]:
        """Synchronous get latest (for thread pool)"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """
                SELECT id, platform, updated_at, items_count, payload_json
                FROM reports
                WHERE platform = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (platform,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            payload = json.loads(row['payload_json'])
            return payload
        finally:
            conn.close()

    async def get_history(self, platform: str, days: int = 7) -> List[Dict]:
        """Get report history for N days"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_history_sync, platform, days)

    def _get_history_sync(self, platform: str, days: int) -> List[Dict]:
        """Synchronous get history (for thread pool)"""
        conn = self._get_conn()
        try:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            cursor = conn.execute(
                """
                SELECT id, platform, updated_at, items_count
                FROM reports
                WHERE platform = ? AND updated_at >= ?
                ORDER BY updated_at DESC
                """,
                (platform, cutoff_date)
            )
            rows = cursor.fetchall()

            history = []
            for row in rows:
                history.append({
                    "storage_key": str(row['id']),
                    "platform": row['platform'],
                    "updated_at": row['updated_at'],
                    "items_count": row['items_count']
                })
            return history
        finally:
            conn.close()

    async def get_report_by_id(self, report_id: str) -> Optional[Dict]:
        """Get a specific report by ID"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_report_by_id_sync, report_id)

    def _get_report_by_id_sync(self, report_id: str) -> Optional[Dict]:
        """Synchronous get by ID (for thread pool)"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """
                SELECT id, platform, updated_at, items_count, payload_json
                FROM reports
                WHERE id = ?
                """,
                (report_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            payload = json.loads(row['payload_json'])
            return payload
        finally:
            conn.close()

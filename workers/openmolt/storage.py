"""SQLite storage for tracking sent posts (deduplication)."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("moltbook.storage")


class Storage:
    def __init__(self, db_path: str = "data/sent_posts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: sqlite3.Connection | None = None

    def init_db(self) -> None:
        """Initialize database and create tables."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT UNIQUE NOT NULL,
                title TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_post_id ON sent_posts(post_id)"
        )
        self.conn.commit()
        logger.info(f"Database initialized: {self.db_path}")

    def is_sent(self, post_id: str) -> bool:
        """Check if a post has already been sent."""
        if not self.conn:
            return False
        cursor = self.conn.execute(
            "SELECT 1 FROM sent_posts WHERE post_id = ?", (post_id,)
        )
        return cursor.fetchone() is not None

    def mark_sent(self, post_id: str, title: str = "") -> None:
        """Mark a post as sent."""
        if not self.conn:
            return
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO sent_posts (post_id, title, sent_at) VALUES (?, ?, ?)",
                (post_id, title, datetime.now().isoformat()),
            )
            self.conn.commit()
            logger.debug(f"Marked post as sent: {post_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to mark post as sent: {e}")

    def cleanup(self, max_history: int = 10000) -> int:
        """Remove old records to keep database size manageable.

        Returns the number of records deleted.
        """
        if not self.conn:
            return 0

        cursor = self.conn.execute("SELECT COUNT(*) FROM sent_posts")
        count = cursor.fetchone()[0]

        if count <= max_history:
            return 0

        to_delete = count - max_history
        self.conn.execute("""
            DELETE FROM sent_posts WHERE id IN (
                SELECT id FROM sent_posts ORDER BY sent_at ASC LIMIT ?
            )
        """, (to_delete,))
        self.conn.commit()
        logger.info(f"Cleaned up {to_delete} old records")
        return to_delete

    def get_sent_count(self) -> int:
        """Get total number of sent posts."""
        if not self.conn:
            return 0
        cursor = self.conn.execute("SELECT COUNT(*) FROM sent_posts")
        return cursor.fetchone()[0]

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Database connection closed")

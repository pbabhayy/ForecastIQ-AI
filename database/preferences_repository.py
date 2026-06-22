"""
Database: User Preferences
==========================
Persist lightweight user settings (theme, etc.) in SQLite.
"""

from __future__ import annotations

from datetime import datetime, timezone

from database import sqlite_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def get_preference(key: str, default: str | None = None) -> str | None:
    """Load a preference value by key."""
    try:
        sqlite_manager.initialize_database()
        row = sqlite_manager.fetch_one(
            "SELECT value FROM user_preferences WHERE key = ?", (key,)
        )
        return row["value"] if row else default
    except sqlite_manager.DatabaseError:
        logger.exception("Failed to read preference '%s'.", key)
        return default


def set_preference(key: str, value: str) -> None:
    """Upsert a preference value."""
    sqlite_manager.initialize_database()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sqlite_manager.execute(
        """
        INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
        VALUES (?, ?, ?)
        """,
        (key, value, now),
    )
    logger.info("Preference saved: %s=%s", key, value)

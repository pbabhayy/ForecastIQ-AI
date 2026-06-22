"""
Database: SQLite Manager
==========================
Low-level SQLite connection and schema lifecycle.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Iterator

from config.settings import get_settings
from database.models import CREATE_TABLES_SQL, SCHEMA_VERSION
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Raised when the database cannot be initialized or queried."""


def get_db_path() -> Path:
    """Return the configured database file path, ensuring parent dir exists."""
    path = Path(get_settings().db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def initialize_database() -> bool:
    """Create schema if missing. Returns True on success."""
    try:
        with connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)
            conn.execute(
                "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
                ("version", str(SCHEMA_VERSION)),
            )
            conn.commit()
        logger.info("Database initialized at %s.", get_db_path())
        return True
    except sqlite3.Error as exc:
        logger.exception("Database initialization failed.")
        raise DatabaseError(str(exc)) from exc


@contextmanager
def connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with row factory enabled."""
    path = get_db_path()
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as exc:
        logger.exception("Database connection error.")
        raise DatabaseError(str(exc)) from exc
    finally:
        if conn is not None:
            conn.close()


def execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    """Execute a write statement and return lastrowid."""
    with connection() as conn:
        cursor = conn.execute(sql, params)
        conn.commit()
        return int(cursor.lastrowid or 0)


def executemany(sql: str, seq: list[tuple[Any, ...]]) -> None:
    """Execute a parameterized statement for many rows."""
    with connection() as conn:
        conn.executemany(sql, seq)
        conn.commit()


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    """Fetch a single row."""
    with connection() as conn:
        return conn.execute(sql, params).fetchone()


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    """Fetch all matching rows."""
    with connection() as conn:
        return list(conn.execute(sql, params).fetchall())


def check_health() -> dict[str, Any]:
    """Return a simple database health/status dict."""
    try:
        initialize_database()
        row = fetch_one("SELECT value FROM schema_meta WHERE key = 'version'")
        return {
            "ok": True,
            "path": str(get_db_path()),
            "version": row["value"] if row else str(SCHEMA_VERSION),
        }
    except DatabaseError as exc:
        return {"ok": False, "path": str(get_db_path()), "error": str(exc)}

"""
Database: Models / Schema
=========================
Schema definitions and row dataclasses for SQLite persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# --------------------------------------------------------------------------- #
# DDL
# --------------------------------------------------------------------------- #
SCHEMA_VERSION: Final[int] = 1

CREATE_TABLES_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    row_count INTEGER,
    column_count INTEGER,
    date_range TEXT,
    metrics_json TEXT,
    quality_score REAL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'saved',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'saved',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);

CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER,
    metric TEXT,
    model TEXT,
    horizon INTEGER,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'saved',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);

CREATE TABLE IF NOT EXISTS ai_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER,
    provider TEXT,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'saved',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER,
    title TEXT NOT NULL,
    file_path TEXT,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'generated',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@dataclass
class DatasetRecord:
    """Row representation for the datasets table."""

    id: int | None
    name: str
    row_count: int | None
    column_count: int | None
    date_range: str | None
    metrics_json: str | None
    quality_score: float | None
    payload_json: str
    status: str
    created_at: str | None = None


@dataclass
class ReportRecord:
    """Row representation for the reports table."""

    id: int | None
    dataset_id: int | None
    title: str
    file_path: str | None
    payload_json: str
    status: str
    created_at: str | None = None
